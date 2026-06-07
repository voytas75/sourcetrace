# SourceTrace real-data checkpoint — Bucket A factual briefs

Status: checkpoint after first three controlled factual-brief passes (`A1`, `A2`, `A3`)
Parent SSOT: `docs/plans/2026-05-21-real-data-test-use-ssot.md`
Observation notes:
- `docs/plans/2026-05-23-test-use-observation-a1-reuters-south-africa-risks.md`
- `docs/plans/2026-05-23-test-use-observation-a2-bbc-us-inflation-energy-shock.md`
- `docs/plans/2026-05-23-test-use-observation-a3-bbc-us-jobs-april.md`

## Decision
Bucket A is currently **usable-with-caveats**.

This is good enough to continue campaign testing, but not good enough to call factual-brief extraction "clean" or "analyst-ready" without qualification.

## What is confirmed
- End-to-end runtime flow is stable across all three factual briefs.
- No obvious assistant/helpdesk prose appeared in persisted claims.
- Chunking stayed operationally clean.
- Credibility drafts were consistently useful enough to support analyst follow-up.
- The dominant failure mode was not hallucinated explanation, but claim granularity / context loss.

## Recurring failure mode
The system tends to split compact factual reporting into claims that are too small and sometimes too context-thin.

Observed symptoms:
- expectation-vs-outcome framing gets separated into weaker fragments
- market-reaction paragraphs get atomized into micro-claims
- some claims become semantically true but less useful as standalone analyst artifacts
- source span anchoring is inconsistent (`pN` in cleaner cases like `A2`, but `chunk-span:unknown` reappears in `A1` and `A3`)

## Strongest signal from the bucket
The factual-brief path appears stylistically healthier than feared.

If there is a major product risk here, it is **not** assistant-style drift. It is **over-splitting and unstable evidence anchoring**.

## Main gap
The product still needs tighter grouping/anchoring for short factual and numeric paragraphs.

Without that, outputs are reviewable, but they remain noisier and less decision-ready than they should be.

## Recommended next product slice
Tighten extraction / post-processing for short factual briefs so that:
1. tightly related numeric facts can remain grouped when the source presents them as one unit,
2. expectation/outcome/context fragments are not split into thin standalone claims,
3. `source_span_reference` falls back to paragraph-level references (`pN`) more consistently instead of `chunk-span:unknown`.

## Campaign decision
Proceed to Bucket B.

Reason:
- Bucket A already produced a consistent enough pattern.
- The bigger unknown is whether longer analytical articles reintroduce a more serious drift mode than the one seen in factual briefs.

## Recommended next execution step
Run `B1` next:
- `campaign-b1-ap-trump-tax-cuts-inflation`
- expectation: check whether the system starts expanding, reframing, or over-explaining once argumentation and mixed perspectives get longer.
