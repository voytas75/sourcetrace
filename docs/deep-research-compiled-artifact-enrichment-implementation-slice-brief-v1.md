# Deep Research compiled artifact enrichment implementation slice brief v1

Status: proposed implementation slice
Date: 2026-06-21
Scope: bounded upgrade of compiled artifact projection quality using already-available result/evaluator data.

## 1. Slice verdict

This is the correct next slice after `artifact lint / health v1`.

Reason:
- lint is now exposing real weakness,
- but the weakness is not mainly in lint logic,
- it is in the current `result -> compiled artifact` projection being too thin.

So the right move is to improve the compiled artifact itself.

---

## 2. Problem statement

Current compiled artifacts are structurally valid, but often too weakly populated.

Observed gap from spot-check:
- `missing_evidence`
- `missing_sources`
- `weak_source_quality`
- `needs_revision`

Some of that reflects true evaluator caution.
But some of it is projection loss:
- compiled artifact does not always carry enough evidence forward,
- source refs can end up too thin,
- claims are just a shallow copy of raw finding summaries,
- follow-up structure is minimal.

That means the compiled layer is currently underrepresenting the quality already achieved lower in the pipeline.

---

## 3. Objective

Improve compiled artifact generation so it carries forward stronger:
- evidence refs,
- source refs,
- claims,
- open questions,
- next checks,
- and quality context.

Desired outcome:
- healthy runs should produce materially healthier compiled artifacts,
- lint should stay honest but become less red by default when the underlying run really was good.

---

## 4. Non-goals

Do not do these in this slice:
- no cross-run merge,
- no artifact rewrite loop,
- no LLM-based artifact editing,
- no UI redesign,
- no semantic search layer,
- no claim graph yet.

This is a projection-enrichment slice, not a new subsystem.

---

## 5. Main enrichment targets

### A. Better source carry-forward
Ensure `source_refs` is reliably populated from the strongest available source set.

Priority order:
1. explicit result sources
2. supporting evidence refs
3. finding-derived fallbacks

### B. Better evidence carry-forward
Ensure `supporting_evidence` is not empty when usable finding/source material exists.

Prefer:
- top evidence-bearing raw findings
- not just generic fallbacks

### C. Better claims
Current claims are too close to raw finding summaries.

v1 improvement can still stay deterministic:
- prefer top findings
- cap at small count
- trim noise
- avoid duplicative claims

### D. Better follow-up structure
Ensure:
- evaluator `missing_checks`
- report `Uncertainty`
- report `Next checks`
- evaluator `recommended_next_check`

are merged into more useful `open_questions` and `next_checks` rather than dropped or kept too narrowly.

---

## 6. Recommended projection rules

### Source refs
- prefer top result sources,
- if empty, derive from supporting evidence,
- dedupe by URL,
- keep small cap like 5–8.

### Supporting evidence
- use top raw findings with real summaries,
- drop obvious duplicates,
- preserve URL/title/summary,
- keep small cap like 4–6.

### Claims
- derive from strongest findings,
- dedupe near-identical text,
- keep 3–5 concise claims,
- attach matching evidence refs where possible.

### Open questions / next checks
- normalize and dedupe,
- preserve evaluator-driven checks,
- avoid empty output when the run clearly surfaced uncertainty.

---

## 7. Quality bar

This slice should specifically aim to reduce false-negative lint weakness.

Meaning:
- do not just silence lint,
- make the artifact genuinely better populated.

A good success signal is:
- procedural runs with strong evaluator output stop looking obviously underfilled at the compiled layer.

---

## 8. Minimal implementation shape

Likely enough:
- refine `_compile_research_artifact(...)`
- add helper functions for:
  - claim selection/dedup
  - source ref projection/dedup
  - evidence ref projection/dedup
  - follow-up normalization

No new subsystem needed.

---

## 9. Tests to add

### A. Enriched procedural result
Result with:
- sources,
- findings,
- evaluator snapshot,
- uncertainty / next checks

Expected:
- compiled artifact has non-empty `source_refs`
- compiled artifact has non-empty `supporting_evidence`
- claims are deduped and concise
- next checks preserved

### B. Sparse result fallback
Even sparse results should still produce the best possible artifact without crashing.

### C. Lint interaction test
An enriched artifact should lint better than the current thin projection in comparable conditions.

---

## 10. Verification steps

After implementation:
1. run focused tests,
2. run full gate,
3. execute one real procedural run,
4. inspect compiled artifact,
5. inspect lint output,
6. confirm the artifact is richer and lint is more truthful.

---

## 11. Success criteria

Minimum success:
- compiled artifacts preserve more usable source/evidence structure,
- lint keeps working,
- full gate remains green.

Preferred success:
- a good procedural run produces a compiled artifact that no longer looks obviously hollow,
- lint shifts from artificial weakness toward more accurate review signals.

---

## 12. Rollback

If enrichment becomes noisy:
- keep lint layer,
- revert projection heuristics to smaller rules,
- preserve only the parts that clearly improve artifact readability and health.

---\n
## 13. Final recommendation

Proceed with `compiled artifact enrichment v1` now.

Reason:
- the current bottleneck has been identified clearly by the new lint layer,
- the next value is in improving the knowledge object itself,
- and this remains a small, local, benchmarkable slice.
