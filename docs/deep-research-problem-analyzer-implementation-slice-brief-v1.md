# Deep Research Problem Analyzer implementation slice brief v1

Status: planned / implementing
Date: 2026-06-24
Scope: bounded Slice 1 implementation for SourceTrace Deep Research

## Goal
Add a minimal `ProblemAnalysis` artifact that is produced for every research job, persisted with the job/result/compiled artifact views, and exposed in API payloads for status/debug/result inspection.

## Why this slice now
The architecture-upgrade plan established that SourceTrace should formalize query understanding before adding richer planner, branching, reflection, or compiled-memory behavior.

A bounded `ProblemAnalysis` artifact gives the runtime one explicit input contract without forcing a rewrite.

## Non-goals
- no planner rewrite
- no branch proposal engine
- no reflection loop
- no critic
- no memory / graph subsystem
- no UI redesign beyond surfacing the new payload field through existing status/result/debug surfaces

## Proposed artifact contract
```json
{
  "query_class": "procedural_admin|broad_concept|current_news|market_symbol|unknown",
  "complexity": "low|medium|high",
  "goal": "string",
  "focus_areas": ["string"],
  "constraints": ["string"],
  "analysis_version": "problem_analyzer_v1"
}
```

## Bounded derivation rules
`ProblemAnalysis` should be deterministic and derived from existing runtime heuristics.

Inputs:
- raw query
- existing query-class detection
- lightweight procedural / market / news cues already present in the runtime

Rules:
- `query_class` comes from existing `_classify_query()` logic
- `goal` defaults to normalized user query text
- `complexity` is inferred coarsely:
  - `low` for direct procedural/admin and narrow market questions
  - `high` for broad concept / architecture / comparison style queries
  - `medium` otherwise
- `focus_areas` are short bounded hints derived from the query class
- `constraints` are only added when the runtime already knows a constraint implicitly, e.g. procedural exactness or recency sensitivity

## Persistence targets
The artifact should appear in:
1. `ResearchJob`
2. `ResearchResultArtifact`
3. `CompiledResearchArtifact`

This keeps the artifact visible across:
- status payloads,
- result payloads,
- compiled artifact/debug inspection,
- future planner/reflection inputs.

## API surfaces
Expose `problem_analysis` in:
- `GET /api/research/status/{job_id}`
- `GET /api/research/result/{job_id}`
- compiled artifact payloads
- existing raw JSON debug surfaces automatically, via serializer inclusion

## Implementation plan
1. Add `ProblemAnalysis` domain contract and export it.
2. Add optional `problem_analysis` field to job/result/compiled artifact records.
3. Derive `ProblemAnalysis` at job acceptance and persist it on the job.
4. Carry the same artifact into the final result and compiled artifact projection.
5. Add payload serializers.
6. Add focused tests for:
   - derivation
   - worker persistence into result/compiled artifact
   - WSGI status/result payload exposure

## Definition of done
- every started job stores `problem_analysis`
- completed result artifacts include the same `problem_analysis`
- compiled artifacts include a `problem_analysis_snapshot`
- status/result/compiled API payloads expose the artifact
- targeted tests pass

## Risks
### Risk: schema bloat
Mitigation: keep the contract tiny and deterministic.

### Risk: artifact becomes decorative only
Mitigation: persist it now specifically so Planner v2 can consume it next.

### Risk: duplicate truth across evaluator and problem analysis
Mitigation: keep roles separate:
- `ProblemAnalysis` = input framing
- `Evaluation` = output quality judgment

## Rollback
Revert:
- domain contract additions
- `problem_analysis` / `problem_analysis_snapshot` fields
- serializer wiring
- focused tests for this slice

No data migration is required for the file-backed local runtime because missing fields remain optional.