# SourceTrace

SourceTrace is a local-first system for evidence-centric OSINT work: collecting source material, turning it into traceable claims, reviewing credibility and verification state, and producing report-ready outputs.

It is designed for work where evidence should stay inspectable, claims should stay grounded, and LLM output should remain an assistant layer rather than the source of truth.

## What this project is
- a local system for evidence-first OSINT workflows
- a web/API runtime for case, document, claim, verification, review, and report flows
- a tool for turning source material into traceable claims and reviewable outputs
- a bounded product surface where LLM helps with extraction, normalization, and drafting, but does not replace evidence or analyst review

## Who SourceTrace is for
- an analyst or operator who wants to work from evidence toward claims and reports
- a technical reviewer who wants to inspect system boundaries, runtime shape, and verification surfaces
- a collaborator who needs a truthful local bootstrap and a clear product boundary

## What this project is not
- not a finished public product
- not a hosted SaaS service
- not an autonomous research agent that can replace analyst review
- not a broad crawler or production ingestion platform
- not a guarantee that every documented runtime path is production-ready

## Product stance
SourceTrace is built around a simple rule: evidence first, claims second, report last.

Current durable boundaries:
- raw evidence and interpretation stay separate
- claims should remain traceable to source text / chunks
- human review remains part of the workflow
- source credibility is advisory and separate from claim support
- the local web runtime is a developer/operator surface, not a production deployment shape

## Core workflow
- create a case for an investigation or topic
- attach one or more documents / source artifacts
- prepare source text into chunks
- extract candidate claims
- assess credibility and verification state
- review results before producing report outputs

## Typical use cases
- investigate a topic as a case and keep source material, chunks, claims, and review state in one local flow
- compare extracted claims with evidence before turning them into analyst-facing conclusions
- test a bounded verification/report workflow locally before deciding what should become a stronger product surface

## Requirements
Confirmed from `pyproject.toml`:
- Python `>=3.13`
- package manager / workflow: `uv`
- optional dev extra includes at least:
  - `pytest`
  - `litellm`

## Quick start
### 1. Install dependencies
```bash
uv sync --dev --extra dev
```

### 2. Run tests
```bash
uv run pytest -q
```

### 3. Start a local runtime
For a thin local web runtime:
```bash
uv run python -m sourcetrace.web
```

For the repo-owned local launcher with LLM wiring:
```bash
uv run sourcetrace-local
```

Expected startup:
```text
SourceTrace local server listening on http://127.0.0.1:8000
```

Then open:
- `http://127.0.0.1:8000/`

## Runtime modes
SourceTrace currently has two practical local run modes.

### A. Thin web mode
Use this when you want the lightweight local front door without repo-owned LLM runtime wiring.

```bash
uv run python -m sourcetrace.web
```

Equivalent console script declared in `pyproject.toml`:
```bash
uv run sourcetrace-web
```

### B. Local launcher mode
Use this when you want the repo-owned runtime config plus LLM-backed credibility wiring.

Required environment variables for this mode:
- `SOURCETRACE_LLM_API_KEY`
- `SOURCETRACE_LLM_BASE_URL`
- `SOURCETRACE_LLM_API_VERSION`

The launcher also mirrors legacy Azure variables when the SourceTrace names are missing:
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_BASE_URL`
- `AZURE_OPENAI_API_VERSION`

Optional continuity-pack persistence:
- `SOURCETRACE_CONTINUITY_PACK_ROOT_DIR`

Installed console scripts declared in `pyproject.toml`:
```bash
uv run sourcetrace-local
uv run sourcetrace-www-start --mode local-launcher
uv run sourcetrace-www-wait --host 127.0.0.1 --port 8000 --timeout-seconds 15
uv run sourcetrace-www-status --mode local-launcher
uv run sourcetrace-www-stop --mode local-launcher
```

Module-entrypoint equivalents:
```bash
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control wait --host 127.0.0.1 --port 8000 --timeout-seconds 15
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control status --mode local-launcher
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control stop --mode local-launcher
```

Direct fallback launcher:
```bash
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.local_launcher
```

## What SourceTrace can do today
- serve a local HTML landing page and local API surface
- create cases and attach documents
- prepare chunks from source text
- run claim extraction
- run credibility assessment
- expose verification and reporting surfaces
- manage continuity-pack state with active and latest-previous views
- run reusable smoke flows for local verification

## What you can currently verify locally
Confirmed in code and existing docs/tests:
- local HTML landing page on `/`
- local API health/readiness/runtime/capabilities routes
- case creation and document attachment flows
- prepare / extract-claims / credibility paths
- verification and report surfaces
- continuity-pack read model with `active` and `latest_previous`
- smoke helpers:
  - `python -m sourcetrace.smoke_flow`
  - `python -m sourcetrace.credibility_smoke`

## Minimal smoke checklist
1. Start one of the local runtimes.
2. Open the landing page:
```bash
curl http://127.0.0.1:8000/
```
3. Check health:
```bash
curl http://127.0.0.1:8000/api/health
```
4. If you started local-launcher mode, also check readiness/runtime:
```bash
curl http://127.0.0.1:8000/api/ready
curl http://127.0.0.1:8000/api/runtime
```
5. Run the reusable smoke command against an already running server:
```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.smoke_flow --pretty
```

## What still needs caution
- this repo is being prepared for private GitHub publication; it is still developer/operator-facing rather than public-polished
- `.env` is not loaded by the repo itself; required secrets come from process environment
- the thin `sourcetrace.web` path is a local stdlib runtime, not a production server stack
- broader extraction/normalization/credibility behavior over real providers should be treated as local-runtime dependent unless re-verified live
- some docs under `docs/plans/` are stable anchors, but process-shaped notes stay local-only by design

## Documentation map
Start with these tracked docs:
- `docs/architecture/architecture-ssot.md` — product and architecture baseline
- `docs/plans/execution-blueprint-v0.md` — implementation blueprint and module map
- `docs/plans/local-launcher-readiness-ssot.md` — verified local launcher/runtime boundary
- `docs/plans/2026-06-05-verification-control-plane-ssot.md` — current verification-first execution SSOT
- `docs/plans/2026-05-24-credibility-inline-continuity-ssot.md` — continuity-pack and credibility inline decisions
- `docs/plans/2026-05-24-credibility-policy-closeout.md` — current credibility policy closeout
- `docs/plans/2026-05-26-source-trace-research-to-backlog-plan.md` — staged research-to-backlog bridge

Local-only notes, ledgers, and transient research artifacts are intentionally excluded from the remote repo.
