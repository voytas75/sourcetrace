# Deep Research Evidence Packing implementation slice brief v1

Status: planned / implementing
Date: 2026-06-24
Scope: bounded Slice 3 implementation for SourceTrace Deep Research

## Goal
Formalize a minimal `ResearchEvidencePack` artifact that captures how findings were grouped for synthesis, persist it on completed result artifacts, expose it in result/debug payloads, and keep packing logic aligned with `problem_analysis` and `execution_plan`.

## Why this slice now
`ProblemAnalysis` and `ResearchExecutionPlan` now exist as explicit upstream artifacts.
The next correct step is to make evidence shaping explicit too, so synthesis stops depending on an implicit local packing decision only visible inside runtime code.

This keeps the roadmap bounded and in order:
1. Problem Analyzer
2. Planner formalization
3. Evidence packing hardening

## Non-goals
- no branch engine yet
- no reflection yet
- no critic yet
- no rewrite of synthesis prompts beyond consuming the same packed evidence shape already used internally
- no new persistence subsystem beyond result artifact storage

## Proposed artifact contract
```json
{
  "pack_version": "evidence_pack_v1",
  "query_class": "...",
  "core": [{"url":"...","title":"...","summary":"..."}],
  "supporting": [{"url":"...","title":"...","summary":"..."}],
  "background": [{"url":"...","title":"...","summary":"..."}],
  "has_direct_procedural_evidence": true
}
```

## Bounded rules
- pack remains deterministic
- no scoring engine yet
- no branch-aware pack separation yet
- just make the existing packing result durable and inspectable

## Persistence target
- `ResearchResultArtifact`

This is enough for:
- result inspection
- debug/status follow-up
- later reflection / artifact promotion work

## API surfaces
Expose `evidence_pack` in:
- `GET /api/research/result/{job_id}`
- existing debug JSON surfaces through serializer inclusion

## Implementation plan
1. Add evidence-pack domain contracts.
2. Persist the existing pack result on `ResearchResultArtifact`.
3. Keep synthesis path using the same packing logic.
4. Expose serializer payloads.
5. Add focused tests.

## Definition of done
- completed result artifacts include `evidence_pack`
- pack counts and grouping are inspectable from result payloads
- synthesis still works
- focused tests pass

## Risks
### Risk: decorative artifact only
Mitigation: persist the exact pack used by runtime before synthesis.

### Risk: schema bloat
Mitigation: keep only grouped evidence refs + one direct-procedural flag.

### Risk: drift from runtime behavior
Mitigation: generate artifact directly from existing `_pack_evidence_for_synthesis()` output.

## Rollback
Revert:
- evidence-pack contract additions
- result artifact field
- serializer wiring
- focused tests for this slice
