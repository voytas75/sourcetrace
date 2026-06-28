# SourceTrace v2 operator trust contract v1 — 2026-06-28

## Goal

Define a light operator-facing truth contract so a technically successful runtime path is not confused with a trustworthy research result.

This slice adds projection semantics, not retrieval heuristics.

## Contract

Added a small `trust` block on persisted execution readback.

Statuses:
- `usable`
- `weak`
- `needs_review`
- `degraded`

Current bounded meanings:
- `degraded`
  - persistence is incomplete, or
  - one or more stages failed
- `weak`
  - run completed, but only with degraded LLM calls and no stronger structural red flags
- `needs_review`
  - run completed, but evidence surface is too thin (for example no selected evidence, too-thin selected evidence, or too-thin candidate pool)
- `usable`
  - no current trust warnings were triggered

The `trust` block also exposes:
- `reasons`
- `selected_evidence_count`
- `candidate_count`

## Why this matters

Before this slice, the system was already decent at saying:
- whether persistence succeeded
- whether receipts existed
- what evidence was selected

But it did not give one compact operator-facing answer to:
- "should I treat this result as usable right now, or with caution?"

This slice adds that first explicit answer without pretending to solve all confidence modeling.

## Verification

Focused tests passed:
- `tests/unit/v2/test_operator_trust_contract.py`
- `tests/unit/v2/test_api_readback_projection.py`
- `tests/unit/v2/test_operator_readback.py`

Result: `8 passed`

## Practical verdict

This is the right level of bounded truth contract for now.
It is intentionally simple.
It gives operators a more honest top-line status without dragging the system into fake precision or broad policy expansion.

## Recommended next bounded slice

`jsonl-durability-posture-v1`

Goal:
- decide explicitly whether the current JSONL substrate is acceptable for the current deployment posture under stated limits, or whether one more bounded durability fix is required before calling the storage line good enough
