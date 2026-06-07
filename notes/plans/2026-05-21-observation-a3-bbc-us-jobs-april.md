# Observation note — A3 BBC US jobs April

Based on template: `docs/plans/test-use-observation-template.md`
Campaign corpus source: `docs/plans/2026-05-21-real-data-campaign-corpus-v1.md`

## Session metadata
- Date: 2026-05-21
- Tester: Wojciech Napierała / Hermes-assisted
- Runtime entrypoint: `python -m sourcetrace.local_launcher`
- Repo commit: `cbd29e6`
- Notes scope: Phase 1 start-set pass for A3 on local launcher runtime

## Article / document
- Case ID: `campaign-a3-bbc-us-jobs-april`
- Document ID: `doc-a3-bbc-us-jobs-april`
- Source URL: `https://www.bbc.com/news/articles/cx21664lp32o`
- Publisher: `BBC`
- Title: `US jobs data beats expectations for second month in a row`
- Published at: `2026-05-08`
- Retrieved at: `2026-05-21T12:27:35+02:00`
- Language: `en`

## Input shape
- Article type:
  - factual brief
- Raw text length:
  - approximately 2714 chars in the runtime-tested inline excerpt
- Number of prepared chunks:
  - 19
- Chunking method:
  - paragraph-v1
- Chunk notes:
  - document metadata persisted correctly through `/api/dev/documents`
  - chunking was clean and granular across factual paragraphs and quotes
  - this run used an inline excerpt derived from the BBC article rather than the full live page

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
  - initial run: `500 internal server error`
  - rerun before adapter fix: `500 internal server error`
  - rerun after bounded adapter fix: `ready`
- Claim count:
  - 16 persisted claims on the post-fix rerun with the fuller multi-paragraph excerpt
- `diagnostics.dropped_claim_items`:
  - 0 on the post-fix rerun
- `diagnostics.dropped_evidence_items`:
  - 0 on the post-fix rerun
- Were final persisted claims concise and claim-like?
  - mixed
- Did assistant/helpdesk prose appear?
  - no obvious assistant/helpdesk prose in persisted claims on the post-fix rerun
- Example good claim:
  - `The US economy created 115,000 jobs in April.`
- Example bad claim:
  - `April’s strong employment report reinforced expectations that the Federal Reserve will leave interest rates unchanged as it continues trying to contain inflation.`
- Notes on extraction quality:
  - the original runtime blocker was real here too: extraction previously failed on this campaign-shaped input with the same mapping error path
  - after the bounded adapter fix in `llm/litellm_client.py`, the same A3 campaign-shaped input now extracts successfully end-to-end
  - persisted claims are now available for quality review, so A3 can contribute to the Phase 1 verdict
  - quality remains mixed: several compact numeric claims are useful, but some normalized claims paraphrase source wording and read more like compact summaries than strict extraction

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mixed
- Did normalization appear to expand into summaries/explanations?
  - slightly
- Did normalization appear to inject assistant wording?
  - no obvious assistant wording on the post-fix rerun
- Notes on normalization behavior:
  - the post-fix rerun made normalization observable again
  - several claims remained traceable and tight, but some outputs compressed or rephrased full source sentences instead of staying maximally source-faithful

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `ready`
- Was the credibility note useful?
  - useful
- Main credibility note takeaway:
  - the note correctly recognized a short secondary report with a concrete numeric claim but limited visible sourcing and weak attribution for the broader causal framing
- Notes on credibility quality:
  - strengths were concrete: mainstream publisher, specific jobs figure, publication date, likely official economic release behind the story
  - concerns were also concrete: brief excerpt, missing visible primary attribution, unattributed war-fallout framing, insufficient detail to confirm nuance
  - credibility again remained operational even while extraction failed

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - no
- Notes on verification/review usefulness:
  - run covered document bootstrap, prepare, failed extract, and credibility
  - verification and analyst review remain untested in this note

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - runtime extraction blocker is closed, but normalization/extraction still produce some paraphrased or over-broad claims
- Highest-value next fix:
  - tighten source-faithful claim extraction so analytical or forecast-style sentences are not lightly rewritten into summary claims
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `The US economy created 115,000 jobs in April.`
  - `The data, published by the US Bureau of Labor Statistics (BLS), also showed the unemployment rate was unchanged at 4.3%.`
  - `Revisions to March and February's figures mean the number of jobs rose on average by 48,000 over the last three months.`
- Diagnostics snapshot:
  - initial prepare: `Prepared 19 chunk(s).`
  - rerun before fix prepare: `Prepared 16 chunk(s).`
  - rerun after fix prepare: `Prepared 15 chunk(s).`
  - extract HTTP response (initial): `500 Internal Server Error`
  - extract HTTP response (rerun before fix): `500 Internal Server Error`
  - extract response after fix: `Extracted 16 claim(s) from 15 chunk(s).`
- Credibility note excerpt:
  - `BBC news report excerpt summarizing April US jobs figures and attributing them to broader economic conditions, but the provided text is very short and lacks sourcing details, methodology, and direct attribution to the underlying data release.`
- Other evidence / curl outputs:
  - `/api/dev/documents` returned `201 Created` on reruns
  - `/api/documents/doc-a3-bbc-us-jobs-april/prepare` returned `200 OK` on reruns
  - `/api/documents/doc-a3-bbc-us-jobs-april/chunks` returned `200 OK`
  - `/api/documents/doc-a3-bbc-us-jobs-april/extract-claims` returned `500` before the adapter fix and `200/ready` after the fix
  - the blocking seam was narrowed to structured payload normalization in `llm/litellm_client.py`, not document prepare or routing
