import csv
from dataclasses import asdict


def write_csv_report(results, csv_path):
    fieldnames = [
        "request_id",
        "success",
        "status_code",
        "error",
        "latency_ms",
        "first_frame_latency_ms",
        "response_bytes",
        "start_time",
        "end_time",
        "relative_end_second",
        "body_template_index",
        "body_template_label",
        "debug_info",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            writer.writerow(asdict(r))
