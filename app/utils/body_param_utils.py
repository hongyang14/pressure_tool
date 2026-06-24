import json
import random
import time
import uuid
from pathlib import Path


def load_body_templates(path: str) -> list[str]:
    file_path = Path(path)
    if not file_path.is_file():
        raise ValueError(f"Body 数据文件不存在：{path}")

    suffix = file_path.suffix.lower()
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("Body 数据文件不能为空")

    templates = []

    if suffix == ".jsonl":
        for line_no, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            templates.append(_normalize_template_item(line, line_no))
    else:
        try:
            data = json.loads(text)
        except Exception as e:
            raise ValueError(f"Body 数据文件不是合法 JSON：{e}") from e

        if not isinstance(data, list):
            raise ValueError("Body 数据文件必须是 JSON 数组，或使用 .jsonl 格式")

        for index, item in enumerate(data, start=1):
            templates.append(_normalize_template_item(item, index))

    if not templates:
        raise ValueError("Body 数据文件中没有可用的请求体")

    return templates


def _normalize_template_item(item, index) -> str:
    if isinstance(item, str):
        body = item.strip()
        if not body:
            raise ValueError(f"第 {index} 条 Body 为空")
        return body

    if isinstance(item, dict):
        return json.dumps(item, ensure_ascii=False)

    raise ValueError(f"第 {index} 条 Body 格式不支持，请使用 JSON 对象或字符串")


def apply_placeholders(template: str, request_id: int) -> str:
    replacements = {
        "{{request_id}}": str(request_id),
        "{{uuid}}": str(uuid.uuid4()),
        "{{timestamp}}": str(int(time.time() * 1000)),
        "{{index}}": str(request_id),
    }

    body = template
    for key, value in replacements.items():
        body = body.replace(key, value)
    return body


def resolve_request_body_info(config, request_id: int):
    if config.body_templates:
        if config.run_mode == "duration":
            index = random.randrange(len(config.body_templates))
        else:
            index = (request_id - 1) % len(config.body_templates)
        template = config.body_templates[index]
        body_template_index = index + 1
    else:
        template = config.body
        body_template_index = None

    return {
        "body": apply_placeholders(template, request_id),
        "body_template_index": body_template_index,
        "body_template_label": f"Body #{body_template_index}" if body_template_index else "",
    }


def resolve_request_body(config, request_id: int) -> str:
    return resolve_request_body_info(config, request_id)["body"]
