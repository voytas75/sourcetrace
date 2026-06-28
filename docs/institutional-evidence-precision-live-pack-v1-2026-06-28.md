# SourceTrace v2 institutional evidence precision live pack v1 — 2026-06-28

## Goal

Validate whether `institutional-evidence-precision-v1` improves the selected-evidence shape consistently across a small institutional-intent live pack before any further tuning.

## Live pack

Queries checked:
- break glass account guidance conditional access official best practice
- data breach notification checklist authority official guidance
- legal hold steps records retention official guidance
- remote work reporting obligations Poland employer official guidance

## Result

### 1. Break glass
Selected shape:
- Microsoft Entra / Microsoft Learn — `institutional`, `authority=high`
- companion practical/vendor source — `vendor`, `authority=none`

Verdict:
- good outcome
- the official institutional source clearly stands out now
- the companion source still contributes practical specificity without pretending to equal authority

### 2. Breach notification
Selected shape:
- FTC — `institutional`, `authority=high`
- ICO — `institutional`, `authority=high`

Verdict:
- strong outcome
- this remains the cleanest institutional-intent case
- the updated authority surface is behaving as intended

### 3. Legal hold
Selected shape:
- OpenText practical PDF — `vendor`
- Venio guide — `vendor`

Verdict:
- unchanged core weakness
- this is still mostly an upstream candidate-pool / source-mix problem, not an institutional-authority scoring problem
- there is no strong institutional candidate here for the new authority surface to rescue

### 4. Remote work reporting
Selected shape:
- `easyeor.pl` advisory/commercial page — `unknown`, `authority=low`
- BPCC commentary page — `commentary`, `authority=none`

Verdict:
- still weak
- this is not primarily a judgment-surface problem anymore
- the deeper issue is that the candidate pool still lacks strong public-institutional Poland-specific evidence

## Overall verdict

`institutional-evidence-precision-v1` is a **real improvement**, but not a universal fix.

What it clearly helped:
- cases where a real institutional candidate is already in the pool
- especially break-glass and breach-notification style queries

What it did not fix:
- cases where retrieval still fails to surface strong institutional candidates at all
- especially legal-hold and remote-work reporting

## Decision

Do **not** keep tuning institutional authority scoring right now.
That seam is good enough for the moment.

The next sharp problem is upstream again:
- candidate-pool composition
- institutional retrieval coverage
- official-intent query shaping for difficult domains / jurisdictions

## Recommended next bounded slice

`institutional-retrieval-gap-diagnostics-v1`

Goal:
- inspect why official/public-institutional candidates are still missing or weak in the remaining hard cases,
- especially for Poland remote-work reporting and legal-hold / records-retention style queries,
- before changing retrieval or selection behavior again
