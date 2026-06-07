# SourceTrace real-data campaign synthesis — buckets A-D

Status: final synthesis for the first controlled 10-document real-data campaign
Parent SSOT: `docs/plans/2026-05-21-real-data-test-use-ssot.md`
Corpus ledger: `docs/plans/2026-05-21-real-data-campaign-corpus-v1.md`
Runbook: `docs/plans/2026-05-23-real-data-campaign-runbook-v1.md`
Bucket checkpoints:
- `docs/plans/2026-05-23-bucket-a-checkpoint.md`
- `docs/plans/2026-05-23-bucket-b-checkpoint.md`
- `docs/plans/2026-05-23-bucket-c-checkpoint.md`
- `docs/plans/2026-05-23-bucket-d-checkpoint.md`

## Final decision
The first campaign shows that SourceTrace is currently **usable-with-caveats**, not yet analyst-ready by default.

The system is healthier than a "chatty summarizer" failure mode would suggest. Its main weakness is different: it tends to preserve proposition content better than provenance, source posture, and decision-ready usefulness.

## Bucket verdicts
- **Bucket A — factual briefs:** `usable-with-caveats`
  - strongest signal: over-splitting + unstable anchoring on short factual paragraphs
- **Bucket B — longer analytical articles:** `usable-with-caveats`, but weakest bucket overall
  - strongest signal: analytical traceability loss and attribution/context thinning
- **Bucket C — quotes / caveats / mixed certainty:** `usable-with-caveats`
  - strongest signal: forecast/caveat content often survives, but speaker ownership is weakened
- **Bucket D — weak / noisy sources:** `usable-with-caveats`
  - strongest signal: extraction does not adapt enough to weak/promotional sources or low-yield caption-like input

## What is confirmed across the campaign
- End-to-end runtime flow is generally stable and usable for controlled passes.
- Persisted claims are usually concise and not polluted by assistant/helpdesk prose.
- Credibility drafts are often healthier than extraction and frequently point to the right review task.
- The system is usually better at preserving broad propositional meaning than source traceability.
- `chunk-span:unknown` remains a repeated signal of weak anchoring across multiple buckets.

## Ranked repeated failure modes
### 1. Provenance / attribution thinning (highest-confidence repeated pattern)
Observed across Buckets B and C, and partly visible in A.

Symptoms:
- `X said ...` becomes a bare proposition
- named experts or institutions lose ownership of the statement
- article-level synthesis turns into generic claim lists
- caveats survive but not the speaker/source label that makes them decision-ready

Why this matters:
- lowers reviewer confidence,
- weakens verification,
- makes downstream analysis more manual,
- is more serious than simple formatting noise.

### 2. Over-splitting and context loss on compact factual reporting
Observed most clearly in Bucket A.

Symptoms:
- expectation-vs-outcome framing gets split into smaller weaker fragments
- tightly related numeric/contextual facts get atomized
- claims remain plausible, but become thinner and noisier than needed

Why this matters:
- hurts briefing quality even when factual drift is low,
- turns healthy factual paragraphs into weaker review artifacts.

### 3. Source-posture-unaware extraction
Observed most clearly in Bucket D1.

Symptoms:
- sponsored/promotional theses are extracted too eagerly
- extraction does not sufficiently react to low-credibility source posture
- operator gets the real caution only when reading the credibility layer

Why this matters:
- overstates practical usefulness of low-quality sources,
- separates extraction from credibility too sharply.

### 4. Low-yield input recognition gap
Observed most clearly in Bucket D2.

Symptoms:
- repeated caption-like material is handled safely,
- but the result is a handful of trivial observational claims,
- no strong collapse into one low-yield summary or explicit low-value marker.

Why this matters:
- wastes operator attention,
- produces syntactically valid but strategically weak output.

### 5. Anchoring instability
Observed across A, B, C, and D.

Symptoms:
- many otherwise usable claims still fall back to `chunk-span:unknown`
- weaker evidence anchoring often co-occurs with low usefulness or attribution loss

Why this matters:
- weakens auditability and reviewer trust,
- makes follow-up slower than it should be.

## Important non-findings
These risks were **not** the dominant pattern in this campaign:
- no broad assistant/helpdesk prose drift,
- no generalized hallucination meltdown,
- no systematic runtime failure,
- no evidence that all long-form content is broken.

This matters because it narrows the engineering target: the next slice should improve evidence-ready extraction quality, not fight the wrong enemy.

## Do weryfikacji
### Runtime stall on one long-form pass
A single `B2` all-in-one pass stalled after `prepare`, and `/api/health` also stopped responding until restart.

Status:
- **confirmed as an operator event**
- **not yet confirmed as a reproducible product/runtime bug**

Interpretation:
- keep it parked as a verification target,
- do not let it distort the main diagnosis, which is primarily extraction/usefulness quality.

## Smallest defensible next engineering slice
Build one bounded extraction-quality slice focused on **evidence-ready usefulness controls**.

### Slice goal
Make extraction more trustworthy for analyst review without redesigning the whole pipeline.

### Scope
1. **Preserve provenance markers**
   - keep `X said`, `according to`, institutional/source labels, and article framing attached to extracted claims.
2. **Reduce thin over-splitting**
   - keep tightly related factual units together when the source presents them as one unit.
3. **Propagate weak-source posture into extraction/review surfaces**
   - visibly mark or downgrade sponsored/promotional theses earlier.
4. **Handle low-yield repeated captions more explicitly**
   - collapse repeated caption galleries into one compact observation summary or mark them as low-value for claim extraction.
5. **Improve anchoring fallback**
   - prefer paragraph-level anchors (`pN`) over `chunk-span:unknown` when exact spans are not preserved.

### Why this slice, not something broader
Because it addresses the dominant confirmed pattern from all four buckets with one coherent seam:
- extraction currently preserves claims better than it preserves evidence-ready structure.

## Campaign closeout verdict
The campaign is strong enough to justify product follow-up.

Not because the system failed catastrophically, but because the evidence is now consistent:
- SourceTrace already produces reviewable material,
- but it still underperforms where analyst trust depends on provenance, source posture, and compactness of evidence-ready claims.

## Recommended next execution step
Start one bounded engineering slice for extraction usefulness controls, then rerun a minimal regression set:
- one factual brief (`A2` or `A3`),
- one analytical attribution case (`B3` or `C1`),
- one weak/noisy source (`D1` or `D2`).
