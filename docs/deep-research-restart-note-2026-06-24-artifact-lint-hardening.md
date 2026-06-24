# Deep Research restart note — 2026-06-24 — Artifact Lint Hardening

## Where we are
- Slice 1 `ProblemAnalysis` shipped.
- Slice 2 `Planner v2` shipped.
- Slice 3 `EvidencePack` shipped.
- Slice 4 `BranchProposalSet` shipped.
- Slice 5 `BranchEvaluation` shipped.
- Slice 6 `Reflection` shipped.
- Slice 7 `CompiledArtifact` hardening shipped.
- Active slice: artifact lint hardening.

## Current goal
Make compiled artifact lint aware of the new snapshot chain and follow-up gaps.

## Planned changes
- extend lint checks for snapshot-chain gaps
- extend lint checks for reflection follow-up mismatches
- keep same lint output contract
- add focused tests

## First files to inspect/resume
- `src/sourcetrace/application/research_runtime.py`
- `tests/unit/application/test_application_research.py`
- `docs/deep-research-artifact-lint-hardening-implementation-slice-brief-v1.md`

## Guardrails
- no new workflow engine
- no auto-repair
- deterministic only
- keep output contract unchanged

## Success condition
- lint flags snapshot gaps and reflection-follow-up mismatches
- focused tests pass
