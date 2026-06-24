import json


def is_json_content_type(headers: dict) -> bool:
    content_type = ""

    for k, v in headers.items():
        if str(k).lower() == "content-type":
            content_type = str(v).lower()
            break

    return "application/json" in content_type


def normalize_body(body_text: str, headers: dict) -> str:
    """
    处理请求体：
    1. 如果是 application/json，则校验 JSON 合法性；
    2. 重新 dump，保证中文不被错误转义；
    3. 如果不是 JSON，则原样返回。
    """
    body_text = body_text.strip()

    if not body_text:
        return ""

    if is_json_content_type(headers):
        try:
            obj = json.loads(body_text)
        except Exception as e:
            raise ValueError(f"Body 不是合法 JSON：{e}")

        return json.dumps(obj, ensure_ascii=False)

    return body_text