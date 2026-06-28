# SourceTrace v2 authority-relevance source typing consumer validation v1 — 2026-06-28

## Goal

Validate one real persisted/readback consumer boundary for the new `source_type` metadata.

This slice stays narrow.
It does not add new shaping rules or change selector policy.

## Validation boundary

Chose the persisted execution readback / HTTP projection path backed by JSONL storage.

Why this is the right seam:
- it is a real downstream consumer boundary
- it proves `source_type` survives persistence and readback
- it is sharper than only checking in-memory projection or runtime state

## What changed

- added focused coverage in `tests/unit/v2/test_jsonl_storage.py`
- validated that persisted execution readback exposes `source_type` in the execution/evidence-input candidate surface
- kept the validation bounded to presence/shape rather than pretending current shallow classification is perfect ground truth

## Verification

Focused tests passed:
- `tests/unit/v2/test_jsonl_storage.py`
- `tests/unit/v2/test_source_typing.py`
- `tests/unit/v2/test_source_type_jsonl_roundtrip.py`

Result: `6 passed`

## Practical verdict

This is enough to treat `source_type` as a real persisted consumer-facing metadata field in bounded form.

That matters because the next shaping/diagnostics slices can now rely on:
- explicit source-type state,
- visible readback,
- and stable persisted transport,
without having to infer everything from title/url again.

## Recommended next bounded slice

`authority-relevance-source-type-aware-shaping-v1`

Goal:
- use the new explicit `source_type` state to make upstream source-mix shaping cleaner and less implicit
- keep downstream selector policy unchanged in the same slice
