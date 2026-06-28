# SourceTrace v2 quality regression pack v2 — 2026-06-28

## Goal

Expand the shared quality regression baseline with the unstable and ambiguous live retrieval cases exposed by the broader evaluation pack.

This slice strengthens evaluation discipline.
It does not add new retrieval heuristics.

## What was added

### Fixture pack
Added:
- `tests/fixtures/v2/quality_regression_pack_v2.json`

New tracked cases:
- legal-hold vendor/vendor fallback shape
- remote-work Poland advisory/commercial drift shape
- cross-border data transfer advisory/commercial drift shape
- tax deadline jurisdiction-mixed institutional shape

### Test
Added:
- `tests/unit/v2/test_quality_regression_pack_v2.py`

Like v1, the test evaluates both:
- selected-evidence API projection
- compiled artifact selected-evidence output

## Why this matters

`quality-regression-pack-v1` captured the healthier anchor cases.
This v2 expansion captures the cases that are currently:
- weak,
- unstable,
- or ambiguous.

That matters because the next retrieval refinement should be judged against:
- what healthy looks like,
- and what currently weak/unstable shapes look like,
- instead of relying on live anecdotes or memory.

## Important posture note

These new v2 cases do **not** claim that the current weak shapes are desirable.
They are recorded because they are currently real and operationally relevant.

The point is to make them visible, reproducible, and harder to forget.
That gives the next refinement step a sharper and more honest baseline.

## Verification

Focused tests passed:
- `tests/unit/v2/test_quality_regression_pack_v1.py`
- `tests/unit/v2/test_quality_regression_pack_v2.py`
- `tests/unit/v2/test_authority_relevance_outcome_eval_v2.py`

Result: `3 passed`

## Practical verdict

This is the right next move after the broader retrieval-quality evaluation pack.
It hardens the shared baseline before any further retrieval refinement, and it keeps the work away from ad hoc heuristic patching.

## Recommended next bounded slice

`retrieval-refinement-decision-v1`

Goal:
- use the stronger regression baseline plus the recent live evaluation evidence to decide what the next retrieval refinement should actually target,
- without jumping straight into another local patch
