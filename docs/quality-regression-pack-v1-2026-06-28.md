# SourceTrace v2 quality regression pack v1 — 2026-06-28

## Goal

Create a small canonical regression pack so quality work no longer depends only on memory, scattered live notes, or local interpretation.

This slice is evaluation infrastructure, not a new retrieval heuristic.

## What was added

### Fixture pack
Added:
- `tests/fixtures/v2/quality_regression_pack_v1.json`

Coverage included:
- break-glass official + practical companion
- breach notification dual institutional
- legal-hold institutional survival
- remote-work / Poland public-source survival

Each case records:
- query
- bounded candidate set
- expected selected-evidence shape
- `must_include`
- `must_exclude`
- optional `must_include_one_of`
- brief evaluation note

### Test
Added:
- `tests/unit/v2/test_quality_regression_pack_v1.py`

The test evaluates both:
- selected-evidence API projection
- compiled artifact selected-evidence output

This keeps the regression pack aligned across the main answer-driving evidence surface and the persisted compiled readback path.

## Why this matters

This pack gives the quality line a small shared baseline.

It helps prevent two bad patterns:
1. relying on memory of recent live checks
2. patching toward one hard query family without noticing regressions elsewhere

It also fits the current posture:
- no deterministic query-specific heuristics
- no selector-contract expansion
- no pretending one live run is enough to define quality truth

## Verification

Focused tests passed:
- `tests/unit/v2/test_quality_regression_pack_v1.py`
- `tests/unit/v2/test_authority_relevance_outcome_eval_v1.py`
- `tests/unit/v2/test_authority_relevance_outcome_eval_v2.py`

Result: `3 passed`

## Practical verdict

This is a good production-gap slice.
It does not solve retrieval quality directly, but it makes future retrieval/selection work less fragile and less guess-driven.

## Recommended next bounded slice

`persistence-failure-mode-audit-v1`

Goal:
- inspect the current JSONL/readback posture for partial-write, stale, and incomplete persistence states,
- and decide what is already honest enough versus what still needs a bounded reliability fix
