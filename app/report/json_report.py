import json
from dataclasses import asdict

from app.utils.time_utils import now_str


def write_json_report(results, metrics, json_path):
    payload = {
        "generated_at": now_str(),
        "metrics": metrics,
        "results": [asdict(r) for r in results],
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)