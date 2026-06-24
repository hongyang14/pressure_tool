from dataclasses import dataclass, field
from typing import Dict, List


RUN_MODE_REQUESTS = "requests"
RUN_MODE_DURATION = "duration"


@dataclass
class ScenarioStep:
    name: str
    url: str
    method: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    success_keyword: str = ""
    think_time_min: float = 0
    think_time_max: float = 0
    extract: Dict[str, object] = field(default_factory=dict)
    retry_count: int = 0
    retry_interval: float = 0
    stop_on_failure: bool = True


@dataclass
class PressureTaskConfig:
    url: str
    method: str
    headers: Dict[str, str]
    body: str
    concurrency: int
    total_requests: int
    timeout: float
    ramp_up: float
    success_keyword: str
    output_dir: str
    run_mode: str = RUN_MODE_REQUESTS
    duration_seconds: float = 0
    think_time_min: float = 0
    think_time_max: float = 0
    body_data_file: str = ""
    body_templates: List[str] = field(default_factory=list)
    proto_file: str = ""
    grpc_service: str = ""
    grpc_method: str = ""
    grpc_request_message: str = ""
    grpc_response_message: str = ""
    grpc_server_streaming: bool = False
    scenario_steps: List[ScenarioStep] = field(default_factory=list)
    user_data_file: str = ""
    user_data_rows: List[Dict[str, str]] = field(default_factory=list)
