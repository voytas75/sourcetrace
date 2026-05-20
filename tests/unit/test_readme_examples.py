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
    assert "curl http://127.0.0.1:8000/api/health" in readme
    assert "curl http://127.0.0.1:8000/api/ready" in readme
    assert "curl http://127.0.0.1:8000/api/runtime" in readme
    assert "curl http://127.0.0.1:8000/api/capabilities" in readme
    assert "Expected: `200 OK` with JSON containing `status: ready` and `checks`" in readme
    assert "Expected: `200 OK` with JSON containing `runtime.entrypoint`" in readme
    assert "Expected: `200 OK` with JSON listing `routes.product`, `routes.dev`, and runtime capability flags" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/cases" in readme
    assert "Expected: `201 Created` with JSON containing `case.case_id`" in readme
    assert "common top-level workflow envelope" in readme
    assert "`status`, `summary`, `next_step`, `resource`, and `resource_id`" in readme
    assert "compatibility aliases at top level (`case_id`, `document_id`)" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/cases/case-1/documents" in readme
    assert "Expected: `201 Created` with JSON containing `document.document_id`" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/documents/doc-1/prepare" in readme
    assert "Expected: `200 OK` with JSON containing `chunks`" in readme
    assert "Current verified diagnostics: the response also includes `diagnostics.chunk_count`" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/documents/doc-1/extract-claims" in readme
    assert '"extraction_method":"llm_v1"' in readme
    assert "Expected: `200 OK` with JSON containing `claims` and `diagnostics`" in readme
    assert "Current verified diagnostics: `diagnostics` now includes `claim_count`, `chunk_count`, `status`, `summary`, and `next_step`" in readme
    assert "Current verified guardrail: if claim normalization returns a conversational/helpdesk-style rewrite" in readme
    assert "Sourcetrace keeps the original extracted claim text" in readme
    assert "resists basic cross-language drift for Polish source text" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/verify" in readme
    assert '"chunk_id": "doc-1:chunk-1"' in readme
    assert "curl http://127.0.0.1:8000/api/cases" in readme
    assert "curl http://127.0.0.1:8000/api/cases/case-1" in readme
    assert "curl http://127.0.0.1:8000/api/cases/case-1/documents" in readme
    assert "curl http://127.0.0.1:8000/api/documents/doc-1" in readme
    assert "curl http://127.0.0.1:8000/api/documents/doc-1/chunks" in readme
    assert "curl http://127.0.0.1:8000/api/cases/case-1/claims" in readme
    assert "curl http://127.0.0.1:8000/api/claims/claim-1" in readme
    assert "Expected: `200 OK` with JSON containing `verification.verdict`" in readme
    assert "curl http://127.0.0.1:8000/api/claims/claim-1/evidence" in readme
    assert "curl http://127.0.0.1:8000/cases/case-1" in readme
    assert "Expected: each returns `200 OK` after the relevant upstream step is completed" in readme
    assert "Current verified UI nuance: `/cases/{case_id}` now renders a `Document status` table" in readme
    assert "returns a real `404` for missing cases instead of rendering `Case None`" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/reviews" in readme
    assert "Expected: `200 OK` with JSON containing the persisted review payload" in readme
    assert "curl http://127.0.0.1:8000/api/claims/claim-1/review" in readme
    assert "Expected: `200 OK` with JSON containing the persisted review artifact" in readme
    assert "curl http://127.0.0.1:8000/api/claims/claim-1/verification" in readme
    assert "curl http://127.0.0.1:8000/api/reports/case-1" in readme
    assert "Expected: `200 OK` with canonical report JSON" in readme
    assert "curl http://127.0.0.1:8000/api/reports/case-1.md" in readme
    assert "Expected: `200 OK` with `Content-Type: text/markdown; charset=utf-8`" in readme
    assert "curl -X POST http://127.0.0.1:8000/api/documents/doc-1/credibility" in readme
    assert "Expected: `200 OK` with JSON containing `credibility_assessment.notes`" in readme
    assert "structured fields (`summary`, `strengths`, `concerns`, `verification_checks`)" in readme
    assert "curl http://127.0.0.1:8000/api/documents/doc-1/credibility" in readme
    assert "Expected: `200 OK` with the latest persisted `credibility_assessment`" in readme
    assert "The current `llm_draft_v1` output should be treated as an advisory draft" in readme
    assert "It currently relies mostly on document metadata, source identity, and topic context" in readme
    assert "not yet on full article-text analysis or claim-by-claim verification" in readme
    assert "## Example: run credibility on your own document payload" in readme
    assert "## Test-use checklist for collecting findings" in readme
    assert "whether extraction returned concise claim-like sentences or assistant-style prose" in readme
    assert "docs/plans/test-use-observation-template.md" in readme
    assert "docs/plans/test-use-observation-example-bbc.md" in readme
    assert "Current known limitation from live smoke: some long assistant-style rewrites can still slip through normalization fallback on real articles" in readme
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
    assert "Expected: `404 Not Found` with `{\"error\": \"document_not_found\", \"status\": \"missing\"}`" in readme
    assert "GET /api/claims/missing-claim/verification" in readme
    assert "Expected: `404 Not Found` with `{\"error\": \"verification_not_found\", \"status\": \"missing\"}`" in readme
    assert "GET /api/reports/missing-case.json" in readme
    assert "Expected: `404 Not Found` with `{\"error\": \"report_not_found\", \"status\": \"missing\"}`" in readme
    assert "POST /api/reviews` with an incomplete payload" in readme
    assert "Expected: `400 Bad Request` with `status: invalid_request`" in readme
