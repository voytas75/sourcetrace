# Deep Research restart note — 2026-06-24 — Evidence Packing

## Where we are
- Slice 1 (`ProblemAnalysis`) shipped and validated.
- Slice 2 (`Planner v2`) shipped and validated.
- Active slice: `Evidence Packing hardening`.

## Current goal
Make evidence grouping durable and inspectable by adding a minimal `ResearchEvidencePack` artifact to result artifacts and result payloads.

## Planned changes
- add evidence-pack contract in domain
- persist `evidence_pack` on `ResearchResultArtifact`
- wire runtime packing output into persisted result
- expose in result/debug payloads
- add focused tests

## First files to inspect/resume
- `src/sourcetrace/domain/research.py`
- `src/sourcetrace/application/research_runtime.py`
- `src/sourcetrace/web/api.py`
- `tests/unit/application/test_application_research.py`
- `tests/unit/web/test_research_api.py`
- `docs/deep-research-evidence-packing-implementation-slice-brief-v1.md`

## Guardrails
- keep bounded
- no branching yet
- no reflection yet
- no planner rewrite in this slice

## Success condition
- result payload exposes `evidence_pack`
- persisted result contains grouped evidence used by runtime
- focused tests pass
