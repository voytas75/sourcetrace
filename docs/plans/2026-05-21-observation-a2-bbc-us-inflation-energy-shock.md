# Observation note — A2 BBC US inflation energy shock

Based on template: `docs/plans/test-use-observation-template.md`
Campaign corpus source: `docs/plans/2026-05-21-real-data-campaign-corpus-v1.md`

## Session metadata
- Date: 2026-05-21
- Tester: Wojciech Napierała / Hermes-assisted
- Runtime entrypoint: `python -m sourcetrace.local_launcher`
- Repo commit: `cbd29e6`
- Notes scope: Phase 1 start-set pass for A2 on local launcher runtime

## Article / document
- Case ID: `campaign-a2-bbc-us-inflation-energy-shock`
- Document ID: `doc-a2-bbc-us-inflation-energy-shock`
- Source URL: `https://www.bbc.com/news/articles/c202pgxx89lo`
- Publisher: `BBC`
- Title: `US inflation jumps to 3.8% as energy costs surge from Iran war`
- Published at: `2026-05-12`
- Retrieved at: `2026-05-21T12:27:35+02:00`
- Language: `en`

## Input shape
- Article type:
  - factual brief
- Raw text length:
  - approximately 770 chars in the runtime-tested inline excerpt
- Number of prepared chunks:
  - 7
- Chunking method:
  - paragraph-v1
- Chunk notes:
  - metadata persisted correctly through `/api/dev/documents`
  - chunks were clean and paragraph-like
  - this run used a shortened inline excerpt, not the full BBC page body

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
  - initial run: `500 internal server error`
  - rerun before adapter fix: `500 internal server error`
  - rerun after bounded adapter fix: `ready`
- Claim count:
  - 19 persisted claims on the post-fix rerun with the richer inline excerpt
- `diagnostics.dropped_claim_items`:
  - 0 on the post-fix rerun
- `diagnostics.dropped_evidence_items`:
  - 0 on the post-fix rerun
- Were final persisted claims concise and claim-like?
  - mixed
- Did assistant/helpdesk prose appear?
  - no obvious assistant/helpdesk prose in persisted claims on the post-fix rerun
- Example good claim:
  - `US prices rose in April at their fastest rate since May 2023.`
- Example bad claim:
  - `The US-Israel war in Iran, and the resulting effective closure of the Strait of Hormuz shipping lane, has led to a jump in oil prices and this has caused a surge in the price of gas in the US.`
- Notes on extraction quality:
  - the original runtime blocker was real: extraction previously failed on this campaign-shaped input with `LlmSchemaError: structured payload for ClaimExtractionPayload must be a mapping`
  - after the bounded adapter fix in `llm/litellm_client.py`, the same campaign-shaped A2 input now extracts successfully end-to-end
  - persisted claims are now available for quality review, so A2 can contribute to the Phase 1 verdict
  - quality is still only mixed: several claims are useful and concise, but some remain too long or preserve speculative/causal framing too broadly for a tight claim set

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mixed
- Did normalization appear to expand into summaries/explanations?
  - slightly
- Did normalization appear to inject assistant wording?
  - no obvious assistant wording on the post-fix rerun
- Notes on normalization behavior:
  - the post-fix rerun made normalization observable again
  - source meaning was generally preserved on straightforward numeric claims, but several longer claims remained too broad and read more like sentence carry-through than tightly bounded extraction

## Post-fix rerun evidence
- After commit `38a137f`, an isolated rerun used a fresh case/document on the local launcher.
- Prepare succeeded with 1 chunk.
- Extract succeeded with 5 claims.
- The previous carry-through style causal sentence appeared as two tighter claims:
  - `Inflation rose because of higher energy prices.`
  - `Economists said the increase might only be temporary if wholesale gas prices continue to fall.`

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `ready`
- Was the credibility note useful?
  - useful
- Main credibility note takeaway:
  - the note correctly treated the input as a short secondary news excerpt with specific but not fully evidenced causal framing
- Notes on credibility quality:
  - strengths were specific: mainstream publisher, concrete statistic, dated metadata, plausibly verifiable topic
  - concerns were also concrete: short excerpt, no visible primary citation, causal claim about Iran/energy not evidenced in excerpt, headline may overstate causation
  - this suggests credibility drafting is still operational even when extraction is failing

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
  - runtime extraction blocker is closed, but claim compactness and boundedness are still uneven on longer causal statements
- Highest-value next fix:
  - tighten extraction/normalization quality so long causal or multi-clause article sentences do not pass through as oversized claims
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `US prices rose in April at their fastest rate since May 2023.`
  - `A jump in the cost of gasoline and groceries pushed the consumer price index (CPI) to 3.8% over the past 12 months.`
  - `The national average price for a gallon of unleaded is at its highest level since July 2022, at $4.50, according to AAA data.`
- Diagnostics snapshot:
  - initial prepare: `Prepared 7 chunk(s).`
  - rerun before fix prepare: `Prepared 8 chunk(s).`
  - rerun after fix prepare: `Prepared 19 chunk(s).`
  - extract HTTP response (initial): `500 Internal Server Error`
  - extract HTTP response (rerun before fix): `500 Internal Server Error`
  - extract response after fix: `Extracted 19 claim(s) from 19 chunk(s).`
- Credibility note excerpt:
  - `BBC news report excerpt claims US inflation rose to 3.8% in April 2026 and attributes the increase partly to energy costs linked to the war in Iran.`
  - `Based on the excerpt alone, this is a secondary news summary with limited visible sourcing and insufficient detail to verify the figures or causal framing.`
- Other evidence / curl outputs:
  - `/api/dev/documents` returned `201 Created` on reruns
  - `/api/documents/doc-a2-bbc-us-inflation-energy-shock/prepare` returned `200 OK` on reruns
  - `/api/documents/doc-a2-bbc-us-inflation-energy-shock/chunks` returned `200 OK`
  - `/api/documents/doc-a2-bbc-us-inflation-energy-shock/extract-claims` returned `500` before the adapter fix and `200/ready` after the fix
  - the blocking seam was narrowed to structured payload normalization in `llm/litellm_client.py`, not document prepare or routing
