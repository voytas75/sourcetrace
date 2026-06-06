from pathlib import Path


README_PATH = Path(__file__).resolve().parents[2] / "README.md"


def test_readme_documents_local_web_smoke_examples() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "SourceTrace is a local-first system for evidence-centric OSINT work" in readme
    assert "LLM output should remain an assistant layer rather than the source of truth" in readme
    assert "## What this project is" in readme
    assert "a local system for evidence-first OSINT workflows" in readme
    assert "a web/API runtime for case, document, claim, verification, review, and report flows" in readme
    assert "a tool for turning source material into traceable claims and reviewable outputs" in readme
    assert "## Who SourceTrace is for" in readme
    assert "an analyst or operator who wants to work from evidence toward claims and reports" in readme
    assert "## What this project is not" in readme
    assert "not a hosted SaaS service" in readme
    assert "not an autonomous research agent that can replace analyst review" in readme
    assert "## Product stance" in readme
    assert "evidence first, claims second, report last" in readme
    assert "raw evidence and interpretation stay separate" in readme
    assert "source credibility is advisory and separate from claim support" in readme
    assert "## Core workflow" in readme
    assert "create a case for an investigation or topic" in readme
    assert "prepare source text into chunks" in readme
    assert "review results before producing report outputs" in readme
    assert "## Typical use cases" in readme
    assert "investigate a topic as a case and keep source material, chunks, claims, and review state in one local flow" in readme
    assert "## Requirements" in readme
    assert "Python `>=3.13`" in readme
    assert "package manager / workflow: `uv`" in readme
    assert "litellm" in readme
    assert "## Quick start" in readme
    assert "uv sync --dev --extra dev" in readme
    assert "uv run pytest -q" in readme
    assert "uv run python -m sourcetrace.web" in readme
    assert "Expected startup:" in readme
    assert "SourceTrace local server listening on http://127.0.0.1:8000" in readme
    assert "## Runtime modes" in readme
    assert "### A. Thin web mode" in readme
    assert "uv run sourcetrace-web" in readme
    assert "### B. Local launcher mode" in readme
    assert "SOURCETRACE_LLM_API_KEY" in readme
    assert "SOURCETRACE_LLM_BASE_URL" in readme
    assert "SOURCETRACE_LLM_API_VERSION" in readme
    assert "AZURE_OPENAI_API_KEY" in readme
    assert "SOURCETRACE_CONTINUITY_PACK_ROOT_DIR" in readme
    assert "PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher" in readme
    assert "PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control wait --host 127.0.0.1 --port 8000 --timeout-seconds 15" in readme
    assert "PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control status --mode local-launcher" in readme
    assert "PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control stop --mode local-launcher" in readme
    assert "PYTHONPATH=src ./.venv/bin/python -m sourcetrace.local_launcher" in readme
    assert "## What SourceTrace can do today" in readme
    assert "serve a local HTML landing page and local API surface" in readme
    assert "manage continuity-pack state with active and latest-previous views" in readme
    assert "## What you can currently verify locally" in readme
    assert "local API health/readiness/runtime/capabilities routes" in readme
    assert "python -m sourcetrace.smoke_flow" in readme
    assert "python -m sourcetrace.credibility_smoke" in readme
    assert "## Minimal smoke checklist" in readme
    assert "curl http://127.0.0.1:8000/" in readme
    assert "curl http://127.0.0.1:8000/api/health" in readme
    assert "curl http://127.0.0.1:8000/api/ready" in readme
    assert "curl http://127.0.0.1:8000/api/runtime" in readme
    assert "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.smoke_flow --pretty" in readme
    assert "## What still needs caution" in readme
    assert "the thin `sourcetrace.web` path is a local stdlib runtime, not a production server stack" in readme
    assert "## Documentation map" in readme
    assert "docs/architecture/architecture-ssot.md" in readme
    assert "docs/plans/execution-blueprint-v0.md" in readme
    assert "docs/plans/local-launcher-readiness-ssot.md" in readme
    assert "docs/plans/2026-06-05-verification-control-plane-ssot.md" in readme
    assert "docs/plans/2026-05-24-credibility-inline-continuity-ssot.md" in readme
    assert "docs/plans/2026-05-24-credibility-policy-closeout.md" in readme
    assert "docs/plans/2026-05-26-source-trace-research-to-backlog-plan.md" in readme
    assert "Local-only notes, ledgers, and transient research artifacts are intentionally excluded from the remote repo." in readme
