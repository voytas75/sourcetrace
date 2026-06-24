# Deep Research Planner v2 implementation slice brief v1

Status: planned / implementing
Date: 2026-06-24
Scope: bounded Slice 2 implementation for SourceTrace Deep Research

## Goal
Add a minimal formal `ResearchExecutionPlan` artifact for each research job, expose it in status/result/debug payloads, and make planner output explicitly consume `problem_analysis` instead of relying only on local query heuristics.

## Why this slice now
Slice 1 introduced `ProblemAnalysis` as the explicit query-framing artifact.
The next correct step is to formalize planning as a first-class runtime artifact rather than leaving planning implicit inside stub behavior and scattered heuristics.

This keeps SourceTrace on the agreed sequence:
1. Problem Analyzer
2. Planner formalization
3. Evidence packing / bounded branching later

## Non-goals
- no branch proposal engine
- no reflection
- no critic
- no UI redesign beyond existing payload surfaces
- no workflow engine rewrite

## Proposed artifact contract
```json
{
  "plan_version": "planner_v2",
  "strategy": "direct_answer|procedural_research|broad_research|news_research|market_scan",
  "objective": "string",
  "steps": [
    {
      "step_id": "step-1",
      "kind": "search",
      "objective": "string",
      "depends_on": []
    }
  ]
}
```

## Bounded planning rules
Planner must remain deterministic and compact.

Inputs:
- query
- `problem_analysis`

Rules:
- strategy is derived from `problem_analysis.query_class`
- objective defaults to `problem_analysis.goal`
- number of steps stays small: 2-4
- no branching or recursive planning in this slice
- steps are descriptive runtime scaffolding, not a full orchestration DSL

## Persistence targets
The plan should appear in:
1. `ResearchJob`
2. `ResearchResultArtifact`

This keeps the plan available in:
- status/debug payloads during execution
- result payloads after execution
- future reflection/branching work

## API surfaces
Expose `execution_plan` in:
- `GET /api/research/status/{job_id}`
- `GET /api/research/result/{job_id}`
- existing debug JSON surfaces through serializer inclusion

## Implementation plan
1. Add minimal plan contracts in the research domain.
2. Persist `execution_plan` on job/result artifacts.
3. Change planner seam to accept `problem_analysis`.
4. Derive explicit strategy + steps from `problem_analysis`.
5. Add payload serializers.
6. Add focused tests for derivation and API exposure.

## Definition of done
- every started job stores `execution_plan`
- planner derives strategy from `problem_analysis`
- completed result artifacts include the same `execution_plan`
- status/result API payloads expose the plan
- focused tests pass

## Risks
### Risk: decorative plan only
Mitigation: planner must directly consume `problem_analysis` in this slice.

### Risk: pseudo-workflow bloat
Mitigation: small fixed contract, 2-4 steps max, no branching.

### Risk: plan drifting from runtime behavior
Mitigation: keep step kinds aligned with actual phases: planning/searching/reading/analyzing/writing.

## Rollback
Revert:
- plan domain contract additions
- `execution_plan` fields on job/result artifacts
- planner signature change
- serializer wiring
- focused tests for this slice
