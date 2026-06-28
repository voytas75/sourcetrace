# SourceTrace v2 retrieval target quality refinement v1 — 2026-06-28

## Goal

Improve upstream candidate targeting quality inside the bounded retrieval pool without introducing deterministic query-specific or country-specific heuristics and without changing selector policy.

## Change made

Implemented a bounded target-quality scoring layer inside retrieval shaping in:
- `src/sourcetrace_v2/execution/stages/retrieval.py`

What changed:
- institutional-intent source-mix ordering still uses the existing source-type priority first
- within that ordering, candidates now also receive a general target-quality score based on:
  - overlap between query focus tokens and candidate title/snippet/url
  - overlap of simple focus phrases derived from the query
- intent-only tokens and generic stopwords are excluded so the score is driven more by topic/jurisdiction-bearing terms

This remains upstream and bounded.
It does not add per-query override rules.

## Verification

### Focused regression/tests
Passed:
- `tests/unit/v2/test_quality_regression_pack_v1.py`
- `tests/unit/v2/test_quality_regression_pack_v2.py`
- `tests/unit/v2/test_authority_relevance_outcome_eval_v1.py`
- `tests/unit/v2/test_authority_relevance_outcome_eval_v2.py`
- `tests/unit/v2/test_source_mix_shaping.py`
- `tests/unit/v2/test_retrieval_target_quality.py`

Result: `10 passed`

### Live sanity check
Checked:
- remote-work Poland
- cross-border data transfer
- tax guidance

Observed:
- **remote-work Poland**: still weak; selected shape stayed advisory/commercial (`easyeor`, `L&E Global`)
- **cross-border data transfer**: improved; an institutional PDPC source now led the selected pair with an advisory companion behind it
- **tax guidance**: improved; selected pair became jurisdiction-consistent institutional (`IRS`, `IRS`) instead of a mixed institutional pair

## Practical verdict

This is a real bounded improvement, but not a full retrieval-line closure.

What improved:
- candidate targeting quality within the bounded pool is better
- jurisdiction/topic targeting improved in at least some previously ambiguous cases
- cross-border and tax-guidance shapes improved without selector changes

What remains weak:
- remote-work Poland still drifts into advisory/commercial material
- that case still looks like a harder retrieval-side instability, not solved by this refinement alone

## Recommended next bounded slice

`retrieval-target-quality-evaluation-v1`

Goal:
- run a slightly broader post-refinement evaluation pass to confirm where this target-quality refinement helps consistently, where it does not, and whether the next step should remain in retrieval or move to trust-quality alignment
