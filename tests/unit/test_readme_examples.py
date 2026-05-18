from pathlib import Path


README_PATH = Path(__file__).resolve().parents[2] / "README.md"


def test_readme_documents_local_web_smoke_examples() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "## Local smoke flow" in readme
    assert "uv run python -m sourcetrace.web" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/verify" in readme
    assert "Expected: `200 OK` with JSON containing `verification.verdict`" in readme
    assert "Expected: `200 OK` with JSON containing `evidence_links` and `evidence_summary`" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/reviews" in readme
    assert "Expected: `200 OK` with JSON containing the persisted review payload" in readme
    assert "curl http://127.0.0.1:8000/api/claims/claim-1/verification" in readme
    assert "curl http://127.0.0.1:8000/api/reports/case-1.md" in readme
    assert "Expected: `200 OK` with `Content-Type: text/markdown; charset=utf-8`" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/documents/doc-1/credibility" in readme
    assert "Expected: `200 OK` with JSON containing `credibility_assessment.notes`" in readme
    assert "## Minimal failure cases" in readme
    assert "POST /api/documents/missing-doc/credibility" in readme
    assert "Expected: `404 Not Found` with `{\"error\": \"credibility_assessment_not_found\", \"status\": \"missing\"}`" in readme
    assert "GET /api/claims/missing-claim/verification" in readme
    assert "Expected: `404 Not Found` with `{\"error\": \"verification_not_found\", \"status\": \"missing\"}`" in readme
    assert "GET /api/reports/missing-case.json" in readme
    assert "Expected: `404 Not Found` with `{\"error\": \"report_not_found\", \"status\": \"missing\"}`" in readme
    assert "POST /api/reviews` with an incomplete payload" in readme
    assert "Expected: `400 Bad Request` with `status: invalid_request`" in readme
