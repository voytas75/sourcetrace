# Test-use observation — BBC B3 Gulf economies / Iran conflict analysis

Based on the controlled real-data campaign pass run through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.

## Session metadata
- Date: 2026-05-23
- Tester: Hermes
- Runtime entrypoint: `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`
- Repo commit: `c975280`
- Notes scope: third longer-analytical baseline pass for frozen corpus item B3

## Article / document
- Case ID: `campaign-b3-bbc-gulf-economies-iran-conflict`
- Document ID: `doc-b3-bbc-gulf-economies-iran-conflict`
- Source URL: `https://www.bbc.com/news/articles/c0k257g8jk5o`
- Publisher: `BBC News`
- Author: `Sameer Hashmi`
- Title: `Gulf economies face long-term hit from Iran conflict`
- Published at: `2026-05-06T00:00:00Z`
- Retrieved at: `2026-05-23T13:37:00+02:00`
- Language: `en`

## Input shape
- Article type:
  - longer regional economic analysis
- Raw text length:
  - bounded analytical excerpt, 10 seeded paragraphs
- Number of prepared chunks:
  - `10`
- Chunking method:
  - `paragraph-v1`
- Chunk notes:
  - the pass used a bounded BBC extract rather than the full original body
  - the seeded input mixed conflict facts, institutional forecasts, estimates, and regional explanatory synthesis
  - this is sufficient to pressure-test traceability and attribution handling in long-form analysis

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
  - `200`
- Claim count:
  - `18`
- `diagnostics.dropped_claim_items`:
  - `0`
- `diagnostics.dropped_evidence_items`:
  - `0`
- Were final persisted claims concise and claim-like?
  - yes
- Did assistant/helpdesk prose appear?
  - no
- Example good claim:
  - `The closure of the Strait of Hormuz has sharply reduced oil and gas flows, forcing Gulf exporters to use limited alternative pipelines.`
- Example bad claim:
  - `Over a third were severely damaged.`
- Notes on extraction quality:
  - this pass was cleaner than B1 and similar in shape to B2
  - the system preserved many major regional claims in readable form without chatty drift
  - the recurring weakness remained attribution/context thinning for estimate-heavy statements
  - several numerically important claims still fell back to `chunk-span:unknown`
  - some outputs became too thin as standalone artifacts because the estimate source was stripped away, e.g. `Across the Gulf, the conflict has caused up to $58bn in damage.` and `Over a third were severely damaged.`
  - long-form analytical handling is therefore usable, but still not reliably evidence-ready when claims depend on explicit source attribution

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mostly
- Did normalization appear to expand into summaries/explanations?
  - no major over-expansion
- Did normalization appear to inject assistant wording?
  - no
- Notes on normalization behavior:
  - no separate normalization surface was exposed; judgment is inferred from persisted claims
  - unlike B1, the main issue here was not generalized reframing of the whole article
  - instead, the system often retained the substantive meaning but weakened provenance by dropping source language like `according to one estimate`, `the International Energy Agency says`, or `the World Bank cut...`

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `200`
- Was the credibility note useful?
  - yes
- Main credibility note takeaway:
  - BBC plus named author gives a solid secondary-source baseline, but the excerpt alone does not expose attribution or primary evidence strongly enough for the most consequential conflict/economic claims
- Notes on credibility quality:
  - the note was appropriately cautious and highlighted exactly the right verification surfaces
  - for this document, credibility assessment again felt healthier than extraction traceability
  - conflict-sensitive and estimate-based claims still clearly need external verification

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - yes
- Notes on verification/review usefulness:
  - review was possible and materially easier than B1
  - however, several extracted claims still required the analyst to reconstruct missing attribution from the original article framing
  - this remains the central long-form review burden in bucket B

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - estimate-heavy and institution-attributed statements still lose provenance detail too easily during extraction
- Highest-value next fix:
  - preserve source attribution markers (`according to`, `X says`, `World Bank cut`, `IEA says`) in extracted claims for long-form analytical content
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `The Iran conflict has caused a major economic shock across Gulf states, with damage to energy infrastructure, reduced exports, tourism losses, and emerging financial stress.`
  - `A ballistic missile reportedly knocked out 17% of global LNG supply.`
  - `Across the Gulf, the conflict has caused up to $58bn in damage.`
  - `Over a third were severely damaged.`
  - `The World Bank cut its Middle East growth forecast to 1.8% for the year, down from a previous estimate of 4% in 2026.`
- Diagnostics snapshot:
  - `{ "chunk_count": 10, "claim_count": 18, "dropped_claim_items": 0, "dropped_evidence_items": 0, "summary": "Extracted 18 claim(s) from 10 chunk(s)." }`
- Credibility note excerpt:
  - `BBC News article by a named journalist reports broad economic impacts on Gulf states from the Iran conflict, citing specific claims about infrastructure damage, LNG disruption, and Strait of Hormuz closures.`
- Other evidence / curl outputs:
  - create case: `201`
  - create document: `201`
  - prepare: `200`
  - extract-claims: `200`
  - list case claims: `200`
  - credibility POST/GET: `200`
