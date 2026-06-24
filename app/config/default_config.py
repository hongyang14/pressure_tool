from pathlib import Path

DEFAULT_URL = "http://127.0.0.1:8000/predict"
DEFAULT_METHOD = "POST"
DEFAULT_CONCURRENCY = 10
DEFAULT_TOTAL_REQUESTS = 100
DEFAULT_TIMEOUT = 10
DEFAULT_RAMP_UP = 0
DEFAULT_RUN_MODE = "requests"
DEFAULT_DURATION_SECONDS = 60
DEFAULT_THINK_TIME_MIN = 0
DEFAULT_THINK_TIME_MAX = 0
DEFAULT_BODY_DATA_FILE = ""
DEFAULT_PROTO_FILE = ""
DEFAULT_SUCCESS_KEYWORD = ""

DEFAULT_OUTPUT_DIR = str(Path.cwd() / "reports")
DEFAULT_BODY_DATA_DIR = str(Path.cwd() / "body_data")
DEFAULT_PROTO_DIR = str(Path.cwd() / "proto_files")
DEFAULT_INTERFACE_DIR = str(Path.cwd() / "interfaces")
DEFAULT_INTERFACE_FILE = str(Path.cwd() / "interfaces" / "interfaces.txt")

DEFAULT_HEADERS_TEXT = """{
  "Content-Type": "application/json; charset=utf-8"
}"""

DEFAULT_BODY_TEXT = """{
  "sourceContent": [
    {
      "clipId": "demo-001",
      "clipType": "speech",
      "speakerType": "other",
      "speakerName": "Speaker 1",
      "startTime": 1775620800000,
      "endTime": 1775621262000,
      "content": "这里填写你的中文请求体内容",
      "translateContent": ""
    }
  ]
}"""
