from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    content_type: str
    body: str


def json_response(payload: dict[str, object], *, status_code: int = 200) -> HttpResponse:
    return HttpResponse(
        status_code=status_code,
        content_type="application/json; charset=utf-8",
        body=json.dumps(payload, ensure_ascii=False),
    )
