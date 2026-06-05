from pathlib import Path


README_PATH = Path(__file__).resolve().parents[2] / "README.md"


def test_readme_documents_local_web_smoke_examples() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "Run locally with uv:" in readme
    assert "uv sync --dev --extra dev" in readme
    assert "uv run pytest -q" in readme
    assert "uv run python -m sourcetrace.web" in readme
    assert "Expected startup: `SourceTrace local server listening on http://127.0.0.1:8000`" in readme
    assert "PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher" in readme
    assert "PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control wait --host 127.0.0.1 --port 8000 --timeout-seconds 15" in readme
    assert "PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control status --mode local-launcher" in readme
    assert "PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control stop --mode local-launcher" in readme
    assert "## Current state" in readme
    assert "Confirmed baseline now:" in readme
    assert "374 passed" in readme
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
    assert "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.credibility_smoke --pretty" in readme
    assert "sourcetrace-credibility-smoke" in readme
    assert "Expected: JSON report confirming `credibility_assessment` exists on both POST and GET" in readme
    assert "post_get_match` is `true`" in readme
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
    assert "Current verified workflow contract: verification payloads now also expose `evidence_sufficiency`, `publication_gate`, and `gate_reason`" in readme
    assert "Current verified workflow contract: report payloads now also expose per-entry `evidence_sufficiency`, `publication_gate`, `gate_reason`, and case-level `publication_summary` including `blocked_claim_count`" in readme
    assert "Current verified UI nuance: `/cases/{case_id}` now also renders `Evidence sufficiency`, `Publication gate`, and `Gate reason` per claim row" in readme
    assert "Expected: `200 OK` with JSON containing `verification.verdict`, `verification.evidence_sufficiency`, `verification.publication_gate`, and `verification.gate_reason`" in readme
    assert "Expected: `200 OK` with canonical report JSON including per-entry publication fields and `publication_summary`" in readme
    assert "Expected: excluded-only report cases now also return `200 OK` with empty `entries` and `publication_summary.blocked_claim_count > 0` instead of `report_not_found`" in readme
    assert "Expected: excluded-only markdown reports also include a `## Publication summary` section with `Blocked claims: 1` when the case was excluded from publication by human review" in readme
    assert "## Publication gate semantics v1" in readme
    assert "- `allowed` — the claim currently has sufficient support for publication in the v1 contract." in readme
    assert "- `review_required` — the claim is not publication-ready and needs analyst review before publication." in readme
    assert "- `blocked` — used when human review explicitly excludes a claim from publication; current runtime surfaces it for `HumanReviewStatus.EXCLUDED`." in readme
    assert "- `gate_reason` is `grounding_insufficient` when the current verdict is `insufficient_evidence`, `conflicting_evidence` when the current verdict is `contradict`, `human_review_excluded` when a reviewed claim is excluded from publication, and otherwise `null` / `none` in current surfaces." in readme
    assert "`POST /api/documents/{document_id}/extract-claims` now also auto-prepares stored inline content when chunks are still missing" in readme
    assert "`POST /api/documents/{document_id}/credibility` now also auto-prepares stored inline content when chunks are still missing" in readme
    assert "SOURCETRACE_CONTINUITY_PACK_ROOT_DIR" in readme
    assert "active continuity pack per case" in readme
    assert "latest_previous" in readme
    assert "GET /api/cases/{case_id}/continuity-pack" in readme
    assert "continuity_pack.decision_support" in readme
    assert "latest_previous` with its own `decision_support" in readme
    assert "same `Decision support` framing used by the dedicated continuity-pack view" in readme
    assert "after clear it still returns `200 OK`" in readme
    assert "continuity_pack_persistence.enabled" in readme
    assert "continuity_pack_persistence" in readme
    assert "requires an already running local server on `127.0.0.1:8000`" in readme
    assert "Current verified diagnostics: `diagnostics` now includes `claim_count`, `chunk_count`, `status`, `summary`, and `next_step`" in readme
    assert "Current verified diagnostics: the response also includes `diagnostics.chunk_count`" in readme
    assert "diagnostics.review_cautions" in readme
    assert "weak_source_posture" in readme
    assert "structured fields (`summary`, `strengths`, `concerns`, `verification_checks`)" in readme
    assert "maps semantic assessment fields" in readme
    assert "hardened toward semantic JSON output" in readme
    assert "stabilisation scenarios in test coverage" in readme
    assert "unattributed notes, anonymous reposts, weak scraped snippets, and anonymous rumor-style blog posts" in readme
    assert "secondary news summaries stay secondary unless they clearly embed the primary material" in readme
    assert "Current verified contrast note continuity: inline note-style contrast inputs no longer fall into `empty`" in readme
    assert "Current verified credibility continuity: dev-seeded inline documents no longer need an explicit `POST /prepare`" in readme
    assert "Current verified credibility nuance: after continuity closure, strong-source `source_reliability` is still metadata-sensitive" in readme
    assert "this was reproduced cross-publisher on Reuters- and BBC-style texts" in readme
    assert "the same excerpt stayed `medium / medium` as a note with missing URL/publication metadata" in readme
    assert "returned to `high / medium` once `source_url` and `published_at` were present" in readme
    assert "weak-source anonymous rumor-style blog rerun reached `low / low`" in readme
    assert "exact claim shape can still vary between the stronger restriction clause and an additional reopening clause" in readme
    assert "## Example: run credibility on your own document payload" in readme
    assert "## Test-use checklist for collecting findings" in readme
    assert "docs/plans/test-use-observation-template.md" in readme
    assert "docs/plans/test-use-observation-example-bbc.md" in readme
    assert "docs/plans/2026-05-23-continuity-pack-usage-note.md" in readme
    assert "continuity-pack operator surfaces are now aligned around a shared `Decision support` model" in readme
    assert "continuity-pack case-page actions and microcopy are normalized" in readme
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
    assert "POST /api/reviews` with an unknown or case-mismatched `claim_id`" in readme
    assert 'Expected: `404 Not Found` with `{"error": "claim_not_found", "status": "missing"}`' in readme
    assert "Expected: `400 Bad Request` with `status: invalid_request`" in readme
