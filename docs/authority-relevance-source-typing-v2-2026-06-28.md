# SourceTrace v2 authority-relevance source typing v2 — 2026-06-28

## Goal

Improve the shallow `source_type` classifier in a bounded way for the weak live classes that still looked too coarse after source-type-aware shaping.

This slice stays upstream.
It does not change downstream selector policy.

## Change made

Extended the source classifier with a slightly richer but still bounded marker set.

What improved:
- more explicit institutional host coverage (for example additional regulator/EU-style hosts)
- broader vendor host coverage for practical/legal-tech style sources
- broader commentary host/title coverage for law-firm and advisory-style commentary sources seen in weak live cases

This stays intentionally shallow.
It is still a lightweight source classifier, not a final authority system.

## Verification

### Focused tests
Focused tests passed:
- `tests/unit/v2/test_source_typing.py`
- `tests/unit/v2/test_source_mix_shaping.py`
- `tests/unit/v2/test_source_type_jsonl_roundtrip.py`

Result: `6 passed`

### Live sanity check
Ran a live check on:
- `remote work reporting obligations Poland employer official guidance`

Observed selected pair:
- `Remote work from abroad: OECD 2025 guidance for Poland - getsix`
- `An employer’s guide to remote work regulations in Poland - British Polish Chamber of Commerce`

Observed source types:
- `unknown`
- `commentary`

Interpretation:
- the slice did help expose commentary more explicitly in one weak live case
- it did **not** fully solve classification for the full pair; one selected result remained `unknown`
- that is acceptable for this bounded slice because the goal was to improve shallow typing for observed weak classes, not to claim complete source truth

## Practical verdict

This was a useful bounded refinement.
The classifier is slightly more honest and useful for weak-case diagnostics than v1.

It also surfaced the next limit clearly:
- the remaining problem is not only missing source labels,
- but the residual `unknown` bucket still being too broad for some practical-but-not-clearly-institutional results.

## Recommended next bounded slice

`authority-relevance-source-typing-unknown-bucket-diagnostics-v1`

Goal:
- inspect which real weak-case sources are still falling into `unknown`
- decide whether the next bounded move should split that bucket more cleanly or just improve markers for a few recurring classes
