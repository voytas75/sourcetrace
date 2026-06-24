# Deep Research branch proposal implementation slice brief v1

Status: planned / implementing
Date: 2026-06-24
Scope: bounded Slice 4 implementation for SourceTrace Deep Research

## Goal
Add a minimal `ResearchBranchProposalSet` artifact that proposes 0-3 bounded analytical branches for eligible queries, persist it on result artifacts, and expose it in result/debug payloads.

## Why this slice now
SourceTrace now has explicit upstream artifacts:
- `ProblemAnalysis`
- `ResearchExecutionPlan`
- `ResearchEvidencePack`

The next correct step is **not** branch execution.
It is first to formalize branch *proposal* as an inspectable planning artifact.

## Non-goals
- no recursive branching
- no multi-branch execution engine
- no branch evaluator yet
- no reflection yet
- no UI redesign beyond payload exposure

## Proposed artifact contract
```json
{
  "proposal_version": "branch_proposal_v1",
  "eligible": true,
  "reason": "broad_concept_query",
  "branches": [
    {
      "branch_id": "branch-1",
      "label": "system_shape",
      "objective": "Describe the current system shape and boundaries"
    }
  ]
}
```

## Eligibility rules
Eligible only when:
- `problem_analysis.query_class == broad_concept`, or
- `problem_analysis.complexity == high`

Additional constraints:
- max 3 branches
- if not eligible, store empty branch set with explicit reason
- deterministic labels/objectives only
- no recursive proposal generation\n
## Persistence target
- `ResearchResultArtifact`

## API surfaces
Expose `branch_proposals` in:
- `GET /api/research/result/{job_id}`
- debug JSON surfaces through serializer inclusion

## Implementation plan
1. Add branch proposal contracts in the domain.
2. Derive branch proposals from `problem_analysis` + `execution_plan`.
3. Persist proposal set on completed result artifacts.
4. Expose serializer payload.
5. Add focused tests.

## Definition of done
- completed eligible results expose `branch_proposals`
- non-eligible results expose explicit `eligible: false`
- branch count is bounded to 3
- focused tests pass

## Risks
### Risk: overbuilding into branch execution
Mitigation: this slice stops at proposal artifact only.

### Risk: decorative artifact with no future path
Mitigation: derive proposals from existing upstream artifacts so Slice 5 can evaluate them later.

### Risk: noisy proposals for routine queries
Mitigation: strict eligibility gate by query class / complexity.

## Rollback
Revert:
- branch proposal domain contracts
- result artifact field
- serializer wiring
- focused tests for this slice
