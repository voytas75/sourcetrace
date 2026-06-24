# Deep Research restart note — 2026-06-24 — Compiled Artifact Hardening

## Where we are
- Slice 1 `ProblemAnalysis` shipped.
- Slice 2 `Planner v2` shipped.
- Slice 3 `EvidencePack` shipped.
- Slice 4 `BranchProposalSet` shipped.
- Slice 5 `BranchEvaluation` shipped.
- Slice 6 `Reflection` shipped.
- Active slice: compiled artifact hardening.

## Current goal
Enrich existing compiled artifacts with selected snapshots from the artifact chain.

## Planned changes
- extend compiled artifact contract with compact snapshots
- populate snapshots in compile path
- expose snapshots in compiled payloads
- add focused tests

## First files to inspect/resume
- `src/sourcetrace/domain/research.py`
- `src/sourcetrace/application/research_runtime.py`
- `src/sourcetrace/web/api.py`
- `tests/unit/domain/test_research.py`
- `tests/unit/application/test_application_research.py`
- `tests/unit/web/test_research_api.py`
- `docs/deep-research-compiled-artifact-hardening-implementation-slice-brief-v1.md`

## Guardrails
- enrich existing compiled artifact only
- no lint expansion yet
- no new persistence path
- keep snapshots compact

## Success condition
- compiled artifacts expose compact snapshots from artifact chain
- focused tests pass
