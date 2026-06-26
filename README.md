# SourceTrace

SourceTrace is a local-first, evidence-centric OSINT system.
It helps an analyst move from source material to traceable claims, reviewable findings, and report outputs — with LLMs kept in an assistant role rather than treated as the source of truth.

## What this project is
SourceTrace is:
- an evidence-first OSINT workflow system
- a local web/API runtime for case, document, claim, verification, review, and report flows
- a tool for turning source material into traceable claims and reviewable outputs

## Who SourceTrace is for
SourceTrace is for:
- an analyst or operator who wants to move from evidence toward claims and reports
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
- user-visible outputs should stay inspectable rather than magical

## Core workflow
1. create a case for an investigation or topic
2. prepare source text into chunks
3. extract claims and inspect supporting evidence
4. review results before producing report outputs

## Typical use cases
- investigate a topic as a case and keep source material, chunks, claims, and review state in one local flow
- run a bounded Deep Research job and inspect a persisted result artifact with progress history

## Requirements
- Python `>=3.13`
- package manager / workflow: `uv`
- `litellm`

## Quick start
```bash
uv sync --dev --extra dev
uv run pytest -q
uv run python -m sourcetrace.web
```

Expected startup:
- SourceTrace local server listening on `http://127.0.0.1:8000`

Then open:
- `http://127.0.0.1:8000/`

## Runtime posture
SourceTrace currently has two practical local runtime modes:
- **thin web mode** — lightweight local front door
- **local launcher mode** — richer repo-owned runtime wiring for Deep Research and LLM-backed flows

For detailed runtime commands, environment variables, and operator workflows, see [`README-dev.md`](README-dev.md).

## What SourceTrace can do today
- serve a local HTML landing page and local API surface
- run a bounded Deep Research flow with persisted progress and result artifacts
- expose a local operator console for research at `/research`
- persist compiled research artifacts and artifact lint/health outputs above run results
- keep official/public-law evidence flows traceable across retrieval, packing, and report projection

## What still needs caution
- SourceTrace is still a local-first operator system, not a hosted production service
- broader extraction, normalization, and credibility behavior over real providers remains runtime-dependent and should be re-verified live when quality matters
- Deep Research recovery still behaves more like recovery-as-error than a true resume model
- LLM output remains an assistant layer and should not be treated as the source of truth

## Developer notes
Developer/operator details were moved to:
- [`README-dev.md`](README-dev.md)

That file covers runtime variants, environment variables, command help surfaces, smoke flows, deeper API/operator paths, and development constraints.

## Documentation map
- `docs/architecture-ssot.md`
- `docs/execution-blueprint.md`
- `docs/deep-research-implementation-slice-v1.md`
- `docs/deep-research-status-checkpoint-2026-06-22.md`

For the current Deep Research restart point, prefer `docs/deep-research-status-checkpoint-2026-06-22.md` over older slice-by-slice notes.

Everything else that is not needed for first project understanding belongs in `notes/` as local working material rather than public-facing docs.

Local-only notes, ledgers, and transient research artifacts are intentionally excluded from the remote repo.
