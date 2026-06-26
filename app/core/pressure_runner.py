import queue
import random
import threading
import time

from app.core.http_client import send_one_request
from app.core.metrics import calculate_metrics
from app.core.task_model import RUN_MODE_DURATION
from app.report.report_generator import ReportGenerator
from app.utils.body_param_utils import resolve_request_body_info


STOP_GRACE_SECONDS = 1.0


class PressureRunner:
    def __init__(self, config, on_log=None, on_progress=None, on_done=None):
        self.config = config
        self.on_log = on_log
        self.on_progress = on_progress
        self.on_done = on_done

        self.stop_event = threading.Event()
        self.collecting_event = threading.Event()
        self.thread = None

    def start(self):
        self.stop_event.clear()
        self.collecting_event.set()

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _log(self, message):
        if self.on_log:
            self.on_log(message)

    def _progress(self, payload):
        if self.on_progress:
            self.on_progress(payload)

    def _done(self, payload):
        if self.on_done:
            self.on_done(payload)

    def _think(self):
        min_time = self.config.think_time_min
        max_time = self.config.think_time_max

        if max_time <= 0 and min_time <= 0:
            return

        if max_time < min_time:
            max_time = min_time

        delay = random.uniform(min_time, max_time) if max_time > min_time else min_time
        deadline = time.perf_counter() + delay

        while time.perf_counter() < deadline and not self.stop_event.is_set():
            time.sleep(min(0.2, max(deadline - time.perf_counter(), 0)))

    def _sleep_interruptible(self, seconds):
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline and not self.stop_event.is_set():
            time.sleep(min(0.2, max(deadline - time.perf_counter(), 0)))

    def _emit_progress(self, results, result, global_start_perf):
        current_wall_time = max(time.perf_counter() - global_start_perf, 0.001)
        metrics = calculate_metrics(results, current_wall_time)

        payload = {
            "completed": len(results),
            "result": result,
            "metrics": metrics,
            "run_mode": self.config.run_mode,
            "elapsed": current_wall_time,
        }

        if self.config.run_mode == RUN_MODE_DURATION:
            payload["total"] = 0
            payload["duration"] = self.config.duration_seconds
        else:
            payload["total"] = self.config.total_requests

        self._progress(payload)

    def _send_request(self, request_id, results, result_lock, global_start_ts, global_start_perf):
        if self.stop_event.is_set():
            return None

        body_info = resolve_request_body_info(self.config, request_id)
        result = send_one_request(
            request_id=request_id,
            config=self.config,
            global_start_ts=global_start_ts,
            body=body_info["body"],
            stop_event=self.stop_event,
        )
        result.body_template_index = body_info["body_template_index"]
        result.body_template_label = body_info["body_template_label"]

        with result_lock:
            if not self.collecting_event.is_set():
                return result
            if self.stop_event.is_set() and result.error == "Cancelled":
                return result
            results.append(result)
            snapshot = list(results)

        self._emit_progress(snapshot, result, global_start_perf)
        return result

    def _worker_loop(self, task_queue, results, result_lock, global_start_ts, global_start_perf):
        while not self.stop_event.is_set():
            try:
                request_id = task_queue.get_nowait()
            except queue.Empty:
                break

            self._send_request(
                request_id=request_id,
                results=results,
                result_lock=result_lock,
                global_start_ts=global_start_ts,
                global_start_perf=global_start_perf,
            )
            task_queue.task_done()

            if self.stop_event.is_set():
                break

            self._think()

    def _duration_worker_loop(
        self,
        request_id_counter,
        counter_lock,
        results,
        result_lock,
        global_start_ts,
        global_start_perf,
        deadline_perf,
    ):
        while not self.stop_event.is_set() and time.perf_counter() < deadline_perf:
            with counter_lock:
                request_id_counter[0] += 1
                request_id = request_id_counter[0]

            self._send_request(
                request_id=request_id,
                results=results,
                result_lock=result_lock,
                global_start_ts=global_start_ts,
                global_start_perf=global_start_perf,
            )

            if time.perf_counter() >= deadline_perf or self.stop_event.is_set():
                break

            self._think()

    def _wait_for_workers(self, threads, results, result_lock):
        if not self.stop_event.is_set():
            for t in threads:
                t.join()
            with result_lock:
                return list(results), 0

        deadline = time.perf_counter() + STOP_GRACE_SECONDS
        while time.perf_counter() < deadline:
            alive = [t for t in threads if t.is_alive()]
            if not alive:
                break
            time.sleep(0.05)

        alive_count = sum(1 for t in threads if t.is_alive())
        self.collecting_event.clear()

        with result_lock:
            snapshot = list(results)

        return snapshot, alive_count

    def _run(self):
        self._log("压测任务启动")
        self._log(f"URL: {self.config.url}")
        self._log(f"Method: {self.config.method}")
        self._log(f"并发数: {self.config.concurrency}")
        self._log(f"首帧超时: {self.config.first_frame_timeout} 秒")
        self._log(f"完整超时: {self.config.timeout} 秒")

        if self.config.run_mode == RUN_MODE_DURATION:
            self._log(f"压测模式: 按时长")
            self._log(f"持续时长: {self.config.duration_seconds} 秒")
        else:
            self._log(f"压测模式: 固定请求数")
            self._log(f"总请求数: {self.config.total_requests}")

        if self.config.think_time_max > 0 or self.config.think_time_min > 0:
            self._log(
                f"思考时间: {self.config.think_time_min}~{self.config.think_time_max} 秒"
            )

        if self.config.body_templates:
            self._log(f"Body 数据文件: {self.config.body_data_file}")
            self._log(f"Body 模板数: {len(self.config.body_templates)}")
            self._log("已启用 Body 数据文件，界面 Body 输入框内容不会作为请求体发送")
        else:
            self._log("Body 来源: 界面 Body 输入框")

        if self.config.method == "GRPC" and self.config.proto_file:
            self._log(f"Proto 文件: {self.config.proto_file}")

        if self.config.method == "GRPC":
            self._log("gRPC URL 可填写 grpc://host:port；配置 Proto 后会自动选择默认 RPC")

        results = []
        result_lock = threading.Lock()
        threads = []

        global_start_perf = time.perf_counter()
        global_start_ts = time.time()

        if self.config.concurrency > 1 and self.config.ramp_up > 0:
            start_interval = self.config.ramp_up / (self.config.concurrency - 1)
        else:
            start_interval = 0

        if self.config.run_mode == RUN_MODE_DURATION:
            request_id_counter = [0]
            counter_lock = threading.Lock()
            deadline_perf = global_start_perf + self.config.duration_seconds

            for _ in range(self.config.concurrency):
                if self.stop_event.is_set():
                    break

                t = threading.Thread(
                    target=self._duration_worker_loop,
                    args=(
                        request_id_counter,
                        counter_lock,
                        results,
                        result_lock,
                        global_start_ts,
                        global_start_perf,
                        deadline_perf,
                    ),
                    daemon=True,
                )
                t.start()
                threads.append(t)

                if start_interval > 0:
                    self._sleep_interruptible(start_interval)
        else:
            task_queue = queue.Queue()
            for i in range(1, self.config.total_requests + 1):
                task_queue.put(i)

            for _ in range(self.config.concurrency):
                if self.stop_event.is_set():
                    break

                t = threading.Thread(
                    target=self._worker_loop,
                    args=(task_queue, results, result_lock, global_start_ts, global_start_perf),
                    daemon=True,
                )
                t.start()
                threads.append(t)

                if start_interval > 0:
                    self._sleep_interruptible(start_interval)

        results_snapshot, alive_count = self._wait_for_workers(threads, results, result_lock)

        wall_time = max(time.perf_counter() - global_start_perf, 0.001)
        metrics = calculate_metrics(results_snapshot, wall_time)

        if self.stop_event.is_set() and alive_count:
            self._log(
                f"停止后仍有 {alive_count} 个请求在等待网络返回，报告仅包含已完成请求"
            )

        self._log("开始生成报告")

        report_paths = ReportGenerator().generate(
            config=self.config,
            results=results_snapshot,
            metrics=metrics,
        )

        self._done({
            "stopped": self.stop_event.is_set(),
            "metrics": metrics,
            "report_paths": report_paths,
            "run_mode": self.config.run_mode,
        })
