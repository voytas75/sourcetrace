# SourceTrace real-data checkpoint — Bucket D weak / noisy sources

Status: checkpoint after two controlled weak/noisy-source passes (`D1`, `D2`)
Parent SSOT: `docs/plans/2026-05-21-real-data-test-use-ssot.md`
Observation notes:
- `docs/plans/2026-05-23-test-use-observation-d1-ap-einpresswire-war-market-trends.md`
- `docs/plans/2026-05-23-test-use-observation-d2-ap-photo-gallery-romania-hat-walk.md`

## Decision
Bucket D is currently **usable-with-caveats**.

This bucket did not expose a single uniform failure. Instead, it cleanly separated two different product behaviors:
- extraction on weak/promotional input remains too proposition-friendly,
- extraction on repetitive low-yield input stays mechanically stable but produces low-value output.

## What is confirmed
- D1 (paid promotional content) showed a strong split between extraction and credibility:
  - extraction still emitted many broad thesis-like claims,
  - credibility correctly identified the source as sponsored, low-reliability, and not AP editorial reporting.
- D2 (AP photo gallery) showed a healthier split:
  - extraction did not over-generate or hallucinate narrative structure,
  - credibility stayed proportionate and correctly treated the gallery as near-primary but context-limited.
- Across both passes:
  - runtime stayed stable,
  - no assistant/helpdesk prose appeared,
  - the system remained readable and operational.

## Recurring failure modes
Bucket D exposed two distinct weaknesses.

### 1. Weak-source posture does not propagate strongly enough into extraction
Observed in `D1`:
- sponsored/promotional theses were preserved as ordinary claims,
- extraction did not visibly down-rank or mark them as weak artifacts,
- the operator would overestimate usefulness if they read extraction without credibility.

### 2. Low-yield input is handled safely, but not especially usefully
Observed in `D2`:
- repeated photo captions compressed into a few trivial observations,
- output remained semantically valid,
- but downstream usefulness was low,
- anchoring still fell back often to `chunk-span:unknown`.

## What changed from Buckets A-C
Buckets A-C mainly exposed traceability problems around:
- attribution,
- provenance,
- caveat ownership,
- analytical framing.

Bucket D adds a new axis:
- **source-posture-aware usefulness**

That means the system is not only weaker at preserving provenance; it also lacks a strong enough mechanism for adapting claim extraction to weak or low-yield source shapes.

## Main gap
The product still lacks two kinds of adaptive behavior:
1. **source-quality-aware extraction**
   - weak/promotional input should be marked, filtered, or downgraded earlier.
2. **low-yield-shape detection**
   - repeated caption galleries should collapse into one compact observation summary or be flagged as low-value for claim extraction.

## Recommended next product slice
Use the completed campaign evidence to define one bounded engineering slice focused on extraction usefulness controls:
1. preserve provenance better for attributed/analytical claims,
2. propagate weak-source posture into extraction/review surfaces,
3. add heuristics for repeated low-yield caption input.

## Campaign decision
Proceed to final campaign synthesis.

Reason:
- all four buckets now have evidence-backed checkpoints or observation notes,
- the campaign already reveals repeated cross-bucket patterns,
- the highest-value next step is no longer another corpus pass, but a compact synthesis that names the dominant seams and recommends the next bounded engineering slice.

## Recommended next execution step
Create a final campaign synthesis covering Buckets A-D:
- aggregate verdicts,
- rank repeated failure modes,
- separate confirmed patterns from do-weryfikacji signals,
- choose the smallest defensible engineering slice for follow-up.
