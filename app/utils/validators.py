from pathlib import Path

from app.core.task_model import RUN_MODE_DURATION, RUN_MODE_REQUESTS, PressureTaskConfig
from app.utils.body_param_utils import load_body_templates
from app.utils.json_utils import parse_headers
from app.utils.body_utils import normalize_body


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def validate_task_config(raw: dict) -> PressureTaskConfig:
    url = raw.get("url", "").strip()
    method = raw.get("method", "").strip().upper()
    headers_text = raw.get("headers_text", "")
    body = raw.get("body", "").strip()
    concurrency = safe_int(raw.get("concurrency"), 0)
    total_requests = safe_int(raw.get("total_requests"), 0)
    timeout = safe_float(raw.get("timeout"), 0)
    ramp_up = safe_float(raw.get("ramp_up"), 0)
    success_keyword = raw.get("success_keyword", "").strip()
    output_dir = raw.get("output_dir", "").strip()
    run_mode = raw.get("run_mode", RUN_MODE_REQUESTS).strip()
    duration_seconds = safe_float(raw.get("duration_seconds"), 0)
    think_time_min = safe_float(raw.get("think_time_min"), 0)
    think_time_max = safe_float(raw.get("think_time_max"), 0)
    body_data_file = raw.get("body_data_file", "").strip()
    body_data_dir = raw.get("body_data_dir", "").strip()
    proto_file = raw.get("proto_file", "").strip()
    proto_dir = raw.get("proto_dir", "").strip()
    grpc_service = raw.get("grpc_service", "").strip()
    grpc_method = raw.get("grpc_method", "").strip()
    grpc_request_message = raw.get("grpc_request_message", "").strip()
    grpc_response_message = raw.get("grpc_response_message", "").strip()
    grpc_server_streaming = bool(raw.get("grpc_server_streaming", False))

    if not url:
        raise ValueError("接口 URL 不能为空")

    if method not in ["GET", "POST", "PUT", "DELETE", "GRPC"]:
        raise ValueError("请求方法只支持 GET / POST / PUT / DELETE / GRPC")

    if run_mode not in [RUN_MODE_REQUESTS, RUN_MODE_DURATION]:
        raise ValueError("压测模式不支持")

    if concurrency <= 0:
        raise ValueError("并发数必须大于 0")

    if run_mode == RUN_MODE_REQUESTS:
        if total_requests <= 0:
            raise ValueError("总请求数必须大于 0")
        if concurrency > total_requests:
            concurrency = total_requests
    else:
        if duration_seconds <= 0:
            raise ValueError("按时长压测时，持续时长必须大于 0")
        total_requests = 0

    if timeout <= 0:
        raise ValueError("超时时间必须大于 0")

    if ramp_up < 0:
        raise ValueError("Ramp-up 时间不能小于 0")

    if think_time_min < 0 or think_time_max < 0:
        raise ValueError("思考时间不能小于 0")

    if think_time_max < think_time_min:
        raise ValueError("思考时间最大值不能小于最小值")

    if not output_dir:
        raise ValueError("报告输出目录不能为空")

    headers = parse_headers(headers_text)
    body = normalize_body(body, headers)

    body_templates = []
    if body_data_file:
        body_data_file = resolve_body_data_file(body_data_file, body_data_dir)
        body_templates = load_body_templates(body_data_file)
        body_templates = [
            normalize_body(template, headers)
            for template in body_templates
        ]

    if proto_file:
        proto_file = resolve_proto_file(proto_file, proto_dir)
        if not Path(proto_file).is_file():
            raise ValueError(f"Proto 文件不存在：{proto_file}")

    return PressureTaskConfig(
        url=url,
        method=method,
        headers=headers,
        body=body,
        concurrency=concurrency,
        total_requests=total_requests,
        timeout=timeout,
        ramp_up=ramp_up,
        success_keyword=success_keyword,
        output_dir=output_dir,
        run_mode=run_mode,
        duration_seconds=duration_seconds,
        think_time_min=think_time_min,
        think_time_max=think_time_max,
        body_data_file=body_data_file,
        body_templates=body_templates,
        proto_file=proto_file,
        grpc_service=grpc_service,
        grpc_method=grpc_method,
        grpc_request_message=grpc_request_message,
        grpc_response_message=grpc_response_message,
        grpc_server_streaming=grpc_server_streaming,
    )


def resolve_body_data_file(body_data_file: str, body_data_dir: str = "") -> str:
    file_path = Path(body_data_file)
    if file_path.is_absolute():
        return str(file_path)

    if body_data_dir:
        return str(Path(body_data_dir) / file_path)

    return str(file_path)


def resolve_proto_file(proto_file: str, proto_dir: str = "") -> str:
    file_path = Path(proto_file)
    if file_path.is_absolute():
        return str(file_path)

    if proto_dir:
        return str(Path(proto_dir) / file_path)

    return str(file_path)
