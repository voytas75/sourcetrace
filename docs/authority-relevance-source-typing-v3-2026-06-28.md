# SourceTrace v2 authority-relevance source typing v3 — 2026-06-28

## Goal

Reduce the residual `unknown` bucket for the recurring weak-case source families identified by the previous diagnostics, while keeping the same four source-type buckets.

This slice stays upstream.
It does not change downstream selector policy.

## Change made

Refined markers for two recurring unknown families:

1. **professional/advisory hosts**
- added bounded commentary-style host coverage for recurring consultancy/advisory domains seen in weak live cases (for example `vansurksum.com`, `getsix`-style hosts)

2. **hosted vendor/practical PDFs**
- added title/path-aware vendor hints for hosted practical PDFs whose host is not itself vendor-branded but whose document provenance is clearly vendor/practical (for example CLOC-hosted OpenText legal-hold material)

The taxonomy stayed the same:
- `institutional`
- `vendor`
- `commentary`
- `unknown`

## Verification

### Focused tests
Focused tests passed:
- `tests/unit/v2/test_source_typing.py`
- `tests/unit/v2/test_source_mix_shaping.py`
- `tests/unit/v2/test_source_type_jsonl_roundtrip.py`

Result: `7 passed`

### Live sanity check
Ran representative live checks over:
- remote work reporting
- legal hold steps
- identity / break-glass

Observed result:
- the previous recurring unknowns from `getsix` / `vansurksum` / CLOC-hosted OpenText PDF no longer define the bucket the way they did before
- `unknown` still exists, but it shifted to narrower residual sources such as:
  - Leinonen Group
  - First Legal
  - Altiatech

Interpretation:
- this is a good bounded improvement
- the unknown bucket got narrower and more specific
- the next remaining unknowns now look like another advisory/professional-commercial cluster rather than a wide mixed bag

## Practical verdict

This slice succeeded in shrinking the residual unknown bucket without adding a new taxonomy.
That was the right move.

The next improvement, if continued, should stay disciplined:
- probably another small advisory/commercial marker refinement,
- or a short diagnostic pass to confirm whether the remaining unknowns are coherent enough to justify one more bounded classifier update.

## Recommended next bounded slice

`authority-relevance-source-typing-v4-or-stop-check`

Goal:
- decide whether one more small refinement is still worth it,
- or whether the remaining unknown bucket is already narrow enough that further tuning should stop until a concrete live failure appears
