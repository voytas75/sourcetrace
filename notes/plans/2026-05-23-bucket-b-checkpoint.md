# SourceTrace real-data checkpoint — Bucket B longer analytical articles

Status: checkpoint after two controlled longer-article passes (`B1`, `B2`)
Parent SSOT: `docs/plans/2026-05-21-real-data-test-use-ssot.md`
Observation notes:
- `docs/plans/2026-05-23-test-use-observation-b1-ap-trump-tax-cuts-inflation.md`
- `docs/plans/2026-05-23-test-use-observation-b2-bbc-global-economy-tariffs-2026.md`

## Decision
Bucket B is currently **unstable, but not uniformly broken**.

This is weaker than Bucket A. It is not yet strong enough for trusted analyst-facing extraction on longer analytical material, but it is strong enough to continue campaign probing and isolate the real failure mode more precisely.

## What is confirmed
- The dominant long-form risk is **not** chatty assistant/helpdesk prose.
- The dominant long-form risk is **attribution/context thinning**:
  - analytical passages get flattened into proposition-style claims,
  - speaker/source framing gets dropped,
  - mixed-perspective passages lose who-says-what structure,
  - some numeric claims fall back to `chunk-span:unknown`.
- B1 showed the worse version of the problem:
  - `engineering-smoke-only`
  - strong flattening of analytical framing and voter-example context.
- B2 showed a cleaner version of the same family of problem:
  - `usable-with-caveats`
  - less noisy than B1, but still too willing to compress attributed statements into bare propositions.
- Credibility notes remain healthier than extraction in this bucket.

## Recurring failure mode
When the input contains longer analysis, attribution, expert views, and multi-step explanatory framing, the system often preserves the broad topic but weakens the evidence-ready artifact.

Observed symptoms:
- `IMF says ...` becomes a bare proposition
- expert attributions become detached from claims
- article-level synthesis becomes generic proposition lists
- some claims become linguistically compressed in awkward ways
- key numeric statements can still lose precise span anchoring

## What changed from Bucket A
Bucket A's dominant issue was over-splitting of short factual paragraphs.

Bucket B adds a different and more serious issue:
- **traceability loss in analytical framing**

This matters more than simple granularity because it weakens:
- reviewer confidence,
- provenance clarity,
- and downstream usefulness for decision-ready analysis.

## Operational signal
One live long-form pass (`B2`) hit a runtime timeout after `prepare` during the first all-in-one attempt.

Observed facts:
- `prepare` succeeded,
- subsequent request flow stalled,
- `/api/health` also stopped responding during the stall,
- restart + stepwise retry with longer timeouts recovered the flow.

Interpretation:
- this is a **real operator signal**,
- but still **do weryfikacji** as a product/runtime bug until reproduced more cleanly.

## Main gap
The product does not yet preserve attribution structure reliably enough for longer analytical articles.

Without that, even factually plausible outputs become weaker analyst artifacts because the operator has to reconstruct too much of the original framing by hand.

## Recommended next product slice
Preserve attribution in extraction from long analytical passages, especially for:
1. institutional forecasts (`IMF says ...`),
2. named expert judgments,
3. article synthesis that contrasts multiple perspectives,
4. quote/explanation passages where the current output strips away who is speaking.

A secondary engineering check should verify whether long-form extraction can intermittently stall the local runtime after `prepare`.

## Campaign decision
Proceed to `B3`.

Reason:
- Bucket B already shows a stable-enough pattern to justify one more confirming pass.
- `B3` should tell us whether the bucket is mostly "attribution thinning but usable" or whether there is a broader long-form instability across regional/economic analysis.

## Recommended next execution step
Run `B3` next:
- `campaign-b3-bbc-gulf-economies-iran-conflict`
- expectation: check whether regional multi-sector analysis stays traceable or collapses into generalized proposition fragments.
