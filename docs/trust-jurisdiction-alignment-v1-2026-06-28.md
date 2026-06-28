# SourceTrace v2 trust-jurisdiction-alignment v1 — 2026-06-28

## Goal

Tighten the operator-facing trust signal for selected evidence pairs that look respectable at first glance, but are still subtly unsafe because they mix institutional authorities from different jurisdictions.

This stays bounded:
- no retrieval/query shaping changes
- no selector policy changes
- no country-specific or query-specific heuristics
- no fake semantic confidence model

## Change made

Updated:
- `src/sourcetrace_v2/projections/api/trust.py`

What changed:
- trust projection now adds `jurisdiction_mixed_selected_institutional_pair` when:
  - both selected evidence items are `institutional`, and
  - their lightweight institutional anchors do not match
- anchor comparison is deliberately shallow and generic:
  - based on stable institutional identity cues from host/title
  - intended to catch obviously mixed authority pairs such as different government/revenue authorities
- this affects only trust projection
  - the selected pair remains visible as-is
  - retrieval and selection behavior stay unchanged

## Why this slice is coherent

The previous trust-quality slice fixed obvious low-authority or non-institutional optimism.
What remained was subtler:
- institutional/institutional pairs could still look `usable`
- but some of them were not actually production-clean because the authorities were from different jurisdictions or governing bodies

This slice addresses that exact gap without widening into deeper semantic or jurisdiction inference.

## Verification

Focused tests passed:
- `tests/unit/v2/test_trust_quality_alignment.py`
- `tests/unit/v2/test_quality_regression_pack_v3.py`
- `tests/unit/v2/test_operator_trust_contract.py`
\nBroader check:
- `tests/unit/v2`

## Practical verdict

This is a real honesty improvement, not a retrieval fix.

What improved:
- tax-guidance-like mixed institutional pairs no longer project as production-clean `usable`
- operator trust is now better aligned with an important subtle failure mode

What remains intentionally unresolved:
- this is still a lightweight structural signal, not deep jurisdiction understanding
- it does not infer the correct jurisdiction from user intent
- it does not change selected evidence itself

## Recommended next bounded slice

Re-run the updated readiness/trust posture review and decide whether the next sharp gap is still in trust semantics or has moved back upstream into retrieval quality for the remaining weak cases.
