import socket
import time
import urllib.error
import urllib.request
from datetime import datetime

from app.core.grpc_client import send_grpc_request
from app.core.result_model import RequestResult
from app.utils.url_utils import encode_url


def build_request(url, method, headers, body):
    method = method.upper()

    # URL 中如果有中文，先编码
    url = encode_url(url)

    data = None

    # 只要 Body 不为空，就用 UTF-8 编码发送
    if body:
        data = body.encode("utf-8")

        if not any(k.lower() == "content-type" for k in headers.keys()):
            headers["Content-Type"] = "application/json; charset=utf-8"

    return urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method
    )


def send_one_request(request_id, config, global_start_ts, body=None) -> RequestResult:
    if config.method.upper() == "GRPC":
        return send_grpc_request(
            request_id=request_id,
            config=config,
            global_start_ts=global_start_ts,
            body=body,
        )

    start_perf = time.perf_counter()
    start_ts = time.time()

    status_code = None
    error = ""
    response_text = ""
    response_bytes = 0
    success = False
    request_body = config.body if body is None else body

    try:
        req = build_request(
            url=config.url,
            method=config.method,
            headers=dict(config.headers),
            body=request_body,
        )

        with urllib.request.urlopen(req, timeout=config.timeout) as resp:
            status_code = resp.getcode()
            raw = resp.read()
            response_bytes = len(raw)
            response_text = raw.decode("utf-8", errors="ignore")

        http_ok = 200 <= int(status_code) < 300
        biz_ok = True

        if config.success_keyword:
            biz_ok = config.success_keyword in response_text

        success = http_ok and biz_ok

        if http_ok and not biz_ok:
            error = "响应内容未命中成功关键字"

    except urllib.error.HTTPError as e:
        status_code = e.code
        error = f"HTTPError: {e}"

        try:
            raw = e.read()
            response_bytes = len(raw)
            response_text = raw.decode("utf-8", errors="ignore")
            if response_text:
                error = f"{error}; response={_short_text(response_text)}"
        except Exception:
            pass

    except urllib.error.URLError as e:
        error = f"URLError: {e}"

    except socket.timeout:
        error = "Timeout"

    except UnicodeEncodeError as e:
        error = (
            f"UnicodeEncodeError: {e}. "
            f"请检查 URL 或 Headers 中是否包含中文。"
            f"中文业务参数请放在 Body 中。"
        )

    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    end_ts = time.time()
    latency_ms = (time.perf_counter() - start_perf) * 1000

    return RequestResult(
        request_id=request_id,
        success=success,
        status_code=status_code,
        error=error,
        latency_ms=latency_ms,
        response_bytes=response_bytes,
        start_time=datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        end_time=datetime.fromtimestamp(end_ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        relative_end_second=int(end_ts - global_start_ts),
    )


def _short_text(text, limit=300):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit] + "..."
