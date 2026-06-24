import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app.config.default_config import (
    DEFAULT_URL,
    DEFAULT_METHOD,
    DEFAULT_CONCURRENCY,
    DEFAULT_TOTAL_REQUESTS,
    DEFAULT_TIMEOUT,
    DEFAULT_RAMP_UP,
    DEFAULT_RUN_MODE,
    DEFAULT_DURATION_SECONDS,
    DEFAULT_THINK_TIME_MIN,
    DEFAULT_THINK_TIME_MAX,
    DEFAULT_BODY_DATA_FILE,
    DEFAULT_BODY_DATA_DIR,
    DEFAULT_PROTO_DIR,
    DEFAULT_INTERFACE_DIR,
    DEFAULT_INTERFACE_FILE,
    DEFAULT_SUCCESS_KEYWORD,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_HEADERS_TEXT,
    DEFAULT_BODY_TEXT,
)
from app.core.task_model import RUN_MODE_DURATION, RUN_MODE_REQUESTS
from app.utils.file_utils import clear_report_files, ensure_dir, list_report_files, open_folder
from app.utils.interface_utils import ensure_sample_interface_file, load_interfaces
from app.utils.validators import validate_task_config

RUN_MODE_LABELS = {
    RUN_MODE_REQUESTS: "固定请求数",
    RUN_MODE_DURATION: "按时长",
}
RUN_MODE_VALUES = {label: mode for mode, label in RUN_MODE_LABELS.items()}


