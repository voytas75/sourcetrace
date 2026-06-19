# SourceTrace

SourceTrace is a local-first system for evidence-centric OSINT work.
LLM output should remain an assistant layer rather than the source of truth.

## What this project is
SourceTrace is:
- a local system for evidence-first OSINT workflows
- a web/API runtime for case, document, claim, verification, review, and report flows
- a tool for turning source material into traceable claims and reviewable outputs

## Who SourceTrace is for
SourceTrace is for:
- an analyst or operator who wants to work from evidence toward claims and reports
- a technical reviewer who wants to inspect system boundaries and verification surfaces
- a collaborator who needs a truthful local bootstrap and a clear product boundary

## What this project is not
- not a hosted SaaS service
- not an autonomous research agent that can replace analyst review
- not a broad crawler or production ingestion platform

## Product stance
- evidence first, claims second, report last
- raw evidence and interpretation stay separate
- source credibility is advisory and separate from claim support

## Core workflow
1. create a case for an investigation or topic
2. prepare source text into chunks
3. extract claims and inspect supporting evidence
4. review results before producing report outputs

## Typical use cases
- investigate a topic as a case and keep source material, chunks, claims, and review state in one local flow

## Requirements
- Python `>=3.13`
- package manager / workflow: `uv`
- litellm

## Quick start
```bash
uv sync --dev --extra dev
uv run pytest -q
```

### 3. Start a local runtime
```bash
uv run python -m sourcetrace.web
```

Expected startup:
- SourceTrace local server listening on http://127.0.0.1:8000

Then open:
- `http://127.0.0.1:8000/`

## Runtime modes
### A. Thin web mode
```bash
uv run sourcetrace-web
```

### B. Local launcher mode
Environment variables:
- `SOURCETRACE_LLM_API_KEY`
- `SOURCETRACE_LLM_BASE_URL`
- `SOURCETRACE_LLM_API_VERSION`
- `AZURE_OPENAI_API_KEY`
- `SOURCETRACE_CONTINUITY_PACK_ROOT_DIR`

```bash
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control wait --host 127.0.0.1 --port 8000 --timeout-seconds 15
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control status --mode local-launcher
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control stop --mode local-launcher
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.local_launcher
```

## What SourceTrace can do today
- serve a local HTML landing page and local API surface
- manage continuity-pack state with active and latest-previous views
- run a bounded Deep Research flow with persisted progress and result artifacts

## What you can currently verify locally
- local API health/readiness/runtime/capabilities routes
- `python -m sourcetrace.smoke_flow`
- `python -m sourcetrace.credibility_smoke`

## Minimal smoke checklist
```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/ready
curl http://127.0.0.1:8000/api/runtime
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.smoke_flow --pretty
```

## What still needs caution
- `.env` is not loaded by the repo itself; required secrets come from process environment
- the thin `sourcetrace.web` path is a local stdlib runtime, not a production server stack
- broader extraction/normalization/credibility behavior over real providers should be treated as local-runtime dependent unless re-verified live

## Developer notes
Developer/operator details were moved to:
- [`README-dev.md`](README-dev.md)

That file covers local runtime variants, environment variables, deeper command references, smoke flows, and development constraints.

## Documentation map
- `docs/architecture-ssot.md`
- `docs/architecture/architecture-ssot.md`
- `docs/execution-blueprint.md`
- `docs/plans/execution-blueprint-v0.md`
- `docs/plans/local-launcher-readiness-ssot.md`
- `docs/plans/2026-06-05-verification-control-plane-ssot.md`
- `docs/plans/2026-05-24-credibility-inline-continuity-ssot.md`
- `docs/plans/2026-05-24-credibility-policy-closeout.md`
- `docs/plans/2026-05-26-source-trace-research-to-backlog-plan.md`
- `docs/deep-research-implementation-slice-v1.md`

Everything else that is not needed for first project understanding belongs in `notes/` as local working material rather than public-facing docs.

Local-only notes, ledgers, and transient research artifacts are intentionally excluded from the remote repo.
