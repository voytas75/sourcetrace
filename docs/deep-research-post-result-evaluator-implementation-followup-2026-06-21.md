# Deep Research post-result evaluator implementation follow-up — 2026-06-21

Status: completed bounded slice
Date: 2026-06-21
Scope: first implementation pass for the post-result evaluator designed in `docs/deep-research-post-result-evaluator-design-v1.md`.

## 1. Goal

Implement post-result evaluator v1 as a bounded, structured diagnostic layer attached to completed Deep Research result artifacts.

The slice goal was not to add automatic rewrite/research loops.
The goal was to make completed artifacts carry query-class-aware quality diagnostics.

---

## 2. What was implemented

### A. Structured evaluation artifact
Added a structured evaluation model to the research domain:
- `ResearchQueryClass`
- `ResearchEvaluationVerdict`
- `ResearchEvaluationArtifact`

This evaluation is now stored on `ResearchResultArtifact` as:
- `evaluation: ResearchEvaluationArtifact | None`

### B. Query classification
Added a small internal query classifier for initial buckets:
- `market_symbol`
- `procedural_admin`
- `broad_concept`
- `current_news`
- `unknown`

### C. Post-result evaluator
Implemented a bounded evaluator that inspects:
- query,
- persisted findings,
- final report,
- result stats.

It currently produces:
- `query_class`
- `source_quality_verdict`
- `source_quality_reasons`
- `relevance_verdict`
- `relevance_risks`
- `truthfulness_verdict`
- `overclaim_risks`
- `missing_checks`
- `recommended_next_check`
- `should_revise_report`

### D. Runtime integration
The evaluator now runs automatically when a Deep Research result artifact is created:
- for normal completed results,
- for salvaged partial results.

### E. Persistence and API surface
Evaluation data is now serialized/deserialized in filesystem persistence and exposed in the research result API payload.

This keeps the first implementation pass observable and benchmark-friendly without adding a separate repository layer yet.

---

## 3. Deliberate v1 constraints kept intact

Still intentionally true after implementation:
- no hidden second retrieval pass,
- no auto-rewrite,
- no evaluator-driven rerun,
- no new external side effects,
- evaluation remains diagnostic first.

So the implementation still matches the original design posture.

---

## 4. Verification

### Tests
- added/updated unit coverage for:
  - domain artifact support,
  - query classification,
  - procedural-query evaluation behavior.

### Full gate
- full repo gate passed: `398 passed`

---

## 5. Current limitations

This v1 evaluator is useful, but still intentionally simple.

Known limits:
- query classification is heuristic,
- verdict logic is rule-based rather than model-driven,
- evaluation is attached to the result artifact rather than stored in a dedicated evaluation repository,
- broad-concept and current-news judgment is still relatively shallow,
- `should_revise_report` is advisory only.

These are acceptable limits for v1.

---

## 6. Verdict

This slice succeeded.

SourceTrace Deep Research now has a first real post-result evaluation layer that:
- is query-class-aware,
- returns structured diagnostics,
- is persisted,
- is API-visible,
- and is safe because it does not mutate the result.

That is enough to support future benchmarking, UI surfacing, and later conditional revision work.

---

## 7. Recommended next step

Do not immediately turn this into auto-rewrite.

The next best moves are now one of:
1. expose evaluator output more clearly in `/research` UI,
2. use evaluator output in benchmark scoring/reporting,
3. later consider bounded evaluator-driven conditional revision only after enough weak-result examples are collected.
