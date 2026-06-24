import base64
import hashlib
import importlib.util
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from app.core.result_model import RequestResult


def send_grpc_request(request_id, config, global_start_ts, body=None) -> RequestResult:
    start_perf = time.perf_counter()
    start_ts = time.time()

    status_code = None
    error = ""
    response_bytes = 0
    success = False
    request_body = config.body if body is None else body
    debug_info = ""

    try:
        import grpc

        target, method_path, secure = _parse_grpc_url(config.url)
        proto_method = None
        if config.proto_file:
            proto_method = _load_proto_method(config, method_path)
            method_path = proto_method["method_path"]
            payload = _encode_proto_payload(request_body, proto_method["request_class"])
            debug_info = (
                f"target={target}, method_path={method_path}, "
                f"request={proto_method['request_class'].DESCRIPTOR.full_name}, "
                f"response={proto_method['response_class'].DESCRIPTOR.full_name}, "
                f"server_streaming={proto_method['server_streaming']}, "
                f"payload_bytes={len(payload)}"
            )
        else:
            if not method_path or method_path.count("/") < 2:
                raise ValueError("未配置 Proto 文件时，gRPC 地址必须写完整：grpc://host:port/package.Service/Method")
            payload = _encode_raw_payload(request_body)
            debug_info = f"target={target}, method_path={method_path}, raw_payload_bytes={len(payload)}"

        metadata = _build_metadata(config.headers)

        channel = grpc.secure_channel(target, grpc.ssl_channel_credentials()) if secure else grpc.insecure_channel(target)
        try:
            response_bytes, response_text = _invoke_grpc(
                channel=channel,
                method_path=method_path,
                payload=payload,
                timeout=config.timeout,
                metadata=metadata,
                proto_method=proto_method,
            )
        finally:
            channel.close()

        status_code = 0

        biz_ok = True
        if config.success_keyword:
            biz_ok = config.success_keyword in response_text

        success = biz_ok
        if not biz_ok:
            error = "gRPC 响应内容未命中成功关键字"

    except ImportError as e:
        error = (
            "缺少 gRPC 依赖，无法执行 gRPC 请求。"
            "请安装 grpcio、grpcio-tools、protobuf 后重试。"
            f" 缺失信息：{e}"
        )

    except ValueError as e:
        error = str(e)

    except Exception as e:
        code = getattr(e, "code", lambda: None)()
        details = getattr(e, "details", lambda: "")()
        if code is not None:
            status_code = _grpc_code_number(code)
            error = f"GrpcError: {code.name if hasattr(code, 'name') else code}: {details}"
        else:
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
        debug_info=debug_info,
    )


def _parse_grpc_url(url):
    text = url.strip()
    if not text:
        raise ValueError("gRPC 地址不能为空")

    if "://" not in text:
        text = "grpc://" + text

    parts = urlsplit(text)
    if parts.scheme not in ["grpc", "grpcs", "http", "https"]:
        raise ValueError(
            "gRPC 地址格式应为 grpc://host:port。"
            f"当前填写的是：{url}"
        )

    target = parts.netloc
    method_path = parts.path
    if not target:
        raise ValueError(
            "gRPC 地址缺少 host:port，请填写类似 grpc://127.0.0.1:50051。"
            f"当前填写的是：{url}"
        )

    secure = parts.scheme in ["grpcs", "https"]
    return target, method_path, secure


def _invoke_grpc(channel, method_path, payload, timeout, metadata, proto_method):
    if proto_method and proto_method["server_streaming"]:
        stub = channel.unary_stream(
            method_path,
            request_serializer=lambda value: value,
            response_deserializer=lambda value: value,
        )
        raw_parts = []
        text_parts = []
        for raw in stub(payload, timeout=timeout, metadata=metadata):
            raw_parts.append(raw or b"")
            text_parts.append(_decode_response(raw or b"", proto_method))
        return sum(len(item) for item in raw_parts), "\n".join(text_parts)

    stub = channel.unary_unary(
        method_path,
        request_serializer=lambda value: value,
        response_deserializer=lambda value: value,
    )
    raw = stub(payload, timeout=timeout, metadata=metadata)
    return len(raw or b""), _decode_response(raw or b"", proto_method)


def _build_metadata(headers):
    metadata = []
    for key, value in headers.items():
        key = str(key).lower()
        if key in ["content-type", "te"]:
            continue
        metadata.append((key, str(value)))
    return metadata


def _encode_raw_payload(body):
    body = (body or "").strip()
    if not body:
        return b""

    try:
        obj = json.loads(body)
    except Exception:
        return body.encode("utf-8")

    if isinstance(obj, dict):
        if "payload_base64" in obj:
            return base64.b64decode(str(obj["payload_base64"]))
        if "payload_hex" in obj:
            return bytes.fromhex(str(obj["payload_hex"]))

    raise ValueError(
        "gRPC Body 需要填写原始 protobuf 载荷，支持 JSON 字段 payload_base64 或 payload_hex"
    )


def _encode_proto_payload(body, request_class):
    try:
        from google.protobuf import json_format
    except ImportError as e:
        raise ImportError("protobuf") from e

    body = (body or "").strip()
    if not body:
        message = request_class()
        return message.SerializeToString()

    try:
        data = json.loads(body)
    except Exception as e:
        raise ValueError(f"gRPC Body 必须是请求消息对应的 JSON：{e}") from e

    message = request_class()
    try:
        json_format.ParseDict(data, message, ignore_unknown_fields=True)
    except Exception as e:
        raise ValueError(
            f"gRPC Body 与请求消息 {request_class.DESCRIPTOR.full_name} 不匹配，"
            f"未知字段已自动忽略，剩余字段仍解析失败：{e}; "
            f"actual_body={_short_text(body)}"
        ) from e
    return message.SerializeToString()


