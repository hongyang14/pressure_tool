import json


def _check_header_latin1(headers: dict):
    """
    HTTP Header 不建议放中文。
    urllib/http.client 在发送 Header 时会按 latin-1 编码。
    如果 Header 里有中文，会触发 UnicodeEncodeError。
    """
    for k, v in headers.items():
        try:
            str(k).encode("latin-1")
            str(v).encode("latin-1")
        except UnicodeEncodeError:
            raise ValueError(
                f"Header 中包含非 latin-1 字符，可能是中文：{k}: {v}\n"
                f"请不要把中文放在 Header 中，中文参数建议放到 Body 或 URL query 中。"
            )


def parse_headers(headers_text: str):
    headers_text = headers_text.strip()

    if not headers_text:
        return {}

    try:
        obj = json.loads(headers_text)
    except Exception as e:
        raise ValueError(f"Headers JSON 解析失败：{e}")

    if not isinstance(obj, dict):
        raise ValueError("Headers 必须是 JSON Object，例如：{\"Content-Type\": \"application/json\"}")

    headers = {str(k): str(v) for k, v in obj.items()}

    _check_header_latin1(headers)

    return headers