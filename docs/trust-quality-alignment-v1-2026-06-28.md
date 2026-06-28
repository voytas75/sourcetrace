# SourceTrace v2 trust-quality-alignment v1 — 2026-06-28

## Goal

Move the operator-facing trust signal a bit closer to real evidence quality after the recent retrieval improvements, without inventing fake confidence math or changing retrieval/selector policy.

## Change made

Updated:
- `src/sourcetrace_v2/projections/api/trust.py`

What changed:
- trust evaluation now looks at the currently selected shape through the compiled selected-evidence view instead of only basic counts
- `low_confidence_selected_shape` is now added when:
  - selected evidence has no strong authority bands, or
  - the selected pair contains no institutional source and is made only of `unknown` / `commentary` / `vendor` surfaces
- the previous bounded checks remain in place:
  - incomplete persistence
  - stage failure
  - degraded LLM calls
  - thin candidate/selection surface

## Verification

### Focused tests
Passed:
- `tests/unit/v2/test_trust_quality_alignment.py`
- `tests/unit/v2/test_operator_trust_contract.py`
- `tests/unit/v2/test_api_readback_projection.py`
- `tests/unit/v2/test_quality_regression_pack_v1.py`
- `tests/unit/v2/test_quality_regression_pack_v2.py`

Result: `10 passed`

### Broader v2 check
Passed:
- `tests/unit/v2`

Result: `94 passed`

### Live sanity check
Checked:
- break-glass
- remote-work Poland
- tax guidance
- cross-border data transfer

Observed:
- weak institutional+advisory or degraded cases surface as `weak` more consistently when degradation is present
- obviously non-institutional selected pairs are now more likely to avoid optimistic `usable` labeling
- trust is still intentionally shallow: jurisdiction-mixed institutional cases like tax guidance can still surface as `usable`

## Practical verdict

This is a real honesty improvement, but not a final trust model.

What improved:
- trust is less count-only and slightly more aware of selected-evidence quality
- the operator signal is better aligned with obviously weak selected shapes\n
What remains intentionally unresolved:
- jurisdiction mismatch is not yet encoded as a trust concern
- mixed institutional-but-possibly-wrong-jurisdiction shapes can still look usable
- this slice does not try to infer deep semantic correctness from thin signals

## Recommended next bounded slice

`quality-regression-pack-v3`

Goal:
- expand the shared regression baseline again after the latest retrieval and trust changes, especially around cases that are improved but still not fully satisfactory (for example break-glass companion quality and jurisdiction-mixed tax guidance)
