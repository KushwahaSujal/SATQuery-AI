import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """Formats log records as structured JSON or readable strings."""
    def __init__(self, is_json: bool = True):
        super().__init__()
        self.is_json = is_json

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            payload["request_id"] = getattr(record, "request_id")
        if hasattr(record, "extra_data"):
            payload["data"] = getattr(record, "extra_data")
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        if self.is_json:
            return json.dumps(payload)
        return f"[{payload['timestamp']}] [{payload['level']}] {record.name}: {payload['message']}"


def setup_logger(name: str = "satquery", level: str = "INFO", structured_json: bool = False) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter(is_json=structured_json))
        logger.addHandler(handler)

    return logger


logger = setup_logger()
