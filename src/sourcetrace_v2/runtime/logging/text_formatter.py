from __future__ import annotations

import logging


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = f"[{record.levelname}] {record.name}: {record.getMessage()}"
        job_id = getattr(record, "job_id", None)
        run_id = getattr(record, "run_id", None)
        stage_id = getattr(record, "stage_id", None)
        extras = [value for value in (job_id, run_id, stage_id) if value]
        if extras:
            return f"{base} ({' | '.join(extras)})"
        return base
