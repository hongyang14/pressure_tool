import csv
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from app.core.task_model import ScenarioStep
from app.utils.body_utils import normalize_body
from app.utils.json_utils import parse_headers


def render_template(value: str, context: Dict[str, Any]) -> str:
    if value is None:
        return ""

    result = str(value)
    builtin_values = {
        "uuid": str(uuid.uuid4()),
        "timestamp": str(int(time.time() * 1000)),
    }

    merged = dict(builtin_values)
    merged.update({k: "" if v is None else str(v) for k, v in context.items()})

    for key, replacement in merged.items():
        result = result.replace("{{" + key + "}}", replacement)

    return result


def render_headers(headers: Dict[str, str], context: Dict[str, Any]) -> Dict[str, str]:
    return {
        render_template(k, context): render_template(v, context)
        for k, v in headers.items()
    }


def load_user_data_rows(path: str) -> List[Dict[str, str]]:
    if not path:
        return []

    file_path = Path(path)
    if not file_path.is_file():
        raise ValueError(f"用户数据文件不存在：{path}")

    suffix = file_path.suffix.lower()
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("用户数据文件不能为空")

    if suffix == ".csv":
        rows = []
        with file_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({str(k): "" if v is None else str(v) for k, v in row.items()})
        return rows

    if suffix == ".jsonl":
        rows = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception as e:
                raise ValueError(f"用户数据文件第 {line_no} 行不是合法 JSON：{e}") from e
            if not isinstance(item, dict):
                raise ValueError(f"用户数据文件第 {line_no} 行必须是 JSON Object")
            rows.append({str(k): "" if v is None else str(v) for k, v in item.items()})
        return rows

    try:
        data = json.loads(text)
    except Exception as e:
        raise ValueError(f"用户数据文件不是合法 JSON：{e}") from e

    if not isinstance(data, list):
        raise ValueError("用户数据 JSON 文件必须是数组")

    rows = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"用户数据第 {index} 条必须是 JSON Object")
        rows.append({str(k): "" if v is None else str(v) for k, v in item.items()})
    return rows


def parse_scenario_steps(scenario_text: str, default_headers: Dict[str, str]) -> List[ScenarioStep]:
    scenario_text = scenario_text.strip()
    if not scenario_text:
        return []

    try:
        data = json.loads(scenario_text)
    except Exception as e:
        raise ValueError(f"场景 JSON 解析失败：{e}") from e

    if isinstance(data, dict):
        data = data.get("steps", [])

    if not isinstance(data, list):
        raise ValueError("场景配置必须是 JSON 数组，或包含 steps 数组的 JSON Object")

    steps = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"场景第 {index} 步必须是 JSON Object")

        name = str(item.get("name") or f"step-{index}")
        url = str(item.get("url") or "").strip()
        method = str(item.get("method") or "GET").strip().upper()
        if not url:
            raise ValueError(f"场景第 {index} 步 URL 不能为空")
        if method not in ["GET", "POST", "PUT", "DELETE", "GRPC"]:
            raise ValueError(f"场景第 {index} 步 Method 只支持 GET / POST / PUT / DELETE / GRPC")

        headers_value = item.get("headers")
        if headers_value is None:
            headers = dict(default_headers)
        elif isinstance(headers_value, dict):
            headers = {str(k): str(v) for k, v in headers_value.items()}
        else:
            headers = parse_headers(json.dumps(headers_value, ensure_ascii=False))

        body_value = item.get("body", "")
        if isinstance(body_value, (dict, list)):
            body = json.dumps(body_value, ensure_ascii=False)
        else:
            body = str(body_value or "")
        body = normalize_body(body, headers)

        extract = item.get("extract") or {}
        if not isinstance(extract, dict):
            raise ValueError(f"场景第 {index} 步 extract 必须是 JSON Object")

        steps.append(ScenarioStep(
            name=name,
            url=url,
            method=method,
            headers=headers,
            body=body,
            success_keyword=str(item.get("success_keyword") or ""),
            think_time_min=_safe_float(item.get("think_time_min"), 0),
            think_time_max=_safe_float(item.get("think_time_max"), 0),
            extract=extract,
            retry_count=max(_safe_int(item.get("retry_count"), 0), 0),
            retry_interval=max(_safe_float(item.get("retry_interval"), 0), 0),
            stop_on_failure=bool(item.get("stop_on_failure", True)),
        ))

    return steps


def extract_variables(extract_rules: Dict[str, Any], response_text: str, response_headers: Dict[str, str]) -> Dict[str, str]:
    values = {}
    for name, rule in extract_rules.items():
        value = _extract_one(rule, response_text, response_headers)
        if value is not None:
            values[str(name)] = str(value)
    return values


def _extract_one(rule: Any, response_text: str, response_headers: Dict[str, str]):
    if isinstance(rule, str):
        if rule.startswith("$."):
            return _extract_json_path(response_text, rule)
        return _extract_regex(response_text, rule)

    if not isinstance(rule, dict):
        return None

    if "json" in rule:
        return _extract_json_path(response_text, str(rule["json"]))
    if "regex" in rule:
        group = _safe_int(rule.get("group"), 1)
        return _extract_regex(response_text, str(rule["regex"]), group)
    if "header" in rule:
        wanted = str(rule["header"]).lower()
        for key, value in response_headers.items():
            if key.lower() == wanted:
                return value
    return None


def _extract_json_path(response_text: str, path: str):
    try:
        current = json.loads(response_text)
    except Exception:
        return None

    if not path.startswith("$."):
        return None

    tokens = _parse_json_path(path[2:])
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                return None
            current = current[token]
        else:
            if not isinstance(current, dict) or token not in current:
                return None
            current = current[token]
    return current


def _parse_json_path(path: str):
    tokens = []
    for part in path.split("."):
        match = re.fullmatch(r"([^\[]+)(?:\[(\d+)\])?", part)
        if not match:
            return []
        tokens.append(match.group(1))
        if match.group(2) is not None:
            tokens.append(int(match.group(2)))
    return tokens


def _extract_regex(response_text: str, pattern: str, group: int = 1):
    match = re.search(pattern, response_text)
    if not match:
        return None
    try:
        return match.group(group)
    except IndexError:
        return None


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default
