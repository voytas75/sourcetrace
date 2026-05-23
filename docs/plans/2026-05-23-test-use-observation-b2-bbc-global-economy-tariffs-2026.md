# Test-use observation — BBC B2 tariffs / global economy 2026 analysis

Based on the controlled real-data campaign pass run through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.

## Session metadata
- Date: 2026-05-23
- Tester: Hermes
- Runtime entrypoint: `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`
- Repo commit: `c975280`
- Notes scope: second longer-analytical baseline pass for frozen corpus item B2

## Article / document
- Case ID: `campaign-b2-bbc-global-economy-tariffs-2026`
- Document ID: `doc-b2-bbc-global-economy-tariffs-2026`
- Source URL: `https://www.bbc.com/news/articles/czejp3gep63o`
- Publisher: `BBC`
- Author: `Jonathan Josephs`
- Title: `How tariffs will continue to reshape the global economy in 2026`
- Published at: `2026-01-07T00:00:00Z`
- Retrieved at: `2026-05-23T13:26:00+02:00`
- Language: `en`

## Input shape
- Article type:
  - longer analytical / explanatory macro article
- Raw text length:
  - bounded analytical excerpt, 10 seeded paragraphs
- Number of prepared chunks:
  - `10`
- Chunking method:
  - `paragraph-v1`
- Chunk notes:
  - the pass used a bounded extract based on BBC article summary material rather than the full body
  - the seeded input mixed attributed forecasts, analytical synthesis, and multi-factor macro framing
  - this is enough to test paraphrase pressure and attribution handling, but not enough for a full long-form final verdict

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
  - `200`
- Claim count:
  - `15`
- `diagnostics.dropped_claim_items`:
  - `0`
- `diagnostics.dropped_evidence_items`:
  - `0`
- Were final persisted claims concise and claim-like?
  - yes, but often too compressed
- Did assistant/helpdesk prose appear?
  - no
- Example good claim:
  - `Tariffs introduced during Donald Trump's second term have already reshaped the global economy and are expected to keep doing so through 2026.`
- Example bad claim:
  - `the tariff shock is smaller than originally announced`
- Notes on extraction quality:
  - there was no chatty drift, but multiple claims were reduced to unattributed proposition fragments
  - several outputs lost the original speaker / attribution framing (`IMF says`, `Kristalina Georgieva says`, `Maurice Obstfeld says`) and collapsed into bare statements
  - some claims became oddly compressed or stylized, e.g. `global growth [is] to slow to 3.1% in 2026`
  - `source_span_reference` was mixed: many claims had clean `pN` references, but some key numeric claims still fell back to `chunk-span:unknown`
  - compared with B1, this pass was cleaner structurally, but it still showed the same long-form weakness: analytical narrative gets flattened into proposition lists

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mixed
- Did normalization appear to expand into summaries/explanations?
  - less than B1, but yes on paraphrase compression
- Did normalization appear to inject assistant wording?
  - no
- Notes on normalization behavior:
  - no separate normalization surface was exposed; judgment is inferred from persisted claims
  - the main issue was not over-explanation, but compression that strips attribution and quotation context
  - longer analytical passages with expert/source attributions still do not reliably survive as attribution-preserving claims

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `200`
- Was the credibility note useful?
  - yes
- Main credibility note takeaway:
  - BBC + named author + IMF attribution gives a stronger baseline than B1, but the bounded excerpt is still too short to validate the article's full evidentiary chain
- Notes on credibility quality:
  - the note was appropriately cautious and materially better grounded than B1
  - it correctly identified secondary-analysis limits and suggested sensible verification checks
  - for long explanatory content, this credibility layer currently feels healthier than the claim extraction layer

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - yes
- Notes on verification/review usefulness:
  - API read-back was enough to spot the recurring long-form issue: attribution thinning
  - review is possible, but the analyst has to reconstruct too much of the original framing manually
  - the first attempt also hit a live timeout after `prepare`; after runtime restart and stepwise retry, extract and credibility completed successfully

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - attributed analytical statements are often converted into de-attributed proposition fragments, weakening traceability
- Highest-value next fix:
  - preserve source attribution in extracted claims for expert forecasts, institutional forecasts, and analysis-with-quote passages
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `Tariffs introduced during Donald Trump's second term have already reshaped the global economy and are expected to keep doing so through 2026.`
  - `the tariff shock is smaller than originally announced`
  - `global growth [is] to slow to 3.1% in 2026`
  - `China induced the US to back down quickly`
  - `tariffs have not produced a trade disaster but have left the global economy with slower growth, more uncertainty, and unresolved policy risks.`
- Diagnostics snapshot:
  - `{ "chunk_count": 10, "claim_count": 15, "dropped_claim_items": 0, "dropped_evidence_items": 0, "summary": "Extracted 15 claim(s) from 10 chunk(s)." }`
- Credibility note excerpt:
  - `BBC news analysis summarizing expected 2026 effects of Trump-era tariffs on global growth, costs, trade flows, US manufacturing, and US-China tensions, with at least one attributed IMF forecast.`
- Other evidence / curl outputs:
  - create case: `201`
  - create document: `201`
  - prepare: `200`
  - extract-claims: `200`
  - list case claims: `200`
  - credibility POST/GET: `200`
  - first all-in-one attempt timed out after `prepare`; rerun succeeded when calls were split and extraction/credibility were given longer timeouts