def _decode_response(raw, proto_method):
    if not proto_method:
        return raw.decode("utf-8", errors="ignore")

    try:
        from google.protobuf import json_format
    except ImportError:
        return raw.decode("utf-8", errors="ignore")

    message = proto_method["response_class"]()
    message.ParseFromString(raw)
    return json_format.MessageToJson(message, ensure_ascii=False)


def _load_proto_method(config, method_path):
    try:
        from grpc_tools import protoc
        from google.protobuf import symbol_database
    except ImportError as e:
        raise ImportError("grpc_tools/protobuf") from e

    proto_path = Path(config.proto_file).resolve()
    if not proto_path.is_file():
        raise ValueError(f"Proto 文件不存在：{config.proto_file}")

    gen_dir = proto_path.parent / ".grpc_gen"
    gen_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(str(proto_path).encode("utf-8")).hexdigest()[:8]
    module_name = f"_grpc_gen_{proto_path.stem}_{cache_key}_pb2"
    module_path = gen_dir / f"{proto_path.stem}_pb2.py"

    proto_files = [str(path) for path in _collect_proto_dependencies(proto_path)]
    result = protoc.main([
        "grpc_tools.protoc",
        f"-I{proto_path.parent}",
        f"--python_out={gen_dir}",
        *proto_files,
    ])
    if result != 0:
        raise ValueError(f"Proto 编译失败：{proto_path}")

    if str(gen_dir) not in sys.path:
        sys.path.insert(0, str(gen_dir))

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"无法加载 Proto 生成文件：{module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    if config.grpc_service and config.grpc_method:
        service = _find_service(module.DESCRIPTOR, config.grpc_service)
        if service:
            method = service.methods_by_name.get(config.grpc_method)
            if not method:
                raise ValueError(f"服务 {service.full_name} 中找不到方法：{config.grpc_method}")
            return _method_info_from_descriptor(symbol_database.Default(), service, method)

        if config.grpc_request_message and config.grpc_response_message:
            service_name = config.grpc_service
            method_name = config.grpc_method
            request_class = _get_message_class(symbol_database.Default(), module.DESCRIPTOR, config.grpc_request_message)
            response_class = _get_message_class(symbol_database.Default(), module.DESCRIPTOR, config.grpc_response_message)
            return {
                "method_path": f"/{service_name}/{method_name}",
                "request_class": request_class,
                "response_class": response_class,
                "server_streaming": config.grpc_server_streaming,
                "client_streaming": False,
            }

        raise ValueError(f"Proto 中找不到服务：{config.grpc_service}")

    if method_path and method_path.count("/") >= 2:
        service_name, method_name = _split_method_path(method_path)
        service = _find_service(module.DESCRIPTOR, service_name)
        if not service:
            raise ValueError(f"Proto 中找不到服务：{service_name}")

        method = service.methods_by_name.get(method_name)
        if not method:
            raise ValueError(f"服务 {service.full_name} 中找不到方法：{method_name}")
    else:
        service, method = _default_service_method(module.DESCRIPTOR)

    return _method_info_from_descriptor(symbol_database.Default(), service, method)


def _method_info_from_descriptor(sym_db, service, method):
    request_class = sym_db.GetSymbol(method.input_type.full_name)
    response_class = sym_db.GetSymbol(method.output_type.full_name)

    return {
        "method_path": f"/{service.full_name}/{method.name}",
        "request_class": request_class,
        "response_class": response_class,
        "server_streaming": method.server_streaming,
        "client_streaming": method.client_streaming,
    }


def _get_message_class(sym_db, descriptor, message_name):
    full_name = message_name if "." in message_name else f"{descriptor.package}.{message_name}"
    try:
        return sym_db.GetSymbol(full_name)
    except KeyError as e:
        raise ValueError(f"Proto 中找不到消息类型：{message_name}") from e


def _collect_proto_dependencies(entry_path):
    root = entry_path.parent
    seen = set()
    ordered = []

    def visit(path):
        path = path.resolve()
        if path in seen:
            return
        seen.add(path)

        if not path.is_file():
            raise ValueError(f"Proto import 文件不存在：{path}")

        text = path.read_text(encoding="utf-8")
        for import_name in re.findall(r'^\s*import\s+(?:public\s+|weak\s+)?"([^"]+)"\s*;', text, re.MULTILINE):
            visit(root / import_name)

        ordered.append(path)

    visit(entry_path)
    return ordered


def _split_method_path(method_path):
    parts = [part for part in method_path.split("/") if part]
    if len(parts) != 2:
        raise ValueError("gRPC 地址格式应为 grpc://host:port/package.Service/Method")
    return parts[0], parts[1]


def _find_service(descriptor, service_name):
    for service in descriptor.services_by_name.values():
        if service.full_name == service_name or service.name == service_name:
            return service
    return None


def _default_service_method(descriptor):
    services = list(descriptor.services_by_name.values())
    if not services:
        raise ValueError(
            "Proto 中没有 service 定义，无法自动选择 gRPC 方法。"
            "请在 interfaces.txt 的该接口下补充 service、rpc、request、response，"
            "例如：service: package.ServiceName，rpc: MethodName，request: RequestMessage，response: ResponseMessage。"
        )

    service = services[0]
    methods = list(service.methods_by_name.values())
    if not methods:
        raise ValueError(f"服务 {service.full_name} 中没有 rpc 方法")

    return service, methods[0]


def _grpc_code_number(code):
    value = getattr(code, "value", None)
    if isinstance(value, tuple) and value:
        return value[0]
    if isinstance(value, int):
        return value
    return None


def _short_text(text, limit=500):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit] + "..."
