from pathlib import Path


README_PATH = Path(__file__).resolve().parents[2] / "README.md"


def test_readme_documents_local_web_smoke_examples() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "Run locally with uv:" in readme
    assert "uv sync --dev --extra dev" in readme
    assert "uv run pytest -q" in readme
    assert "uv run python -m sourcetrace.web" in readme
    assert "Expected startup: `SourceTrace local server listening on http://127.0.0.1:8000`" in readme
    assert "Use `Ctrl+C` to stop the server cleanly." in readme
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
    assert "The current `llm_draft_v1` output should be treated as an advisory draft" in readme
    assert "It currently relies mostly on document metadata, source identity, and topic context" in readme
    assert "not yet on full article-text analysis or claim-by-claim verification" in readme
    assert "## Example: run credibility on your own document payload" in readme
    assert 'document_id": "doc-custom-1"' in readme
    assert 'source_url": "https://example.test/your-article"' in readme
    assert 'title": "Your article title"' in readme
    assert ".venv/bin/sourcetrace-www-start" in readme
    assert ".venv/bin/sourcetrace-www-wait" in readme
    assert ".venv/bin/sourcetrace-www-status" in readme
    assert ".venv/bin/sourcetrace-www-stop" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/dev/documents" in readme
    assert 'curl -X POST http://127.0.0.1:8000/api/documents/doc-custom-1/credibility' in readme
    assert "Expected: `201 Created` with JSON echoing `document.document_id`" in readme
    assert "Expected: `200 OK` with JSON containing `credibility_assessment.notes` and `method`" in readme
    assert "## Reusable payload template" in readme
    assert "## systemd --user example" in readme
    assert ".venv/bin/sourcetrace-www-write-user-unit" in readme
    assert "systemctl --user daemon-reload" in readme
    assert '"document_id": "{{document_id}}"' in readme
    assert '"source_url": "{{source_url}}"' in readme
    assert '"publisher": "{{publisher}}"' in readme
    assert '"title": "{{title}}"' in readme
    assert '"language": "{{language}}"' in readme
    assert "## Minimal failure cases" in readme
    assert "POST /api/documents/missing-doc/credibility" in readme
    assert "Expected: `404 Not Found` with `{\"error\": \"credibility_assessment_not_found\", \"status\": \"missing\"}`" in readme
    assert "GET /api/claims/missing-claim/verification" in readme
    assert "Expected: `404 Not Found` with `{\"error\": \"verification_not_found\", \"status\": \"missing\"}`" in readme
    assert "GET /api/reports/missing-case.json" in readme
    assert "Expected: `404 Not Found` with `{\"error\": \"report_not_found\", \"status\": \"missing\"}`" in readme
    assert "POST /api/reviews` with an incomplete payload" in readme
    assert "Expected: `400 Bad Request` with `status: invalid_request`" in readme