class ConfigPanel(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="压测配置", padding=10)

        self.url_var = tk.StringVar(value=DEFAULT_URL)
        self.method_var = tk.StringVar(value=DEFAULT_METHOD)
        self.concurrency_var = tk.StringVar(value=str(DEFAULT_CONCURRENCY))
        self.total_var = tk.StringVar(value=str(DEFAULT_TOTAL_REQUESTS))
        self.timeout_var = tk.StringVar(value=str(DEFAULT_TIMEOUT))
        self.ramp_up_var = tk.StringVar(value=str(DEFAULT_RAMP_UP))
        self.success_keyword_var = tk.StringVar(value=DEFAULT_SUCCESS_KEYWORD)
        self.output_dir_var = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.run_mode_var = tk.StringVar(value=RUN_MODE_LABELS[DEFAULT_RUN_MODE])
        self.duration_var = tk.StringVar(value=str(DEFAULT_DURATION_SECONDS))
        self.think_min_var = tk.StringVar(value=str(DEFAULT_THINK_TIME_MIN))
        self.think_max_var = tk.StringVar(value=str(DEFAULT_THINK_TIME_MAX))
        self.body_data_file_var = tk.StringVar(value=DEFAULT_BODY_DATA_FILE)
        self.body_data_dir_var = tk.StringVar(value=DEFAULT_BODY_DATA_DIR)
        self.interface_var = tk.StringVar(value="自定义")
        self.proto_dir_var = tk.StringVar(value=DEFAULT_PROTO_DIR)
        self.proto_file_var = tk.StringVar(value="")
        self.grpc_service_var = tk.StringVar(value="")
        self.grpc_method_var = tk.StringVar(value="")
        self.grpc_request_message_var = tk.StringVar(value="")
        self.grpc_response_message_var = tk.StringVar(value="")
        self.grpc_server_streaming_var = tk.BooleanVar(value=False)
        ensure_dir(DEFAULT_BODY_DATA_DIR)
        ensure_dir(DEFAULT_PROTO_DIR)
        ensure_dir(DEFAULT_INTERFACE_DIR)
        ensure_sample_interface_file(DEFAULT_INTERFACE_FILE)
        self.interfaces = load_interfaces(DEFAULT_INTERFACE_FILE, DEFAULT_PROTO_DIR)

        self._build()
        self._on_run_mode_changed()
        self._refresh_interface_options()

    def _build(self):
        for i in range(6):
            self.columnconfigure(i, weight=1)

        ttk.Label(self, text="接口").grid(row=0, column=0, sticky="w")
        self.interface_combo = ttk.Combobox(
            self,
            textvariable=self.interface_var,
            width=22,
            state="readonly",
        )
        self.interface_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=4)
        self.interface_combo.bind("<<ComboboxSelected>>", self._on_interface_changed)

        ttk.Label(self, text="URL").grid(row=0, column=2, sticky="w")
        ttk.Entry(self, textvariable=self.url_var).grid(
            row=0, column=3, columnspan=2, sticky="ew", padx=5, pady=4
        )
        ttk.Button(self, text="刷新接口", command=self.reload_interfaces).grid(
            row=0, column=5, sticky="e", padx=5, pady=4
        )

        ttk.Label(self, text="Method").grid(row=1, column=0, sticky="w")
        ttk.Combobox(
            self,
            textvariable=self.method_var,
            values=["GET", "POST", "PUT", "DELETE", "GRPC"],
            width=10,
            state="readonly",
        ).grid(row=1, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(self, text="并发数").grid(row=1, column=2, sticky="w")
        ttk.Entry(self, textvariable=self.concurrency_var, width=12).grid(
            row=1, column=3, sticky="w", padx=5
        )

        self.total_label = ttk.Label(self, text="总请求数")
        self.total_label.grid(row=1, column=4, sticky="w")
        self.total_entry = ttk.Entry(self, textvariable=self.total_var, width=12)
        self.total_entry.grid(row=1, column=5, sticky="w", padx=5)

        ttk.Label(self, text="超时时间/s").grid(row=2, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.timeout_var, width=12).grid(
            row=2, column=1, sticky="w", padx=5, pady=4
        )

        ttk.Label(self, text="Ramp-up/s").grid(row=2, column=2, sticky="w")
        ttk.Entry(self, textvariable=self.ramp_up_var, width=12).grid(
            row=2, column=3, sticky="w", padx=5
        )

        ttk.Label(self, text="成功关键字").grid(row=2, column=4, sticky="w")
        ttk.Entry(self, textvariable=self.success_keyword_var, width=20).grid(
            row=2, column=5, sticky="w", padx=5
        )

        sim_frame = ttk.LabelFrame(self, text="用户模拟", padding=8)
        sim_frame.grid(row=3, column=0, columnspan=6, sticky="ew", pady=4)
        for i in range(6):
            sim_frame.columnconfigure(i, weight=1)

        ttk.Label(sim_frame, text="压测模式").grid(row=0, column=0, sticky="w")
        self.run_mode_combo = ttk.Combobox(
            sim_frame,
            textvariable=self.run_mode_var,
            values=list(RUN_MODE_LABELS.values()),
            width=14,
            state="readonly",
        )
        self.run_mode_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        self.run_mode_combo.bind("<<ComboboxSelected>>", self._on_run_mode_changed)

        self.duration_label = ttk.Label(sim_frame, text="持续时长/s")
        self.duration_label.grid(row=0, column=2, sticky="w")
        self.duration_entry = ttk.Entry(sim_frame, textvariable=self.duration_var, width=12)
        self.duration_entry.grid(row=0, column=3, sticky="w", padx=5)

        ttk.Label(sim_frame, text="思考时间/s").grid(row=0, column=4, sticky="w")
        think_frame = ttk.Frame(sim_frame)
        think_frame.grid(row=0, column=5, sticky="w", padx=5)
        ttk.Entry(think_frame, textvariable=self.think_min_var, width=6).pack(side=tk.LEFT)
        ttk.Label(think_frame, text="~").pack(side=tk.LEFT, padx=2)
        ttk.Entry(think_frame, textvariable=self.think_max_var, width=6).pack(side=tk.LEFT)

        ttk.Label(sim_frame, text="Body 数据文件").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(sim_frame, textvariable=self.body_data_file_var).grid(
            row=1, column=1, columnspan=4, sticky="ew", padx=5, pady=(6, 0)
        )
        ttk.Button(sim_frame, text="浏览", command=self.choose_body_data_file).grid(
            row=1, column=5, sticky="w", padx=5, pady=(6, 0)
        )

        ttk.Label(
            sim_frame,
            text=f"支持 .json 数组或 .jsonl；默认加载目录：{DEFAULT_BODY_DATA_DIR}",
            foreground="#666",
        ).grid(row=2, column=0, columnspan=6, sticky="w", pady=(4, 0))

        ttk.Button(sim_frame, text="打开数据目录", command=self.open_body_data_folder).grid(
            row=3, column=5, sticky="w", padx=5, pady=(4, 0)
        )

        ttk.Label(
            sim_frame,
            text=f"接口定义文件：{DEFAULT_INTERFACE_FILE}",
            foreground="#666",
        ).grid(row=4, column=0, columnspan=5, sticky="w", pady=(8, 0))

        ttk.Button(sim_frame, text="打开接口目录", command=self.open_interface_folder).grid(
            row=4, column=5, sticky="w", padx=5, pady=(8, 0)
        )

        ttk.Label(self, text="报告输出目录").grid(row=4, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.output_dir_var).grid(
            row=4, column=1, columnspan=3, sticky="ew", padx=5, pady=4
        )

        report_btn_frame = ttk.Frame(self)
        report_btn_frame.grid(row=4, column=4, columnspan=2, sticky="e", padx=5)

        ttk.Button(report_btn_frame, text="打开文件夹", command=self.open_report_folder).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(report_btn_frame, text="清除报告", command=self.clear_reports).pack(
            side=tk.LEFT, padx=2
        )

        payload_frame = ttk.Frame(self)
        payload_frame.grid(row=5, column=0, columnspan=6, sticky="nsew", pady=8)

        payload_frame.columnconfigure(0, weight=1)
        payload_frame.columnconfigure(1, weight=1)

        header_frame = ttk.LabelFrame(payload_frame, text="Headers，JSON 格式", padding=6)
        header_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.headers_text = tk.Text(header_frame, height=8)
        self.headers_text.pack(fill=tk.BOTH, expand=True)
        self.headers_text.insert("1.0", DEFAULT_HEADERS_TEXT)

        body_frame = ttk.LabelFrame(payload_frame, text="Body，POST/PUT 时生效", padding=6)
        body_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self.body_text = tk.Text(body_frame, height=8)
        self.body_text.pack(fill=tk.BOTH, expand=True)
        self.body_text.insert("1.0", DEFAULT_BODY_TEXT)

    def _on_run_mode_changed(self, _event=None):
        is_duration = RUN_MODE_VALUES.get(self.run_mode_var.get()) == RUN_MODE_DURATION

        if is_duration:
            self.total_entry.config(state=tk.DISABLED)
            self.duration_entry.config(state=tk.NORMAL)
        else:
            self.total_entry.config(state=tk.NORMAL)
            self.duration_entry.config(state=tk.DISABLED)

    def choose_body_data_file(self):
        data_dir = ensure_dir(self.body_data_dir_var.get())
        path = filedialog.askopenfilename(
            title="选择 Body 数据文件",
            initialdir=str(data_dir),
            filetypes=[
                ("JSON 文件", "*.json *.jsonl"),
                ("所有文件", "*.*"),
            ],
        )

        if path:
            self.body_data_file_var.set(path)

    def open_body_data_folder(self):
        try:
            open_folder(self.body_data_dir_var.get())
        except Exception as e:
            messagebox.showerror("打开失败", str(e))

    def open_interface_folder(self):
        try:
            open_folder(DEFAULT_INTERFACE_DIR)
        except Exception as e:
            messagebox.showerror("打开失败", str(e))

    def _refresh_interface_options(self):
        names = ["自定义"] + [item["name"] for item in self.interfaces]
        self.interface_combo.config(values=names)
        if self.interface_var.get() not in names:
            self.interface_var.set("自定义")

    def reload_interfaces(self):
        self.interfaces = load_interfaces(DEFAULT_INTERFACE_FILE, DEFAULT_PROTO_DIR)
        self._refresh_interface_options()
        self._on_interface_changed()

    def _on_interface_changed(self, _event=None):
        selected = self.interface_var.get()
        if selected == "自定义":
            self.proto_file_var.set("")
            self.grpc_service_var.set("")
            self.grpc_method_var.set("")
            self.grpc_request_message_var.set("")
            self.grpc_response_message_var.set("")
            self.grpc_server_streaming_var.set(False)
            return

        item = next((i for i in self.interfaces if i["name"] == selected), None)
        if not item:
            return

        self.method_var.set(item["method"])
        self.url_var.set(item["url"])
        self.success_keyword_var.set(item.get("success_keyword", ""))
        self.proto_file_var.set(item.get("proto_file", ""))
        self.grpc_service_var.set(item.get("grpc_service", ""))
        self.grpc_method_var.set(item.get("grpc_method", ""))
        self.grpc_request_message_var.set(item.get("grpc_request_message", ""))
        self.grpc_response_message_var.set(item.get("grpc_response_message", ""))
        self.grpc_server_streaming_var.set(bool(item.get("grpc_server_streaming", False)))

        self.headers_text.delete("1.0", tk.END)
        self.headers_text.insert("1.0", item.get("headers") or "{}")

        if item["method"] == "GRPC":
            self.body_data_file_var.set("")


    def _get_output_dir(self):
        return self.output_dir_var.get().strip()

    def open_report_folder(self):
        path = self._get_output_dir()
        if not path:
            messagebox.showwarning("提示", "请先设置报告输出目录")
            return

        try:
            open_folder(path)
        except Exception as e:
            messagebox.showerror("打开失败", str(e))

    def clear_reports(self):
        path = self._get_output_dir()
        if not path:
            messagebox.showwarning("提示", "请先设置报告输出目录")
            return

        report_files = list_report_files(path)
        if not report_files:
            messagebox.showinfo("提示", "报告目录中没有可清除的报告文件")
            return

        if not messagebox.askyesno(
            "确认清除",
            f"确定要删除 {len(report_files)} 个报告文件吗？\n\n"
            f"目录：{path}\n\n"
            "此操作不可恢复。",
        ):
            return

        try:
            count = clear_report_files(path)
            messagebox.showinfo("清除完成", f"已删除 {count} 个报告文件")
        except Exception as e:
            messagebox.showerror("清除失败", str(e))

    def get_config(self):
        raw = {
            "url": self.url_var.get(),
            "method": self.method_var.get(),
            "headers_text": self.headers_text.get("1.0", tk.END),
            "body": self.body_text.get("1.0", tk.END),
            "concurrency": self.concurrency_var.get(),
            "total_requests": self.total_var.get(),
            "timeout": self.timeout_var.get(),
            "ramp_up": self.ramp_up_var.get(),
            "success_keyword": self.success_keyword_var.get(),
            "output_dir": self.output_dir_var.get(),
            "run_mode": RUN_MODE_VALUES.get(self.run_mode_var.get(), RUN_MODE_REQUESTS),
            "duration_seconds": self.duration_var.get(),
            "think_time_min": self.think_min_var.get(),
            "think_time_max": self.think_max_var.get(),
            "body_data_file": self.body_data_file_var.get(),
            "body_data_dir": self.body_data_dir_var.get(),
            "proto_file": self.proto_file_var.get(),
            "proto_dir": self.proto_dir_var.get(),
            "grpc_service": self.grpc_service_var.get(),
            "grpc_method": self.grpc_method_var.get(),
            "grpc_request_message": self.grpc_request_message_var.get(),
            "grpc_response_message": self.grpc_response_message_var.get(),
            "grpc_server_streaming": self.grpc_server_streaming_var.get(),
        }

        return validate_task_config(raw)
