# SourceTrace v2 authority-relevance source-type-aware shaping v1 — 2026-06-28

## Goal

Clean up upstream source-mix shaping so it uses explicit `source_type` metadata as the primary signal instead of mostly implicit host/title scoring.

This slice stays upstream.
It does not change downstream selected-evidence policy.

## Change made

Refactored source-mix shaping in `RetrievalStage` so the shaping pass now prefers explicit source-type state first.

Current priority posture:
- `institutional` > `vendor` > `unknown` > `commentary`
- non-empty snippet still gives a small bounded bump

Behavior notes:
- if candidates already carry explicit `source_type`, shaping uses that directly
- if all candidates are still `unknown`, shaping falls back to the existing early annotation pass before reordering
- this makes shaping less opaque and less dependent on duplicated implicit host/title logic

## Verification

### Focused tests
Focused tests passed:
- `tests/unit/v2/test_source_mix_shaping.py`
- `tests/unit/v2/test_source_typing.py`
- `tests/unit/v2/test_source_type_jsonl_roundtrip.py`

Result: `5 passed`

### Live sanity check
Ran a live check on:
- `legal hold steps records retention official guidance`

Observed selected pair:
- Everlaw litigation holds guide
- Venio legal hold best practices guide

Observed source types:
- `vendor`
- `vendor`

Interpretation:
- the shaping logic is now cleaner and explicit-source-type-aware
- but this live case still lands an all-vendor pair because the candidate pool itself remains vendor-heavy for this topic/query shape
- that is a useful result: it suggests the remaining limitation is not hidden shaping ambiguity anymore, but upstream candidate availability / classification granularity for this query class

## Practical verdict

This is a good cleanup slice.
It makes source-mix shaping easier to reason about and easier to evolve.
It does not, by itself, guarantee institutional wins when the provider candidate pool remains mostly vendor/practical.

## Recommended next bounded slice

`authority-relevance-source-typing-v2`

Goal:
- improve the source classifier itself in a bounded way for the observed weak classes
- keep downstream selector policy unchanged in the same slice
