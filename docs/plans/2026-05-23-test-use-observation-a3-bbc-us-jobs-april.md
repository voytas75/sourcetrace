# Test-use observation — BBC A3 US jobs / April labour-market brief

Based on the first controlled real-data campaign pass run through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.

## Session metadata
- Date: 2026-05-23
- Tester: Hermes
- Runtime entrypoint: `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`
- Repo commit: `c975280`
- Notes scope: first factual-brief baseline pass for frozen corpus item A3

## Article / document
- Case ID: `campaign-a3-bbc-us-jobs-april`
- Document ID: `doc-a3-bbc-us-jobs-april`
- Source URL: `https://www.bbc.com/news/articles/cx21664lp32o`
- Publisher: `BBC`
- Title: `US jobs data beats expectations for second month in a row`
- Published at: `2026-05-08T00:00:00Z`
- Retrieved at: `2026-05-23T13:12:00+02:00`
- Language: `en`

## Input shape
- Article type:
  - factual brief
- Raw text length:
  - bounded excerpt, 9 source paragraphs seeded inline
- Number of prepared chunks:
  - 9
- Chunking method:
  - `paragraph-v1`
- Chunk notes:
  - paragraph chunking behaved cleanly
  - numeric labor-market facts remained easy to inspect
  - this pass used a bounded inline excerpt from the BBC article, not a full automated fetch pipeline

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
  - `200`
- Claim count:
  - `11`
- `diagnostics.dropped_claim_items`:
  - `0`
- `diagnostics.dropped_evidence_items`:
  - `0`
- Were final persisted claims concise and claim-like?
  - mixed
- Did assistant/helpdesk prose appear?
  - no
- Example good claim:
  - `The unemployment rate was unchanged at 4.3%.`
- Example bad claim:
  - `The increase was stronger than expected.`
- Notes on extraction quality:
  - claims remained short and non-chatty
  - no assistant/helpdesk prose appeared
  - main issue was again decontextualized micro-claims and partial loss of compact framing
  - several claims fell back to `source_span_reference: chunk-span:unknown`, especially around the opening expectation-vs-outcome framing and payroll history numbers
  - relative to A2, anchoring regressed; relative to A1, the quality issue is similar but slightly cleaner stylistically

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mostly yes
- Did normalization appear to expand into summaries/explanations?
  - no
- Did normalization appear to inject assistant wording?
  - no
- Notes on normalization behavior:
  - no separate normalized-text surface was exposed, so this remains an inference from persisted claims
  - the persisted claims stayed close to source language, but some claims became too context-thin after splitting
  - do weryfikacji with a later slice that exposes normalization trace more directly

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `200`
- Was the credibility note useful?
  - useful
- Main credibility note takeaway:
  - BBC is a credible secondary source for the jobs brief, but the BLS release should remain the primary check and the geopolitical framing requires extra caution
- Notes on credibility quality:
  - strengths/concerns/checklist structure was again concrete and useful
  - the note appropriately flagged the unusual geopolitical framing and the need to verify expectations sourcing
  - it remained specific rather than generic

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - yes
- Notes on verification/review usefulness:
  - API read-back was enough to inspect claims, spans, and credibility guidance
  - review was slightly worse than A2 because the `chunk-span:unknown` fallback returned on several central claims

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - extraction of short labor-market briefs still over-splits expectation/context paragraphs and sometimes loses specific source-span anchoring
- Highest-value next fix:
  - tighten extraction/post-processing for compact numeric/economic paragraphs so outcome + expectation + reference numbers are kept in tighter grouped claims with stable `pN` anchoring
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `The US economy created 115,000 jobs in April.`
  - `The increase was stronger than expected.`
  - `The unemployment rate was unchanged at 4.3%.`
  - `The number of jobs rose on average by 48,000 over the last three months.`
  - `The S&P 500 rose by 0.8%.`
- Diagnostics snapshot:
  - `{ "chunk_count": 9, "claim_count": 11, "dropped_claim_items": 0, "dropped_evidence_items": 0, "summary": "Extracted 11 claim(s) from 9 chunk(s)." }`
- Credibility note excerpt:
  - `BBC news report summarizing April US jobs figures and attributing the data to the US Bureau of Labor Statistics. The excerpt is specific about headline numbers but is a secondary account and includes a notable geopolitical framing claim that requires careful verification against the full article and primary data release.`
- Other evidence / curl outputs:
  - create case: `201`
  - create document: `201`
  - prepare: `200`
  - extract-claims: `200`
  - list case claims: `200`
  - credibility POST/GET: `200`
  - prepared chunk example (`p7`): `The better-than-expected jobs figures helped to lift the major US stock indexes. The S&P 500 rose by 0.8% and the Dow Jones Industrial Average closed flat.`
