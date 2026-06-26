import tkinter as tk
from tkinter import ttk

from app.utils.time_utils import format_ms, format_rate


class MetricPanel(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="实时指标", padding=8)

        self.vars = {
            "total": tk.StringVar(value="0"),
            "success": tk.StringVar(value="0"),
            "fail": tk.StringVar(value="0"),
            "success_rate": tk.StringVar(value="0.00%"),
            "qps": tk.StringVar(value="0.00"),
            "tps": tk.StringVar(value="0.00"),
            "avg_first_frame": tk.StringVar(value="0.00 ms"),
            "first_frame_p95": tk.StringVar(value="0.00 ms"),
            "avg_latency": tk.StringVar(value="0.00 ms"),
            "p95": tk.StringVar(value="0.00 ms"),
        }

        self._build()

    def _build(self):
        items = [
            ("已完成", "total"),
            ("成功", "success"),
            ("失败", "fail"),
            ("成功率", "success_rate"),
            ("QPS", "qps"),

            ("TPS", "tps"),
            ("平均首帧", "avg_first_frame"),
            ("首帧 P95", "first_frame_p95"),
            ("平均完整耗时", "avg_latency"),
            ("完整耗时 P95", "p95"),
        ]

        # 每行放 5 个指标，避免窗口太挤
        for idx, (label, key) in enumerate(items):
            col = idx % 5
            row_group = idx // 5
            label_row = row_group * 2
            value_row = label_row + 1

            ttk.Label(self, text=label).grid(
                row=label_row,
                column=col,
                padx=18,
                pady=(0, 2),
                sticky="w"
            )

            ttk.Label(
                self,
                textvariable=self.vars[key],
                font=("Arial", 12, "bold")
            ).grid(
                row=value_row,
                column=col,
                padx=18,
                pady=(0, 6),
                sticky="w"
            )

    def reset(self):
        self.vars["total"].set("0")
        self.vars["success"].set("0")
        self.vars["fail"].set("0")
        self.vars["success_rate"].set("0.00%")
        self.vars["qps"].set("0.00")
        self.vars["tps"].set("0.00")
        self.vars["avg_first_frame"].set("0.00 ms")
        self.vars["first_frame_p95"].set("0.00 ms")
        self.vars["avg_latency"].set("0.00 ms")
        self.vars["p95"].set("0.00 ms")

    def update_metrics(self, metrics):
        self.vars["total"].set(str(metrics["total"]))
        self.vars["success"].set(str(metrics["success_count"]))
        self.vars["fail"].set(str(metrics["fail_count"]))
        self.vars["success_rate"].set(format_rate(metrics["success_rate"]))
        self.vars["qps"].set(f"{metrics['qps']:.2f}")
        self.vars["tps"].set(f"{metrics['tps']:.2f}")
        self.vars["avg_first_frame"].set(format_ms(metrics["avg_first_frame_latency"]))
        self.vars["first_frame_p95"].set(format_ms(metrics["p95_first_frame_latency"]))
        self.vars["avg_latency"].set(format_ms(metrics["avg_latency"]))
        self.vars["p95"].set(format_ms(metrics["p95_latency"]))
