import tkinter as tk
from tkinter import ttk

from app.utils.time_utils import now_str


class LogPanel(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="运行日志", padding=6)

        self.text = tk.Text(self, height=16)
        self.text.pack(fill=tk.BOTH, expand=True)

    def clear(self):
        self.text.delete("1.0", tk.END)

    def info(self, message):
        self.text.insert(tk.END, f"[{now_str()}] {message}\n")
        self.text.see(tk.END)

    def error(self, message):
        self.info(f"[ERROR] {message}")