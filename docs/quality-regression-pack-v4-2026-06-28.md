# SourceTrace v2 quality regression pack v4 — 2026-06-28

## Goal

Pin the small subset of post-query-refinement live-eval outcomes that now look stable enough to become part of the shared regression baseline.

This stays bounded:
- no retrieval heuristics changed
- no selector policy changed
- no trust logic changed
- no runtime behavior changed

## What was added

Added:
- `tests/fixtures/v2/quality_regression_pack_v4.json`
- `tests/unit/v2/test_quality_regression_pack_v4.py`

Tracked slice:
- legal hold improved from the earlier weak drift into a public/institutional pair, but still remains `needs_review`
- tax guidance improved from the earlier jurisdiction-mixed institutional pair into a same-authority IRS pair that now stays `usable`

## Why only these cases

The live eval produced four outcomes, but only two are clean enough to pin as a bounded shared baseline update:
- `legal hold` changed materially and in a durable-looking way
- `tax guidance` changed materially and crossed an important trust boundary

The other two cases were left out on purpose:
- `remote-work Poland` improved, but still does not have a clear exact-subject official winner
- `cross-border data transfer` remains mixed and is still better treated as live-eval caution rather than a shared regression target

## What the v4 test checks

For each case, the test verifies:
- selected-evidence API projection
- compiled artifact selected-evidence output
- current operator-trust projection

This keeps the slice aligned with the existing regression-pack pattern instead of creating a new harness.

## Practical verdict

This is the smallest coherent regression-baseline update after the live eval:
- it preserves the older v1/v2/v3 history
- it pins the two live outcomes that materially changed
- it avoids locking in the still-unclean cases as if they were settled
