# SourceTrace v2 institutional retrieval window v1 — 2026-06-28

## Goal

Relieve premature top-N truncation for institutional-intent queries by widening the bounded retrieval window modestly before source-mix shaping, then trimming back to the normal bounded pool.

This slice stays upstream.
It does not widen downstream selector policy.

## Change made

Updated `src/sourcetrace_v2/execution/stages/retrieval.py`.

What changed:
- for institutional-intent queries, retrieval now asks the search gateway for a slightly larger window (`limit + 3`)
- source typing and source-mix shaping run over that larger temporary pool
- after shaping, the pool is trimmed back to the normal bounded candidate limit
- non-institutional-intent queries keep the original retrieval window

This preserves boundedness while giving lower-ranked institutional/public candidates a chance to survive into the candidate pool.

## Verification

### Focused tests
Focused tests passed:
- `tests/unit/v2/test_institutional_retrieval_window.py`
- `tests/unit/v2/test_source_mix_shaping.py`
- `tests/unit/v2/test_source_typing.py`

Result: `9 passed`

### Live verification
Ran the two hardest cases again.

#### 1. Poland remote-work reporting
New candidate pool:
- `Remote work - Ministry of Family, Labour and Social Policy - Gov.pl website` — `institutional`
- `Implementing Remote Work for Employees Based in Poland` — `unknown`
- `New OECD guidelines on remote work from abroad - Deloitte` — `unknown`

Selected:
- `gov.pl` institutional page
- `easyeor.pl` advisory/commercial page

Verdict:
- material improvement
- the public-institutional Poland source now survives into the v2 pool and wins the first slot

#### 2. Legal-hold / records-retention
New candidate pool:
- `PDF Records Management Guidance` — `institutional`
- `Records Management Regulations and Guidance | National Archives` — `institutional`
- `Legal Hold Best Practices: A Complete Guide for Organizations` — `vendor`

Selected:
- `PDF Records Management Guidance`
- `Records Management Regulations and Guidance | National Archives`

Verdict:
- strong improvement
- the pool is no longer trapped in vendor/vendor
- institutional/public-law sources now survive and dominate the selected shape

## Practical verdict

This slice worked.

The sharper diagnosis from the previous step was correct:
- the main issue was early truncation,
- not a pure provider miss,
- and not another selector/judgment weakness.

A small upstream retrieval-window expansion was enough to materially improve both hard live cases.

## Recommended next bounded slice

`institutional-retrieval-window-evaluation-v1`

Goal:
- run a slightly broader live/eval pack to check whether the widened institutional-intent window helps consistently without causing obvious regressions or commentary/vendor crowding in easier cases
