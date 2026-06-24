# Deep Research restart note — 2026-06-24 — Branch Proposal

## Where we are
- Slice 1 `ProblemAnalysis` shipped.
- Slice 2 `Planner v2` shipped.
- Slice 3 `EvidencePack` shipped.
- Active slice: bounded branch proposal artifact.

## Current goal
Add a minimal branch proposal artifact to result payloads for eligible queries only.

## Planned changes
- add branch proposal domain contracts
- derive proposals from `problem_analysis` + `execution_plan`
- persist on `ResearchResultArtifact`
- expose in result/debug payloads
- add focused tests

## First files to inspect/resume
- `src/sourcetrace/domain/research.py`
- `src/sourcetrace/application/research_runtime.py`
- `src/sourcetrace/web/api.py`
- `tests/unit/application/test_application_research.py`
- `tests/unit/web/test_research_api.py`
- `docs/deep-research-branch-proposal-implementation-slice-brief-v1.md`

## Guardrails
- proposal artifact only
- no branch execution
- no recursion
- max 3 branches
- eligible queries only

## Success condition
- result payload exposes `branch_proposals`
- broad/high-complexity queries get 1-3 proposals
- routine procedural queries get explicit `eligible: false`
- focused tests pass
