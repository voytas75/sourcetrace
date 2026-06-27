from __future__ import annotations

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "event_name": getattr(record, "event_name", None),
            "job_id": getattr(record, "job_id", None),
            "run_id": getattr(record, "run_id", None),
            "stage_id": getattr(record, "stage_id", None),
            "call_site": getattr(record, "call_site", None),
            "receipt_id": getattr(record, "receipt_id", None),
            "provider": getattr(record, "provider", None),
            "model": getattr(record, "model", None),
            "feature": getattr(record, "feature", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
