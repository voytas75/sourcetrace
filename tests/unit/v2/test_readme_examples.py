from pathlib import Path


README_PATH = Path(__file__).resolve().parents[3] / "README.md"


def test_readme_documents_v2_local_runtime_examples() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "SourceTrace is a local-first system for evidence-centric OSINT work." in readme
    assert "LLM output should remain an assistant layer rather than the source of truth." in readme
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
    assert "## Quick start" in readme
    assert "uv sync --dev --extra dev" in readme
    assert "uv run pytest -q" in readme
    assert "uv run sourcetrace-www-start" in readme
    assert "uv run sourcetrace-www-wait --host 127.0.0.1 --port 8000 --timeout-seconds 15" in readme
    assert "SourceTrace v2 local server listening on `http://127.0.0.1:8000`" in readme
    assert "## What SourceTrace can do today" in readme
    assert "serve a local HTML landing page and local API surface" in readme
    assert "run a bounded Deep Research flow with persisted progress and result artifacts" in readme
    assert "## What still needs caution" in readme
    assert "SourceTrace is still a local-first operator system, not a hosted production service" in readme
    assert "## Documentation map" in readme
    assert "docs/sourcetrace-v2-restart-checkpoint-2026-07-19.md" in readme
    assert "docs/architecture-ssot.md" in readme
    assert "docs/execution-blueprint.md" in readme
    assert "Everything else that is not needed for first project understanding belongs in `notes/`" in readme
