"""Small live smoke for the Sourcetrace credibility API contract."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


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


def run_credibility_smoke(base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    case_id = "smoke-credibility-contract"
    document_id = "smoke-credibility-contract-doc"

    _request_json(
        base_url,
        "POST",
        "/api/cases",
        {
            "case_id": case_id,
            "title": "Credibility smoke contract",
            "summary": "Small smoke for POST/GET credibility payload contract.",
            "created_by": "smoke",
        },
    )
    _request_json(
        base_url,
        "POST",
        f"/api/cases/{case_id}/documents",
        {
            "document_id": document_id,
            "title": "BBC borrowing smoke doc",
            "source_type": "url",
            "source_url": "https://www.bbc.com/news/articles/ce9py7nx8j4o",
            "publisher": "BBC",
            "published_at": "2026-05-24T00:00:00Z",
            "text": (
                "UK public sector borrowing in April hit £24.3bn, the highest April total since the Covid pandemic in 2020. "
                "Borrowing was £4.9bn higher than a year earlier and above expectations. "
                "Retail sales volumes fell 1.3% in April after a jump in petrol prices hit fuel demand."
            ),
        },
    )
    _request_json(base_url, "POST", f"/api/documents/{document_id}/prepare", {})
    post_payload = _request_json(base_url, "POST", f"/api/documents/{document_id}/credibility", {})
    get_payload = _request_json(base_url, "GET", f"/api/documents/{document_id}/credibility")

    post_assessment = post_payload.get("credibility_assessment") or {}
    get_assessment = get_payload.get("credibility_assessment") or {}

    return {
        "case_id": case_id,
        "document_id": document_id,
        "checks": {
            "post_status": post_payload.get("status"),
            "get_status": get_payload.get("status"),
            "post_has_credibility_assessment": isinstance(post_payload.get("credibility_assessment"), dict),
            "get_has_credibility_assessment": isinstance(get_payload.get("credibility_assessment"), dict),
            "post_source_reliability": post_assessment.get("source_reliability"),
            "get_source_reliability": get_assessment.get("source_reliability"),
            "post_information_credibility": post_assessment.get("information_credibility"),
            "get_information_credibility": get_assessment.get("information_credibility"),
            "post_provenance_distance": post_assessment.get("provenance_distance"),
            "get_provenance_distance": get_assessment.get("provenance_distance"),
            "post_get_match": post_assessment == get_assessment,
        },
    }


def _validate_report(report: dict[str, Any]) -> list[str]:
    checks = report["checks"]
    failures: list[str] = []
    if checks["post_status"] != "ready":
        failures.append(f"post_status={checks['post_status']!r} != 'ready'")
    if checks["get_status"] != "ready":
        failures.append(f"get_status={checks['get_status']!r} != 'ready'")
    if not checks["post_has_credibility_assessment"]:
        failures.append("post_has_credibility_assessment is false")
    if not checks["get_has_credibility_assessment"]:
        failures.append("get_has_credibility_assessment is false")
    if not checks["post_source_reliability"]:
        failures.append("post_source_reliability missing")
    if not checks["get_source_reliability"]:
        failures.append("get_source_reliability missing")
    if not checks["post_information_credibility"]:
        failures.append("post_information_credibility missing")
    if not checks["get_information_credibility"]:
        failures.append("get_information_credibility missing")
    if not checks["post_provenance_distance"]:
        failures.append("post_provenance_distance missing")
    if not checks["get_provenance_distance"]:
        failures.append("get_provenance_distance missing")
    if not checks["post_get_match"]:
        failures.append("post_get_match is false")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a small Sourcetrace credibility API smoke.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = run_credibility_smoke(base_url=args.base_url)
    failures = _validate_report(report)
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False))
    if failures:
        print(json.dumps({"status": "failed", "failures": failures}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
