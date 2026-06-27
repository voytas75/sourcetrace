# SourceTrace v2 bounded quality pass v2 — 2026-06-27

## Scope

Run one short quality pass over the richer v2 eval surface after `selected-evidence policy v2` landed.

Corpus exercised:
- `eval_corpus_v1`
- `eval_corpus_v2`
- focused selected-evidence policy tests
- compiled-readback tests
- provider-backed search adapter tests

## Result

Current bounded quality pass v2 status: **PASS**

Verification run:
- `tests/unit/v2/test_eval_corpus_v2.py`
- `tests/unit/v2/test_eval_corpus_v1.py`
- `tests/unit/v2/test_selected_evidence_policy.py`
- `tests/unit/v2/test_compiled_readback.py`
- `tests/unit/v2/test_unified_search_adapter.py`
- `tests/unit/v2/test_searxng_search_adapter.py`

Observed outcome:
- legacy eval corpus v1 still passes after the policy-v2 update once expectations are aligned with the new bounded policy surface
- eval corpus v2 passes across stub, SearxNG-backed, preferred-search, thin-content, and partial-compiled cases
- selected-evidence policy v2 behaves coherently under both minimal-content and same-domain competition cases
- compiled artifact readback remains stable under both found and incomplete states

## Sharpest finding

The sharpest remaining weakness is now less about contract shape or tiny heuristic gaps and more about **representativeness of topic realism**.

In plain terms:
- the bounded system is coherent,
- the current heuristics are good enough for the synthetic/fixture-level surface we exercise,
- but the next bottleneck is likely corpus realism before more policy sophistication.

## What this pass proves

It proves that the current bounded v2 stack is coherent across:
- retrieval input
- selected-evidence policy v2
- explain/debug surface
- compiled artifact projection
- compiled artifact readback
- stub and provider-backed runtime paths

## What this pass still does not prove

It still does **not** prove:
- realistic topical retrieval quality,
- robust evidence relevance on non-synthetic queries,
- production-grade authority or domain trust judgments,
- benchmark-grade ranking quality.

## Recommended next bounded slice

Prefer:
1. `eval corpus v3` with a few more realistic topical cases, or
2. one small authority/relevance guard only if it is directly motivated by new corpus evidence.

Recommendation: **eval corpus v3 first**.
