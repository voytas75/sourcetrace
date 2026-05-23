# SourceTrace real-data checkpoint — Bucket C quotes / caveats / mixed certainty

Status: checkpoint after two controlled mixed-certainty passes (`C1`, `C2`)
Parent SSOT: `docs/plans/2026-05-21-real-data-test-use-ssot.md`
Observation notes:
- `docs/plans/2026-05-23-test-use-observation-c1-bbc-uk-growth-risks.md`
- `docs/plans/2026-05-23-test-use-observation-c2-bbc-uk-inflation-expected-rise.md`

## Decision
Bucket C is currently **usable-with-caveats**.

It is not failing in a qualitatively new way. Instead, it reinforces the main product weakness already seen in Buckets B and partly A: the system preserves proposition content better than it preserves provenance.

## What is confirmed
- The system can preserve some caveat and uncertainty language in a useful form.
- C1 was the cleaner pass:
  - explicit uncertainty language survived well,
  - review burden remained manageable,
  - output stayed concise and non-chatty.
- C2 was slightly weaker:
  - attribution flattening was more visible,
  - some extracted claims became clipped or lowercased fragments,
  - multiple forecast/expert statements lost speaker identity.
- Across both passes, the system remained operationally stable:
  - no runtime stall,
  - no dropped claim items,
  - no assistant/helpdesk prose drift.

## Recurring failure mode
The model often preserves the warning, forecast, or caveat itself, but drops the source ownership that makes the statement decision-ready.

Observed symptoms:
- `IMF said ...` becomes a bare proposition
- `Luc Eyraud said ...` becomes a generic institutional statement
- `economists broadly expect ...` survives as unattributed expectation language
- named expert statements become free-floating forecast text
- some claims degrade into partial sentence fragments

## What changed from Bucket B
Bucket B's dominant issue was analytical traceability loss in longer articles.

Bucket C keeps the same family of issue, but in a narrower and more diagnosable form:
- **quote / forecast / caveat attribution loss**

This is slightly healthier than Bucket B because uncertainty language itself often survives. But the missing `who says this` marker still weakens analyst confidence and downstream verification.

## Main gap
The product still does not reliably preserve explicit attribution labels for:
- institutional judgments,
- named experts,
- article-level caveat framing,
- forecast statements,
- conditional policy interpretations.

In C2, there was also a secondary readability problem:
- some outputs were clipped, lowercased, or sentence-fragment-like.

## Recommended next product slice
Improve extraction for attributed forecast / caveat statements:
1. preserve `X said`, `according to`, `article notes`, and similar provenance markers,
2. avoid clipping sentence heads on extracted claims,
3. keep forecast/expectation statements explicitly tied to their speaker class (`economists`, named analyst, institution, article framing).

## Campaign decision
Proceed to Bucket D.

Reason:
- Buckets A, B, and C already show a stable cross-bucket pattern.
- The next useful discriminator is not another attribution-heavy article, but a weaker/noisier source where credibility caution behavior should matter more.

## Recommended next execution step
Run `D1` next:
- `campaign-d1-ap-einpresswire-war-market-trends`
- expectation: check whether the system becomes appropriately cautious on a weak/promotional source, or whether it still extracts broad claims too confidently.
