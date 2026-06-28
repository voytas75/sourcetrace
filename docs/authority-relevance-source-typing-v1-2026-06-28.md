# SourceTrace v2 authority-relevance source typing v1 — 2026-06-28

## Goal

Add explicit early source-type metadata so upstream shaping and diagnostics can reason about source classes more cleanly.

This slice remains upstream.
It does not change downstream selected-evidence policy.

## Change made

Added `source_type` to retrieval candidates with a bounded early classification pass.

Current bounded classes:
- `institutional`
- `vendor`
- `commentary`
- `unknown`

Where it now lives:
- `RetrievedEvidenceCandidate.source_type`
- minimal/readback/evidence projections
- JSONL result-artifact readback

Current classification posture is intentionally shallow and heuristic:
- institutional: government/EU/regulator-style hosts and selected institutional titles
- vendor: known vendor-style hosts
- commentary: blog/social/commentary-like hosts and selected title markers
- unknown: fallback

## Why this is useful

The previous shaping slice proved that a little upstream institutional preference can help, but it was still operating on implicit host/title scoring.

This slice improves the posture by making source-type assumptions explicit and inspectable.
That helps with:
- cleaner diagnostics
- cleaner future shaping
- less opaque source-mix behavior

## Verification

### Focused tests
Focused source-typing and regression tests passed:
- `tests/unit/v2/test_source_typing.py`
- `tests/unit/v2/test_source_type_jsonl_roundtrip.py`
- `tests/unit/v2/test_source_mix_shaping.py`
- `tests/unit/v2/test_query_handoff_contract.py`

Result: `5 passed`

### Live sanity check
Ran a live execution/readback check on:
- `data breach notification checklist authority official guidance`

Observed:
- selected titles remained FTC + ICO
- selected `source_type` values were both `institutional`
- candidate source types in readback were visible and all marked `institutional` for that case

Interpretation:
- explicit source typing is now visible in the runtime/readback surface
- strongest institutional case remains stable

## Practical verdict

This is a good bounded infrastructure slice.
It does not solve source-mix quality by itself, but it turns a previously implicit upstream assumption into explicit state that later shaping/diagnostics can use more cleanly.

## Recommended next bounded slice

`authority-relevance-source-typing-consumer-validation-v1`

Goal:
- validate one real downstream persisted/readback consumer boundary for `source_type`
- keep selector policy unchanged in the same slice
