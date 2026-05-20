"""Reusable end-to-end smoke flow for the local Sourcetrace WWW API."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def _build_expectations(*, minimum_claims: int) -> dict[str, object]:
    return {
        "create_case_status": "ready",
        "create_document_status": "ready",
        "document_has_inline_content": True,
        "prepare_status": "ready",
        "prepare_chunk_count": 1,
        "extract_status": "ready",
        "extract_claim_count_min": minimum_claims,
        "credibility_status": "ready",
        "credibility_has_summary": True,
        "html_has_snippet": True,
        "html_has_summary": True,
    }


def _validate_report(report: dict[str, Any], *, minimum_claims: int) -> list[str]:
    checks = report["checks"]
    failures: list[str] = []
    expected = _build_expectations(minimum_claims=minimum_claims)
    for key, value in expected.items():
        if key == "extract_claim_count_min":
            actual_claim_count = int(checks["extract_claim_count"])
            expected_minimum = int(minimum_claims)
            if actual_claim_count < expected_minimum:
                failures.append(
                    f"extract_claim_count={actual_claim_count} < expected_min={expected_minimum}"
                )
            continue
        if checks.get(key) != value:
            failures.append(f"{key}={checks.get(key)!r} != expected {value!r}")
    return failures


def _request_json(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(base_url + path, data=data, headers=headers, method=method)
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_text(base_url: str, path: str) -> str:
    with urlopen(base_url + path, timeout=20) as response:
        return response.read().decode("utf-8")


def run_smoke_flow(base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    case_payload = _request_json(
        base_url,
        "POST",
        "/api/cases",
        {
            "title": "Smoke flow continuity case",
            "description": "Reusable smoke for continuity/extract/credibility/html.",
        },
    )
    case_id = str(case_payload["case_id"])

    document_payload = _request_json(
        base_url,
        "POST",
        f"/api/cases/{case_id}/documents",
        {
            "title": "Smoke flow inline document",
            "text": (
                "OpenAI announced a major partnership with Example University to improve AI "
                "safety research. The announcement described a multi-year research program "
                "and related governance commitments."
            ),
            "source_type": "web_article",
            "source_url": "https://example.test/smoke-flow-inline",
            "content_hash": "sha256:smoke-flow-inline",
        },
    )
    document_id = str(document_payload["document_id"])

    prepare_payload = _request_json(
        base_url,
        "POST",
        f"/api/documents/{document_id}/prepare",
        {},
    )
    extract_payload = _request_json(
        base_url,
        "POST",
        f"/api/documents/{document_id}/extract-claims",
        {"extraction_method": "llm_v1"},
    )
    credibility_payload = _request_json(
        base_url,
        "POST",
        f"/api/documents/{document_id}/credibility",
        {},
    )
    html = _request_text(base_url, f"/cases/{case_id}")

    return {
        "case_id": case_id,
        "document_id": document_id,
        "checks": {
            "create_case_status": case_payload["status"],
            "create_document_status": document_payload["status"],
            "document_has_inline_content": document_payload["document"]["has_inline_content"],
            "prepare_status": prepare_payload["status"],
            "prepare_chunk_count": prepare_payload["diagnostics"]["chunk_count"],
            "extract_status": extract_payload["status"],
            "extract_claim_count": extract_payload["diagnostics"]["claim_count"],
            "credibility_status": credibility_payload["status"],
            "credibility_has_summary": bool(
                credibility_payload["credibility_assessment"].get("summary")
            ),
            "html_has_snippet": "Snippet:" in html,
            "html_has_summary": "Summary:" in html,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the reusable Sourcetrace WWW smoke flow.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--expect-claims-min", type=int, default=1)
    args = parser.parse_args(argv)

    report = run_smoke_flow(base_url=args.base_url)
    failures = _validate_report(report, minimum_claims=args.expect_claims_min)
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False))
    if failures:
        print(
            json.dumps({"status": "failed", "failures": failures}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
