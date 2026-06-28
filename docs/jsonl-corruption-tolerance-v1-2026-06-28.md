# SourceTrace v2 JSONL corruption tolerance v1 — 2026-06-28

## Goal

Add a narrow tolerance posture for malformed/truncated trailing JSONL lines so readback behaves more gracefully under obvious tail corruption, without pretending the entire file is healthy.

## Change made

Updated `src/sourcetrace_v2/adapters/storage/jsonl.py`.

What changed:
- `_read_jsonl(...)` now tolerates a malformed **last non-empty line**
- if the broken line is clearly the trailing tail entry, readback stops there and preserves earlier valid rows
- if corruption appears earlier in the file and valid rows still follow, readback still raises instead of silently hiding broader damage

This is intentionally narrow.
It does not claim general corruption recovery.
It only improves the most plausible append-tail failure mode.

## Verification

Focused tests passed:
- `tests/unit/v2/test_jsonl_storage.py`
- `tests/unit/v2/test_readback.py`
- `tests/unit/v2/test_operator_readback.py`

Result: `12 passed`

New focused coverage includes:
- truncated trailing result line is tolerated and earlier valid row still reads back
- non-trailing corruption still raises instead of being silently ignored

## Practical verdict

This is a good bounded reliability improvement.

It does **not** make JSONL fully production-grade.
But it does improve the most realistic crash/interruption artifact:
- a broken final append line no longer destroys the whole readback path
- broader corruption still fails loudly

That is the right tradeoff for this slice.

## Recommended next bounded slice

`operator-trust-contract-v1`

Goal:
- define a light operator-facing truth contract for result usability (`usable / weak / needs_review / degraded`) so runtime success is not confused with trustworthy research quality
