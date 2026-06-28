# SourceTrace v2 official-guidance-source-typing-v1 — 2026-06-28

## Goal

Apply the smallest coherent retrieval-side fix for the remaining official-intent weakness after query-refinement improvements:
- keep the coarse public `source_type` contract stable,
- but stop publication-like institutional surfaces from competing too strongly with real official guidance inside already-official candidate pools.

## What changed

Updated:
- `src/sourcetrace_v2/execution/stages/retrieval.py`
- `tests/unit/v2/test_source_mix_shaping.py`
- `tests/unit/v2/test_retrieval_target_quality.py`

Behavior:
- retrieval still labels candidates with the same coarse public types: `institutional`, `vendor`, `commentary`, `unknown`
- official-intent source-mix shaping now applies a small internal penalty to institutional candidates that look publication-like
- the penalty is based on source-surface signals only, such as:
  - PMC / PubMed hosts
  - publication-style markers like `doi`, `abstract`, `journal`, `issn`
  - the known CEJSH-like publication surface marker seen in the live weak case

## What stayed unchanged

Deliberately unchanged:
- query-refinement contract
- retrieval window size
- selector policy
- trust policy
- public API/readback `source_type` shape

This slice only changes how already-typed official-intent retrieval candidates are reordered before the bounded trim.

## Why this shape

The post-query-refinement live eval showed a narrower failure mode than earlier retrieval drift:
- official/public guidance was already entering the candidate pool,
- but publication-like institutional surfaces could still outrank it because the coarse `institutional` label was too generous.

The fix therefore stays at the source-typing/shaping seam instead of widening back out into query heuristics or selector/trust changes.

## Validation

Focused tests:
- `./.venv/bin/pytest -q tests/unit/v2/test_source_mix_shaping.py tests/unit/v2/test_retrieval_target_quality.py tests/unit/v2/test_source_typing.py tests/unit/v2/test_institutional_retrieval_window.py tests/unit/v2/test_quality_regression_pack_v4.py`
- result: `15 passed`

Broader v2 suite:
- `./.venv/bin/pytest -q tests/unit/v2`
- result: `100 passed`

Live reruns:
- `cross-border data transfer official guidance`
  - top retrieval candidate moved to `International data transfers | Data protection guide for small business`
  - selected pair became EDPB + ICO guidance instead of a PMC article leading the pool
- `remote work reporting obligations Poland employer official guidance`
  - top retrieval candidate moved to `The rights and obligations of employers | Biznes.gov.pl`
  - the earlier CEJSH publication-like PDF no longer leads the pool
  - this case still remains weak on exact-subject fit, so it should not be treated as solved

## Practical outcome

This slice does what it was supposed to do:
- official/regulator/service guidance now survives more cleanly against institutional-academic/publication-like surfaces in official-intent retrieval
- legal-hold and tax-guidance gains remain covered by the existing regression pack
- the remaining unresolved weakness is narrower and more honest: exact-subject survival within an already-more-official pool, not generic source drift
