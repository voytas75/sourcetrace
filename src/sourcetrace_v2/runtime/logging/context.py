from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoggingContext:
    job_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    call_site: str | None = None
    feature: str | None = None
    receipt_id: str | None = None
    provider: str | None = None
    model: str | None = None
    event_name: str | None = None

    def as_extra(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        for key, value in self.__dict__.items():
            if value is not None:
                payload[key] = value
        return payload
