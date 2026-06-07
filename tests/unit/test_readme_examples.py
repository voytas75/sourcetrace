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
    assert "## Quick start" in readme
    assert "uv sync --dev --extra dev" in readme
    assert "uv run pytest -q" in readme
    assert "### 3. Start a local runtime" in readme
    assert "uv run python -m sourcetrace.web" in readme
    assert "## What SourceTrace can do today" in readme
    assert "serve a local HTML landing page and local API surface" in readme
    assert "manage continuity-pack state with active and latest-previous views" in readme
    assert "## What still needs caution" in readme
    assert "the thin `sourcetrace.web` path is a local stdlib runtime, not a production server stack" in readme
    assert "## Documentation map" in readme
    assert "docs/architecture/architecture-ssot.md" in readme
    assert "docs/plans/execution-blueprint-v0.md" in readme
    assert "Everything else that is not needed for first project understanding belongs in `notes/`" in readme
