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
    assert "## Current state" in readme
    assert "Confirmed baseline now:" in readme
    assert "workflow envelope" in readme
    assert "ASCII-safe" in readme
    assert "structured credibility output" in readme
    assert "`CI Smoke` workflow" in readme
    assert "## Local smoke flow" in readme
    assert "curl http://127.0.0.1:8000/api/health" in readme
    assert "curl http://127.0.0.1:8000/api/ready" in readme
    assert "curl http://127.0.0.1:8000/api/runtime" in readme
    assert "curl http://127.0.0.1:8000/api/capabilities" in readme
    assert "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.smoke_flow" in readme
    assert "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src sourcetrace-smoke-flow" in readme
    assert "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.smoke_flow --pretty" in readme
    assert "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.smoke_flow --expect-claims-min 2" in readme
    assert "Operational contract: the command exits `0` on pass and `1` on failed expectations" in readme
    assert "failure summary JSON to stderr" in readme
    assert "prepare_chunk_count" in readme
    assert "html_has_snippet" in readme
    assert "html_has_summary" in readme
    assert "Current verified UI nuance: `/cases/{case_id}` now renders a `Document status` table" in readme
    assert "a short `Snippet:` preview sourced from inline text" in readme
    assert "shows summary/strengths/concerns/verification checks" in readme
    assert "Status: Not assessed yet." in readme
    assert "next credibility endpoint" in readme
    assert "returns a real `404` for missing cases instead of rendering `Case None`" in readme
    assert "Current verified continuity: the same route also accepts inline `text` (alias for `content`)" in readme
    assert "Current verified continuity: if the document was created earlier with inline `content` or `text`" in readme
    assert "`POST /api/documents/{document_id}/extract-claims` now also auto-prepares stored inline content when chunks are still missing" in readme
    assert "requires an already running local server on `127.0.0.1:8000`" in readme
    assert "Current verified diagnostics: `diagnostics` now includes `claim_count`, `chunk_count`, `status`, `summary`, and `next_step`" in readme
    assert "Current verified diagnostics: the response also includes `diagnostics.chunk_count`" in readme
    assert "structured fields (`summary`, `strengths`, `concerns`, `verification_checks`)" in readme
    assert "maps semantic assessment fields" in readme
    assert "hardened toward semantic JSON output" in readme
    assert "stabilisation scenarios in test coverage" in readme
    assert "unattributed notes, anonymous reposts, and weak scraped snippets" in readme
    assert "secondary news summaries stay secondary unless they clearly embed the primary material" in readme
    assert "Current verified contrast note continuity: inline note-style contrast inputs no longer fall into `empty`" in readme
    assert "exact claim shape can still vary between the stronger restriction clause and an additional reopening clause" in readme
    assert "## Example: run credibility on your own document payload" in readme
    assert "## Test-use checklist for collecting findings" in readme
    assert "docs/plans/test-use-observation-template.md" in readme
    assert "docs/plans/test-use-observation-example-bbc.md" in readme
    assert "docs/plans/2026-05-23-continuity-pack-usage-note.md" in readme
    assert "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md" in readme
    assert "docs/plans/2026-05-23-source-trace-research-continuity-pack-cerebroscope.md" in readme
    assert "Use a continuity pack selectively" in readme
    assert "## Reusable payload template" in readme
    assert "## systemd --user example" in readme
    assert ".venv/bin/sourcetrace-www-write-user-unit" in readme
    assert "systemctl --user daemon-reload" in readme
    assert "## Minimal failure cases" in readme
    assert "POST /api/documents/missing-doc/credibility" in readme
    assert "GET /api/claims/missing-claim/verification" in readme
    assert "GET /api/reports/missing-case.json" in readme
    assert "Expected: `400 Bad Request` with `status: invalid_request`" in readme
