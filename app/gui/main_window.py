import queue
import tkinter as tk
from tkinter import ttk, messagebox

from app.core.task_model import RUN_MODE_DURATION
from app.core.pressure_runner import PressureRunner
from app.gui.config_panel import ConfigPanel
from app.gui.log_panel import LogPanel
from app.gui.metric_panel import MetricPanel


class PressureTestMainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("算法接口压测工具")
        self.root.geometry("1100x780")

        self.runner = None
        self.running = False
        self.ui_queue = queue.Queue()

        self._build()
        self.root.after(200, self._poll_ui_queue)

    def _build(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        self.config_panel = ConfigPanel(main)
        self.config_panel.pack(fill=tk.X)

        action_frame = ttk.Frame(main)
        action_frame.pack(fill=tk.X, pady=6)

        self.start_btn = ttk.Button(action_frame, text="开始压测", command=self.start_test)
        self.start_btn.pack(side=tk.LEFT, padx=4)

        self.stop_btn = ttk.Button(
            action_frame,
            text="停止",
            command=self.stop_test,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=4)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            action_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        self.progress_label_var = tk.StringVar(value="0/0")
        ttk.Label(action_frame, textvariable=self.progress_label_var).pack(side=tk.RIGHT)

        self.metric_panel = MetricPanel(main)
        self.metric_panel.pack(fill=tk.X, pady=6)

        self.log_panel = LogPanel(main)
        self.log_panel.pack(fill=tk.BOTH, expand=True)

    def start_test(self):
        if self.running:
            return

        try:
            config = self.config_panel.get_config()
        except Exception as e:
            messagebox.showerror("配置错误", str(e))
            return

        self.running = True
        self.progress_var.set(0)
        if config.run_mode == RUN_MODE_DURATION:
            self.progress_label_var.set(f"0 请求 | 0/{config.duration_seconds:.0f}s")
        else:
            self.progress_label_var.set(f"0/{config.total_requests}")
        self.metric_panel.reset()
        self.log_panel.clear()

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        self.runner = PressureRunner(
            config=config,
            on_log=self._on_log,
            on_progress=self._on_progress,
            on_done=self._on_done,
        )
        self.runner.start()

    def stop_test(self):
        if self.runner:
            self.runner.stop()
            self.stop_btn.config(text="停止中...", state=tk.DISABLED)
            self.log_panel.info("收到停止信号，正在等待运行中请求结束...")

    def _on_log(self, message):
        self.ui_queue.put({
            "type": "log",
            "message": message,
        })

    def _on_progress(self, payload):
        self.ui_queue.put({
            "type": "progress",
            "payload": payload,
        })

    def _on_done(self, payload):
        self.ui_queue.put({
            "type": "done",
            "payload": payload,
        })

    def _poll_ui_queue(self):
        try:
            while True:
                event = self.ui_queue.get_nowait()

                if event["type"] == "log":
                    self.log_panel.info(event["message"])

                elif event["type"] == "progress":
                    payload = event["payload"]
                    completed = payload["completed"]
                    total = payload["total"]
                    result = payload["result"]
                    metrics = payload["metrics"]
                    run_mode = payload.get("run_mode")

                    if run_mode == RUN_MODE_DURATION:
                        elapsed = payload.get("elapsed", 0)
                        duration = payload.get("duration", 1)
                        percent = min(elapsed / duration * 100, 100) if duration else 0
                        self.progress_var.set(percent)
                        self.progress_label_var.set(
                            f"{completed} 请求 | {elapsed:.0f}/{duration:.0f}s"
                        )
                    else:
                        percent = completed / total * 100 if total else 0
                        self.progress_var.set(percent)
                        self.progress_label_var.set(f"{completed}/{total}")

                    self.metric_panel.update_metrics(metrics)

                    if not result.success:
                        debug = f", debug={result.debug_info}" if result.debug_info else ""
                        self.log_panel.error(
                            f"请求失败 request_id={result.request_id}, "
                            f"status={result.status_code}, "
                            f"latency={result.latency_ms:.2f}ms, "
                            f"error={result.error}"
                            f"{debug}"
                        )

                elif event["type"] == "done":
                    payload = event["payload"]
                    metrics = payload["metrics"]
                    report_paths = payload["report_paths"]

                    self.running = False
                    self.start_btn.config(state=tk.NORMAL)
                    self.stop_btn.config(text="停止", state=tk.DISABLED)

                    if payload.get("stopped"):
                        self.log_panel.info("压测任务已停止")
                    else:
                        self.log_panel.info("压测任务完成")

                    self.log_panel.info(f"总请求数: {metrics['total']}")
                    self.log_panel.info(f"成功率: {metrics['success_rate']:.2f}%")
                    self.log_panel.info(f"QPS: {metrics['qps']:.2f}")
                    self.log_panel.info(f"TPS: {metrics['tps']:.2f}")
                    self.log_panel.info(f"P90: {metrics['p90_latency']:.2f} ms")
                    self.log_panel.info(f"P95: {metrics['p95_latency']:.2f} ms")
                    self.log_panel.info(f"P99: {metrics['p99_latency']:.2f} ms")
                    self.log_panel.info(f"HTML 报告: {report_paths['html_path']}")
                    self.log_panel.info(f"CSV 明细: {report_paths['csv_path']}")
                    self.log_panel.info(f"JSON 原始结果: {report_paths['json_path']}")

                    messagebox.showinfo(
                        "压测完成",
                        f"压测完成。\n\n"
                        f"成功率：{metrics['success_rate']:.2f}%\n"
                        f"QPS：{metrics['qps']:.2f}\n"
                        f"TPS：{metrics['tps']:.2f}\n"
                        f"P90：{metrics['p90_latency']:.2f} ms\n"
                        f"P95：{metrics['p95_latency']:.2f} ms\n"
                        f"P99：{metrics['p99_latency']:.2f} ms\n\n"
                        f"报告路径：\n{report_paths['html_path']}"
                    )

        except queue.Empty:
            pass

        self.root.after(200, self._poll_ui_queue)
