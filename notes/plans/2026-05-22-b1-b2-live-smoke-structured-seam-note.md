# B1/B2 live smoke note — structured extraction seam stability

Date: 2026-05-22
Repo: `/home/voytas/projects/sourcetrace`
Runtime: `.venv/bin/sourcetrace-www-start`
Endpoint: `http://127.0.0.1:8000`

## Purpose
Record whether the structured-output seam fix that unblocked A1/A2/C1 also holds on longer B-shape live inputs.

## Inputs used
These were bounded live smoke inputs shaped after the frozen campaign corpus B bucket, not full raw article bodies.

### B1
- Case ID: `campaign-b1-live-smoke-20260522`
- Document ID: `doc-b1-live-smoke-20260522`
- Source URL: `https://apnews.com/article/trump-north-carolina-senate-big-beautiful-bill-09c3d170f57f56c74a7e4e35d6cf2dee`
- Shape: longer analytical political-economy article with multiple viewpoints and caveats

### B2
- Case ID: `campaign-b2-live-smoke-20260522`
- Document ID: `doc-b2-live-smoke-20260522`
- Source URL: `https://www.bbc.com/news/articles/czejp3gep63o`
- Shape: longer explanatory macro article with causal links and sector variation

## Confirmed live results
### B1
- `prepare_chunk_count`: `3`
- `extract_claim_count`: `10`
- `case_claim_count`: `10`
- `unknown_count`: `0`
- Chunk distribution:
  - `chunk-2`: `7`
  - `chunk-3`: `3`
- Sample anchors:
  - `claim-1` → `chunk-2 / p2`
  - `claim-8` → `chunk-3 / p3`

### B2
- `prepare_chunk_count`: `3`
- `extract_claim_count`: `10`
- `case_claim_count`: `10`
- `unknown_count`: `0`
- Chunk distribution:
  - `chunk-2`: `8`
  - `chunk-3`: `2`
- Sample anchors:
  - `claim-1` → `chunk-2 / p2`
  - later claims also anchored into `chunk-3 / p3`

## Operational verdict
- The structured-output seam fix is no longer supported only by short factual A-shape inputs.
- It also holds on bounded longer B-shape live smoke inputs.
- No `500 internal_server_error` was observed on these reruns.
- No `chunk-span:unknown` fallback appeared on these reruns.
- The live system returned persisted claims with concrete `chunk_id` and `source_span_reference` values.

## Interpretation
This does **not** prove every future real article will avoid provider-output drift.
It does justify changing the current blocker classification from:
- runtime/seam blocker

to:
- quality/traceability tuning and broader campaign verification.

## Suggested next slice
Return to bounded quality work:
- claim compactness on longer analytical inputs,
- caveat/attribution preservation,
- grounding quality on full real campaign documents rather than only bounded smoke excerpts.
