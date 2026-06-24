from dataclasses import dataclass
from typing import Optional


@dataclass
class RequestResult:
    request_id: int
    success: bool
    status_code: Optional[int]
    error: str
    latency_ms: float
    response_bytes: int
    start_time: str
    end_time: str
    relative_end_second: int
    body_template_index: Optional[int] = None
    body_template_label: str = ""
    debug_info: str = ""
