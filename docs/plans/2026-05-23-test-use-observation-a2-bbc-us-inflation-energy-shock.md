# Test-use observation — BBC A2 US inflation / energy shock

Based on the first controlled real-data campaign pass run through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.

## Session metadata
- Date: 2026-05-23
- Tester: Hermes
- Runtime entrypoint: `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`
- Repo commit: `c975280`
- Notes scope: first factual-brief baseline pass for frozen corpus item A2

## Article / document
- Case ID: `campaign-a2-bbc-us-inflation-energy-shock`
- Document ID: `doc-a2-bbc-us-inflation-energy-shock`
- Source URL: `https://www.bbc.com/news/articles/c202pgxx89lo`
- Publisher: `BBC`
- Title: `US inflation jumps to 3.8% as energy costs surge from Iran war`
- Published at: `2026-05-12T00:00:00Z`
- Retrieved at: `2026-05-23T13:08:00+02:00`
- Language: `en`

## Input shape
- Article type:
  - factual brief
- Raw text length:
  - bounded excerpt, 8 source paragraphs seeded inline
- Number of prepared chunks:
  - 8
- Chunking method:
  - `paragraph-v1`
- Chunk notes:
  - paragraph chunking behaved cleanly
  - numeric facts remained easy to inspect
  - this pass used a bounded inline excerpt from the BBC article, not a full automated fetch pipeline

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
  - `200`
- Claim count:
  - `12`
- `diagnostics.dropped_claim_items`:
  - `0`
- `diagnostics.dropped_evidence_items`:
  - `0`
- Were final persisted claims concise and claim-like?
  - yes
- Did assistant/helpdesk prose appear?
  - no
- Example good claim:
  - `A rise in gasoline and grocery prices pushed the consumer price index (CPI) up to 3.8%.`
- Example bad claim:
  - `The S&P 500 fell 0.6%.`
- Notes on extraction quality:
  - persisted claims were concise and generally well anchored to paragraph spans
  - this pass looked cleaner than A1 on source-span specificity: all observed claims used `pN`, not `chunk-span:unknown`
  - main issue remained over-splitting into micro-claims for simple numeric/reporting paragraphs
  - the weakest outputs were not stylistically bad, but too atomized to preserve the article's compact causal framing
  - claim set split market reaction into multiple small items instead of keeping one tighter market-reaction claim

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mostly yes
- Did normalization appear to expand into summaries/explanations?
  - no
- Did normalization appear to inject assistant wording?
  - no
- Notes on normalization behavior:
  - no separate normalized-text surface was exposed, so this remains an inference from persisted claims
  - persisted claim text stayed close to source meaning and avoided obvious explanatory drift
  - do weryfikacji with a later slice that exposes normalization trace more directly

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `200`
- Was the credibility note useful?
  - useful
- Main credibility note takeaway:
  - BBC is a solid secondary source for the report, but the CPI figure and especially the causal Iran-war framing should be checked against the primary BLS release and supporting market data
- Notes on credibility quality:
  - strengths/concerns/checklist structure was again useful and concrete
  - the note correctly flagged the causal headline framing as something requiring independent confirmation
  - it was appropriately cautious without collapsing into generic boilerplate

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - yes
- Notes on verification/review usefulness:
  - API read-back was enough to inspect chunking, claim granularity, and credibility guidance
  - this factual brief was easier to review than A1 because span anchoring was clearer and the numeric facts were compact

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - extraction still over-splits short factual/numeric passages into multiple micro-claims, weakening compact event framing
- Highest-value next fix:
  - improve claim grouping heuristics for short economic briefs so tightly related numeric facts can remain bundled where the source presents them as one unit
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `US prices rose in April at their fastest rate since May 2023.`
  - `A rise in gasoline and grocery prices pushed the consumer price index (CPI) up to 3.8%.`
  - `Nearly half of the increase was caused by soaring energy prices.`
  - `Average paychecks grew by just 3.6%.`
  - `The S&P 500 fell 0.6%.`
- Diagnostics snapshot:
  - `{ "chunk_count": 8, "claim_count": 12, "dropped_claim_items": 0, "dropped_evidence_items": 0, "summary": "Extracted 12 claim(s) from 8 chunk(s)." }`
- Credibility note excerpt:
  - `BBC news report summarizing April US inflation data and attributing much of the increase to energy costs linked to the Iran war. The excerpt cites the Bureau of Labor Statistics and gives a specific CPI figure, but the causal framing and full context should be checked against the underlying BLS release and market data.`
- Other evidence / curl outputs:
  - create case: `201`
  - create document: `201`
  - prepare: `200`
  - extract-claims: `200`
  - list case claims: `200`
  - credibility POST/GET: `200`
  - prepared chunk example (`p3`): `The Bureau of Labor Statistics (BLS) said almost half of the rise was driven by surging energy costs, while housing and food costs also contributed.`
