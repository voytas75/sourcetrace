# Deep Research reflection v1 implementation slice brief v1

Status: planned / implementing
Date: 2026-06-24
Scope: bounded Slice 6 implementation for SourceTrace Deep Research

## Goal
Add a minimal `ResearchReflection` artifact that performs a deterministic post-result self-check and emits at most one follow-up recommendation without triggering any retry loop.

## Why this slice now
SourceTrace already has explicit upstream artifacts for:
- problem framing
- execution planning
- evidence packing
- branch proposal
- branch evaluation

The next correct bounded step is a reflection artifact that checks whether the result likely covered the intended goal and where evidence remains thin.

## Non-goals
- no retry loop
- no recursive reflection
- no new model call
- no critic yet

## Proposed artifact contract
```json
{
  "reflection_version": "reflection_v1",
  "goal_coverage": "full|partial|weak",
  "missing_topics": ["string"],
  "weak_evidence_areas": ["string"],
  "should_follow_up": true,
  "recommended_follow_up": "string|null"
}
```

## Bounded rules
- deterministic only
- use existing artifacts only:
  - `problem_analysis`
  - `execution_plan`
  - `evidence_pack`
  - `branch_evaluation`
  - `evaluation`
- emit at most one recommended follow-up
- do not trigger retry automatically in this slice

## Persistence target
- `ResearchResultArtifact`

## API surfaces
Expose `reflection` in:
- `GET /api/research/result/{job_id}`
- debug JSON surfaces through serializer inclusion

## Implementation plan
1. Add reflection contracts in the domain.
2. Derive deterministic reflection from existing artifacts.
3. Persist on completed result artifacts.
4. Expose serializer payload.
5. Add focused tests.

## Definition of done
- completed results expose `reflection`
- reflection remains bounded and deterministic
- at most one follow-up recommendation is emitted
- focused tests pass

## Risks
### Risk: pseudo-reasoning theater
Mitigation: keep the artifact simple and explicit about being heuristic.

### Risk: pressure toward self-loop retries
Mitigation: no retry trigger in this slice, recommendation only.

### Risk: duplicating evaluator semantics
Mitigation: reflection answers goal-coverage and follow-up questions, not source-quality judgment.

## Rollback
Revert:
- reflection contracts
- result artifact field
- serializer wiring
- focused tests for this slice
