# Checkpoint 1 — Phase 1 (A1/A2/A3)

Date: 2026-05-21
Scope: controlled test-use only
Source corpus SSOT: `docs/plans/2026-05-21-real-data-campaign-corpus-v1.md`
Observation notes:
- `docs/plans/2026-05-21-observation-a1-reuters-south-africa-risks.md`
- `docs/plans/2026-05-21-observation-a2-bbc-us-inflation-energy-shock.md`
- `docs/plans/2026-05-21-observation-a3-bbc-us-jobs-april.md`

## Completed documents
- A1 — Reuters South Africa risks
- A2 — BBC US inflation energy shock
- A3 — BBC US jobs April

## Verified stable behavior
- `POST /api/dev/documents` worked for all Phase 1 documents during reruns.
- `POST /api/documents/<doc-id>/prepare` worked for all Phase 1 documents during reruns.
- The A2/A3 live extraction blocker was real, reproducible, and then removed by a bounded adapter fix in `src/sourcetrace/llm/litellm_client.py`.
- After the adapter fix, campaign-shaped A2/A3 reruns both returned `ready` and persisted claims.
- Credibility drafting remained operational across the Phase 1 set, including when extraction had previously failed.

## Post-checkpoint bounded quality follow-ups
- A1 grounding traceability tightening landed in `src/sourcetrace/application/extraction_runtime.py` and improved grounding for uniquely paraphrased claims without broadening matching globally.
- A2 carry-through tightening landed for `however,` sentence tails so core factual claims win over obvious carry-through duplicates.
- A2.2 extended the same bounded carry-through rule to `although` tails.
- A3 normalization source-faithfulness tightening now rejects normalized claim text when it changes percentage values from the extracted source claim.
- Current post-follow-up baseline status: `275 passed` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q`.

## Newly observed failure modes
- `runtime_bootstrap` / severity `high` / repeatability `recurring` / buckets `A`
  - Historical A2/A3 blocker: `LlmSchemaError: structured payload for ClaimExtractionPayload must be a mapping`.
  - Root seam narrowed to structured payload normalization in `llm/litellm_client.py`.
  - Status now: closed for current Phase 1 reruns after bounded alias normalization fix.
- `grounding_traceability` / severity `high` / repeatability `recurring` / buckets `A`
  - A1 still shows weak chunk/span grounding on many claims.
  - Although a bounded grounding fix improved exact/unique matches, many live claims still fall back to weak span references.
- `extraction_quality` / severity `medium` / repeatability `recurring` / buckets `A`
  - A2/A3 now extract successfully, but some claims remain too long, too broad, or too close to sentence carry-through rather than tightly bounded factual claims.
- `normalization_quality` / severity `medium` / repeatability `recurring` / buckets `A`
  - A1/A2/A3 still show paraphrase drift on some claims.
  - The system now has a bounded guard for percentage-value drift, but can still lightly rewrite causal or analytical statements.

## Bucket A preliminary verdict
- Verdict: `usable-with-caveats` for controlled test-use.
- Reasoning:
  - A1/A2/A3 can now run end-to-end.
  - Runtime extraction is no longer blocked for the Phase 1 start set.
  - However, traceability and source-tightness are still too uneven for trusted analytical use.

## Verdict shift
- Previous state during Phase 1:
  - Bucket A was blocked by a live extraction/runtime failure on A2/A3.
- Current state after bounded fix:
  - Runtime blocker is closed.
  - The dominant remaining issues shifted from runtime failure to quality issues: grounding traceability and remaining claim compactness/source-faithfulness gaps.
  - Post-checkpoint bounded follow-ups reduced the failure surface for paraphrased grounding, carry-through duplicates, and percentage drift, but did not remove the broader analytical-use caveat.

## Checkpoint 1 output verdict
- Definition of Done status:
  - 3 observation notes exist: yes
  - each note has pasteable evidence: yes
  - at least one preliminary verdict exists for Bucket A behavior: yes
- Checkpoint 1 status:
  - complete

## Next bounded engineering slice
1. Re-check live grounding traceability on A1-style paraphrased claims after the bounded grounding fix and confirm what still falls back to weak spans.
2. Tighten extraction/normalization so long causal or analytical sentences are less likely to survive as oversized claims when they are not simple carry-through duplicates.

## Next campaign action
- Proceed to Phase 2 (C1, C2) only with the bounded readiness statement unchanged:
  - SourceTrace is acceptable for continued controlled test-use.
  - It is not yet ready for trusted analytical use on real documents.
