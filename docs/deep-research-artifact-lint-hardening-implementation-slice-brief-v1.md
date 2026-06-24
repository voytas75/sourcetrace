# Deep Research artifact lint hardening implementation slice brief v1

Status: planned / implementing
Date: 2026-06-24
Scope: bounded Slice 8 implementation for SourceTrace Deep Research

## Goal
Harden the existing compiled artifact lint by making it aware of the new compact snapshot chain on `CompiledResearchArtifact`, while keeping the lint deterministic and bounded.

## Why this slice now
Compiled artifacts now preserve selected snapshots from the runtime artifact chain:
- `problem_analysis_snapshot`
- `execution_plan_snapshot`
- `reflection_snapshot`
- `evaluation_snapshot`

That makes it finally worth extending lint beyond the original thin result shape.

## Non-goals
- no new lint workflow engine
- no background repair loop
- no artifact auto-rewrite
- no new persistence subsystem

## Planned hardening
Extend lint checks for:
- missing `execution_plan_snapshot`
- missing `reflection_snapshot`
- reflection-follow-up without matching `next_checks`
- shallow execution plan snapshot
- high-risk reflection/evaluation mismatch when coverage is weak but repair guidance is absent

## Bounded rules
- deterministic only
- use compiled artifact content only
- output stays inside existing lint contract:
  - risk flags
  - missing sections
  - recommended repairs
  - recommended next action

## Implementation plan
1. Extend `_lint_compiled_research_artifact()` with snapshot-aware checks.
2. Keep existing lint output contract unchanged.
3. Add focused tests for the new checks.

## Definition of done
- lint reacts to missing snapshot chain elements
- lint reacts to reflection follow-up gaps
- focused tests pass

## Risks
### Risk: lint becomes noisy
Mitigation: add only a few high-signal checks tied to new snapshots.

### Risk: duplicate evaluator/reflection semantics
Mitigation: lint operates on artifact health, not live run reasoning.

### Risk: over-expanding repair logic
Mitigation: keep existing output surface; no new workflow actions.

## Rollback
Revert:
- lint heuristic additions
- focused tests for this slice
