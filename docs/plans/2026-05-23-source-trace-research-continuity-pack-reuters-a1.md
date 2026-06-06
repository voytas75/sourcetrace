# SourceTrace Research Continuity Pack — A1 Reuters South Africa risks

Source artifact: `docs/plans/2026-05-21-observation-a1-reuters-south-africa-risks.md`
Related context: `docs/plans/test-use-observation-template.md`, `docs/research/research-ledger.md`
Status: first continuity-pack experiment

## Potwierdzone
- SourceTrace already has a usable observation artifact shape for real-data test runs: session metadata, input shape, extraction outcome, normalization behavior, credibility draft, and outcome classification are all captured in one note.
- On the Reuters A1 run, the system was operationally usable but not trustworthy enough for research-to-decision handoff without caveats.
- The strongest confirmed problem was not only wording drift but evidence grounding collapse:
  - initial run anchored all persisted claims to `chunk-1`
  - most claims had `source_span_reference: chunk-span:unknown`
- A bounded grounding fix improved the seam partially, not fully:
  - at least one live retest claim anchored correctly to `chunk-10` with `source_span_reference: p10`
  - most claims still fell back to `chunk-1`
- The credibility pass was materially useful on this artifact because it surfaced the weakness of the run itself: summary-based seeding, incomplete metadata, and the need to verify Reuters attribution / underlying S&P material.
- This artifact already supports an operator decision better than a raw run log because it separates:
  - extraction quality
  - normalization drift
  - credibility usefulness
  - blocker
  - next fix

## Przypuszczenia
- A standardized continuity-pack wrapper may be the missing bridge between research notes and engineering prioritization, because the raw observation already contains most of the needed evidence but not yet a strict decision-ready summary.
- The highest leverage of the continuity pack is probably not archival value, but faster triage: it makes it easier to answer “is this a model-quality issue, an evidence-link issue, or an ingestion-contract issue?” without rereading the whole note.
- The Reuters A1 artifact suggests SourceTrace quality decisions should be driven by traceability failures before stylistic extraction cleanup; otherwise teams may optimize claim phrasing while the grounding seam is still unreliable.

## Do weryfikacji
- Whether one continuity-pack format is equally useful for:
  - external research review artifacts from `docs/research/research-ledger.md`
  - live runtime observation notes like this Reuters A1 run
  - future wiki-native research artifacts
- Whether continuity packs actually shorten handoff time in practice versus just producing another documentation layer.
- Whether the recommended next test section is sufficient, or the pack also needs an explicit decision field such as:
  - park
  - execute next bounded slice
  - escalate to discovery
- Whether the pack should become a canonical doc type in SourceTrace docs, or stay a lightweight wrapper generated only for decision checkpoints.

## Recommended next test
- Run one bounded continuity-pack comparison on a second artifact with a different failure mode, then compare whether the same `potwierdzone / przypuszczenia / do weryfikacji` structure still helps an operator decide the next slice faster than the raw note.

## Decision snapshot
Keep continuity packs as a lightweight decision wrapper for now; useful enough to continue, not yet proven enough to canonize as a hard SSOT doc type.
