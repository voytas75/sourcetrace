# SourceTrace v2 bounded quality pass — 2026-06-27

## Scope

Run one short quality pass over the new v2 eval corpus and record what it really proves.

Corpus exercised:
- `stubbed_memory`
- `searxng_stubbed_jsonl`
- `preferred_search_stubbed_jsonl`

Assertions exercised:
- run status
- retrieval candidate count
- selected-evidence count
- selected-evidence basis
- compiled-artifact presence
- compiled-artifact readback status
- top provider on provider-backed paths

## Result

Current bounded quality pass status: **PASS**

Observed outcome:
- stub path is stable
- SearxNG-backed retrieval path is stable
- preferred-search path with Unified Search first is stable
- selected-evidence policy behaves consistently across the exercised corpus
- compiled artifact + compiled readback surfaces stay coherent across the exercised corpus

## What this pass proves

It proves that the current bounded v2 system is coherent across:
- execution
- retrieval attribution
- selected-evidence projection
- compiled artifact projection
- compiled artifact readback

It also proves that:
- provider-backed retrieval paths do not break the current evidence/compiled surface contract
- the eval corpus is runnable and useful as a reusable regression boundary

## What this pass does not prove

It does **not** prove:
- broad retrieval quality on real-world topics
- high-confidence evidence relevance
- evidence-role sophistication beyond the current bounded policy
- benchmark-grade quality scoring
- provider breadth beyond the currently exercised seams

## Sharpest remaining weakness

The sharpest remaining weakness is no longer contract shape.
It is **evidence quality depth**:
- selected evidence is now explainable and slightly quality-aware,
- but it is still a small deterministic heuristic layer, not a richer evidence judgment boundary.

## Recommended next bounded slice

Prefer one of:
1. `selected-evidence policy v2` — add one more bounded quality rule (for example provider/domain diversity or compact relevance guard), or
2. `eval corpus v2` — add a few more representative cases before changing policy again.

Recommendation: **eval corpus v2 first** if the goal is confidence; **selected-evidence policy v2** first if the goal is capability.
