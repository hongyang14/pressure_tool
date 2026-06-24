import json
import re
from pathlib import Path


def ensure_sample_interface_file(path: str):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.exists():
        return

    file_path.write_text(
        """# 每个接口用 --- 分隔，key=value 或 key: value 都可以。
# headers/body 支持多行 JSON，分别用 headers: 和 body: 起始。

---
name: 示例 POST 接口
method: POST
url: http://127.0.0.1:8000/predict
headers:
{
  "Content-Type": "application/json; charset=utf-8"
}
body:
{
  "text": "hello"
}

---
name: 示例 gRPC Chat
method: GRPC
url: grpc://127.0.0.1:50051
proto: intend.proto
body:
{
  "header": {
    "dialogId": "d1",
    "deviceId": "dev1",
    "roundId": "r1",
    "round": 1,
    "userId": "u1",
    "traceId": "t1"
  },
  "body": {
    "text": "你好",
    "msgSource": "glasses"
  }
}
""",
        encoding="utf-8",
    )


def load_interfaces(path: str, proto_dir: str = ""):
    file_path = Path(path)
    if not file_path.is_file():
        return []

    text = file_path.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^\s*---\s*$", text)
    interfaces = []

    for block in blocks:
        item = _parse_block(block)
        if not item:
            continue

        name = item.get("name") or item.get("接口") or item.get("title")
        method = (item.get("method") or item.get("类型") or "").upper()
        url = item.get("url") or item.get("地址") or ""
        if not name or not method or not url:
            continue

        proto = item.get("proto") or item.get("proto_file") or item.get("protobuf") or ""
        if not proto and method == "GRPC":
            proto = _first_proto_file(proto_dir)
        if proto and proto_dir:
            proto_path = Path(proto)
            if not proto_path.is_absolute():
                proto = str(Path(proto_dir) / proto_path)

        interfaces.append({
            "name": name,
            "method": method,
            "url": url,
            "headers": _normalize_json_text(item.get("headers") or "{}"),
            "body": _normalize_json_text(item.get("body") or ""),
            "success_keyword": item.get("success_keyword") or item.get("成功关键字") or "",
            "proto_file": proto,
            "grpc_service": item.get("service") or item.get("grpc_service") or "",
            "grpc_method": item.get("rpc") or item.get("grpc_method") or "",
            "grpc_request_message": item.get("request") or item.get("request_message") or "",
            "grpc_response_message": item.get("response") or item.get("response_message") or "",
            "grpc_server_streaming": _to_bool(item.get("server_streaming") or item.get("stream") or ""),
        })

    return interfaces


def _parse_block(block: str):
    lines = block.splitlines()
    data = {}
    current_key = None
    current_lines = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = re.match(r"^([A-Za-z_][\w\-]*|[\u4e00-\u9fff]+)\s*[:=]\s*(.*)$", stripped)
        if match:
            if current_key:
                data[current_key] = "\n".join(current_lines).strip()

            key = match.group(1).strip().lower().replace("-", "_")
            value = match.group(2).strip()
            current_key = key
            current_lines = [value] if value else []
        elif current_key:
            current_lines.append(line)

    if current_key:
        data[current_key] = "\n".join(current_lines).strip()

    return data


def _normalize_json_text(text: str):
    text = (text or "").strip()
    if not text:
        return ""

    try:
        obj = json.loads(text)
    except Exception:
        return text

    return json.dumps(obj, ensure_ascii=False, indent=2)


def _first_proto_file(proto_dir: str):
    if not proto_dir:
        return ""

    path = Path(proto_dir)
    if not path.is_dir():
        return ""

    files = sorted(path.glob("*.proto"))
    if not files:
        return ""

    return files[0].name


def _to_bool(value):
    return str(value).strip().lower() in ["1", "true", "yes", "y", "是", "stream", "server_streaming"]
