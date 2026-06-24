# Deep Research branch evaluator implementation slice brief v1

Status: planned / implementing
Date: 2026-06-24
Scope: bounded Slice 5 implementation for SourceTrace Deep Research

## Goal
Add a minimal `ResearchBranchEvaluation` artifact that scores proposed branches in a deterministic, bounded way and exposes selection guidance without introducing multi-branch execution.

## Why this slice now
SourceTrace already has:
- `ProblemAnalysis`
- `ResearchExecutionPlan`
- `ResearchEvidencePack`
- `ResearchBranchProposalSet`

The next correct bounded move is to evaluate branch proposals, not to execute them.

## Non-goals
- no branch execution engine
- no recursive loop
- no reflection yet
- no critic yet

## Proposed artifact contract
```json
{
  "evaluation_version": "branch_evaluator_v1",
  "selected_branch_ids": ["branch-1"],
  "scores": [
    {
      "branch_id": "branch-1",
      "coverage_score": 0.9,
      "evidence_fit_score": 0.8,
      "priority_score": 0.85,
      "combined_score": 0.85
    }
  ]
}
```

## Bounded evaluation rules
- deterministic only
- score from existing artifacts only:
  - `problem_analysis`
  - `execution_plan`
  - `evidence_pack`
  - `branch_proposals`
- no model call required
- select top 1-2 branches max

## Persistence target
- `ResearchResultArtifact`

## API surfaces
Expose `branch_evaluation` in:
- `GET /api/research/result/{job_id}`
- debug JSON surfaces through serializer inclusion

## Implementation plan
1. Add branch evaluation contracts in the domain.
2. Derive deterministic scores from existing artifacts.
3. Persist evaluation on completed result artifacts.
4. Expose serializer payload.
5. Add focused tests.

## Definition of done
- completed results expose `branch_evaluation`
- non-eligible branch sets produce empty selection cleanly
- selected branches are bounded to max 2
- focused tests pass

## Risks
### Risk: pretending this is real branch reasoning
Mitigation: keep the scoring explicitly heuristic and deterministic.

### Risk: overfitting labels
Mitigation: use only a few bounded label-aware heuristics.

### Risk: pressure toward branch execution
Mitigation: stop at evaluation artifact only.

## Rollback
Revert:
- branch evaluation contracts
- result artifact field
- serializer wiring
- focused tests for this slice
