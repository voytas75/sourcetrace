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
- a technical reviewer who wants to inspect system boundaries and verification surfaces
- a collaborator who needs a truthful local bootstrap and a clear product boundary

## What this project is not
- not a hosted SaaS service
- not an autonomous research agent that can replace analyst review
- not a broad crawler or production ingestion platform

## Product stance
SourceTrace is built around a simple rule: evidence first, claims second, report last.

Current durable boundaries:
- raw evidence and interpretation stay separate
- claims should remain traceable to source text / chunks
- human review remains part of the workflow
- source credibility is advisory and separate from claim support

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
```bash
uv run python -m sourcetrace.web
```

Then open:
- `http://127.0.0.1:8000/`

## What SourceTrace can do today
- serve a local HTML landing page and local API surface
- create cases and attach documents
- prepare chunks from source text
- run claim extraction
- run credibility assessment
- expose verification and reporting surfaces
- manage continuity-pack state with active and latest-previous views
- run reusable smoke flows for local verification

## What still needs caution
- `.env` is not loaded by the repo itself; required secrets come from process environment
- the thin `sourcetrace.web` path is a local stdlib runtime, not a production server stack
- broader extraction/normalization/credibility behavior over real providers should be treated as local-runtime dependent unless re-verified live

## Developer notes
Developer/operator details were moved to:
- [`README-dev.md`](README-dev.md)

That file covers local runtime variants, environment variables, deeper command references, smoke flows, and development constraints.

## Documentation map
- [`docs/architecture-ssot.md`](docs/architecture-ssot.md) — product and architecture baseline
- [`docs/execution-blueprint.md`](docs/execution-blueprint.md) — implementation overview and module map

Everything else that is not needed for first project understanding belongs in `notes/` as local working material rather than public-facing docs.
