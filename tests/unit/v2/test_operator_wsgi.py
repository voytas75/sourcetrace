from __future__ import annotations

import json
from io import BytesIO

from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.operator import www


def _request(app, body: bytes) -> tuple[str, dict[str, object]]:
    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = dict(headers)

    response = app(
        {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/v2/run",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": BytesIO(body),
        },
        start_response,
    )
    return str(captured["status"]), json.loads(b"".join(response).decode("utf-8"))


def test_run_endpoint_rejects_malformed_or_non_object_json(monkeypatch) -> None:
    monkeypatch.setattr(www, "_runtime", build_stubbed_memory_runtime)
    app = www.build_wsgi_app()

    malformed_status, malformed_payload = _request(app, b"{")
    non_object_status, non_object_payload = _request(app, b"[]")

    assert malformed_status == "400 Bad Request"
    assert malformed_payload == {"error": "invalid_json"}
    assert non_object_status == "400 Bad Request"
    assert non_object_payload == {"error": "invalid_json"}
