# SourceTrace v2 institutional evidence precision v1 — 2026-06-28

## Goal

Improve cases where institutional sources are present but their authority signal is still too weak relative to broader/off-topic or community/practical competitors.

This slice stays bounded.
It does not change the overall selector contract or broaden taxonomy.

## Diagnosis behind the change

Live checks showed a recurring precision weakness:
- institutional candidates could be present,
- but their authority banding was still too soft,
- while community/practical candidates with strong title/path specificity could compete too well.

This was especially visible in identity/break-glass style queries.

## Change made

Refined authority scoring in `src/sourcetrace_v2/core/policies/selected_evidence.py`.

What changed:
- `source_type="institutional"` now explicitly contributes to authority scoring
- `source_type="vendor"` contributes a smaller bounded authority bump
- `source_type="commentary"` is treated more skeptically in authority scoring
- unknown community/forum-like surfaces (for example reddit/forum host tokens) get a bounded authority demotion

This is still a bounded judgment refinement, not a new selector policy.

## Verification

### Focused tests
Focused tests passed:
- `tests/unit/v2/test_institutional_evidence_precision.py`
- `tests/unit/v2/test_selected_evidence_policy.py`
- `tests/unit/v2/test_source_typing.py`

Result: `6 passed`

### Live check
Ran a live sanity check on:
- `break glass account guidance conditional access official best practice`

Observed selected pair:
- `Manage emergency access admin accounts - Microsoft Entra ID`
- `Break Glass Accounts in Entra ID: Emergency Access Done Right | Altiatech`

Observed authority bands:
- institutional Microsoft Learn source: `high`
- second source: `none`

Interpretation:
- the official institutional source now stands out much more clearly in the judgment surface
- the remaining non-institutional companion is still present, but it is no longer competing on misleadingly similar authority footing

## Practical verdict

This is a good bounded quality-pack slice.
It improves precision inside the institutional evidence track without changing the broader selector contract.

It does not solve every retrieval/source-mix problem, but it makes the judgment surface more honest where institutional sources are already present.

## Recommended next bounded slice

`institutional-evidence-precision-live-pack-v1`

Goal:
- run a small multi-query live pack over institutional-intent cases and confirm whether the updated authority surface produces consistently better selected-evidence shapes before any further tuning
