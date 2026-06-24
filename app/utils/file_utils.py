import os
import platform
import subprocess
from pathlib import Path


def ensure_dir(path: str):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def open_folder(path: str):
    folder = ensure_dir(path).resolve()
    folder_str = str(folder)

    system = platform.system()
    if system == "Windows":
        os.startfile(folder_str)
    elif system == "Darwin":
        subprocess.run(["open", folder_str], check=False)
    else:
        subprocess.run(["xdg-open", folder_str], check=False)


def list_report_files(path: str):
    report_dir = Path(path)
    if not report_dir.is_dir():
        return []

    return [f for f in report_dir.glob("pressure_report_*") if f.is_file()]


def clear_report_files(path: str) -> int:
    count = 0
    for file_path in list_report_files(path):
        file_path.unlink()
        count += 1
    return count