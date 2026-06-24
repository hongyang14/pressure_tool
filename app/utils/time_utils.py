from datetime import datetime


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def format_ms(value):
    return f"{value:.2f} ms"


def format_rate(value):
    return f"{value:.2f}%"