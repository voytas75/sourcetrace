# Deep Research restart note — 2026-06-24 — Branch Evaluator

## Where we are
- Slice 1 `ProblemAnalysis` shipped.
- Slice 2 `Planner v2` shipped.
- Slice 3 `EvidencePack` shipped.
- Slice 4 `BranchProposalSet` shipped.
- Active slice: branch evaluator artifact.

## Current goal
Add a bounded branch evaluation artifact to result payloads using only existing runtime artifacts.

## Planned changes
- add branch evaluation contracts
- derive deterministic scores from proposal/evidence/plan context
- persist on `ResearchResultArtifact`
- expose in result/debug payloads
- add focused tests

## First files to inspect/resume
- `src/sourcetrace/domain/research.py`
- `src/sourcetrace/application/research_runtime.py`
- `src/sourcetrace/web/api.py`
- `tests/unit/application/test_application_research.py`
- `tests/unit/web/test_research_api.py`
- `docs/deep-research-branch-evaluator-implementation-slice-brief-v1.md`

## Guardrails
- evaluator artifact only
- no branch execution
- no recursion
- max selected branches: 2

## Success condition
- result payload exposes `branch_evaluation`
- eligible branch sets yield bounded scores + selected ids
- non-eligible cases stay empty and clean
- focused tests pass
