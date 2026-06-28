# SourceTrace v2 quality regression pack v3 — 2026-06-28

## Goal

Extend the shared regression baseline around the cases that are now improved enough to look acceptable at first glance, but are still not fully clean after the latest retrieval-target-quality and trust-quality-alignment work.

This stays bounded:
- no retrieval heuristics changed
- no selector policy changed
- no trust logic changed

## What was added

Added:
- `tests/fixtures/v2/quality_regression_pack_v3.json`
- `tests/unit/v2/test_quality_regression_pack_v3.py`

Tracked slice:
- break-glass official source with a still-weaker practical companion
- tax guidance institutional pair that remains jurisdiction-mixed

## Why this slice is coherent

`quality-regression-pack-v1` pinned the healthier anchor shapes.
`quality-regression-pack-v2` pinned obviously weak or unstable shapes.

This v3 slice fills the gap between them:
- cases that improved materially,
- cases that are broadly acceptable,
- but cases that still contain visible quality imperfections the current trust layer does not flag.

That makes the shared baseline more honest.
It prevents future work from treating these cases as either fully solved or fully broken.

## What the v3 test checks

For each case, the test verifies:
- selected-evidence API projection
- compiled artifact selected-evidence output
- current operator-trust projection

The important posture point is intentional:
- break-glass still projects as `usable` because one strong institutional source anchors the pair, even though the companion is weaker
- tax guidance still projects as `usable` because the current trust layer does not model jurisdiction mismatch

These are not endorsements of those shapes.
They are the current bounded baseline after the latest retrieval/trust improvements.

## Verification

Focused tests passed:
- `tests/unit/v2/test_quality_regression_pack_v1.py`
- `tests/unit/v2/test_quality_regression_pack_v2.py`
- `tests/unit/v2/test_quality_regression_pack_v3.py`
- `tests/unit/v2/test_trust_quality_alignment.py`
- `tests/unit/v2/test_operator_trust_contract.py`

## Practical verdict

This was the right bounded follow-up.
The baseline now covers:
- healthy anchor shapes,
- clearly weak/unstable shapes,
- and improved-but-still-imperfect shapes that could otherwise disappear from memory because they currently look "good enough."
