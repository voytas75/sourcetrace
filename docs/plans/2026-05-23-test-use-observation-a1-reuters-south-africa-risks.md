# Test-use observation — Reuters A1 South Africa coalition / wider Africa risks

Based on the first controlled real-data campaign pass run through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.

## Session metadata
- Date: 2026-05-23
- Tester: Hermes
- Runtime entrypoint: `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`
- Repo commit: `c975280`
- Notes scope: first factual-brief baseline pass for frozen corpus item A1

## Article / document
- Case ID: `campaign-a1-reuters-south-africa-risks`
- Document ID: `doc-a1-reuters-south-africa-risks`
- Source URL: `https://www.reuters.com/world/africa/sp-says-it-is-watching-south-africa-coalition-middle-east-conflict-risks-wider-2026-05-13/`
- Publisher: `Reuters`
- Title: `S&P says it is watching South Africa coalition, Middle East conflict risks for wider Africa`
- Published at: `2026-05-13T12:35:41Z`
- Retrieved at: `2026-05-23T12:58:33+02:00`
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
  - input remained compact and attributable
  - this pass used a bounded inline excerpt derived from the Reuters text, not a full automated fetch pipeline

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
  - mixed
- Did assistant/helpdesk prose appear?
  - no
- Example good claim:
  - `South Africa faces a double blow from domestic political uncertainty and external headwinds.`
- Example bad claim:
  - `The global median is around 5.5%.`
- Notes on extraction quality:
  - extraction stayed mostly concise and non-chatty
  - no obvious assistant/helpdesk drift appeared in the persisted claims
  - main issue was over-fragmentation and decontextualization rather than stylistic drift
  - several claims were split into very small standalone statements that lose source framing, e.g. `The Middle East conflict now poses a risk.` and `The global median is around 5.5%.`
  - multiple claims carried `source_span_reference: chunk-span:unknown` even when source anchoring should have been more specific

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - unclear
- Did normalization appear to expand into summaries/explanations?
  - no
- Did normalization appear to inject assistant wording?
  - no
- Notes on normalization behavior:
  - this pass did not expose a separate normalized-text surface, so normalization quality cannot be isolated with confidence
  - no obvious assistant-style rewrite was visible in the persisted claim text
  - do weryfikacji on a later slice with a clearer normalization read-back or comparative trace

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `200`
- Was the credibility note useful?
  - useful
- Main credibility note takeaway:
  - Reuters is treated as a strong secondary source, but the excerpt is incomplete and key claims should be checked against the full Reuters piece plus primary S&P / court materials
- Notes on credibility quality:
  - strengths/concerns/checklist structure was useful and concrete
  - verification checks were specific enough to guide follow-up
  - the note correctly recognized the bounded excerpt as a limitation instead of overstating confidence

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - yes
- Notes on verification/review usefulness:
  - API read-back was enough to inspect prepared chunks, persisted claims, and credibility output
  - biggest review gap in this pass was weak source-span specificity for several claims

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - extraction tends to over-split compact factual text into smaller context-thin claims, and source-span anchoring is often too weak (`chunk-span:unknown`)
- Highest-value next fix:
  - tighten extraction/claim post-processing so short factual briefs preserve tighter claim grouping and more specific source-span references
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `South Africa faces a double blow from domestic political uncertainty and external headwinds.`
  - `S&P Global Ratings is watching to see whether the country’s coalition government stays intact and keeps up the reforms that led to last year’s credit rating upgrade.`
  - `The Middle East conflict now poses a risk.`
  - `African sovereigns spend on average around 17% of revenues on interest payments.`
  - `The global median is around 5.5%.`
- Diagnostics snapshot:
  - `{ "chunk_count": 9, "claim_count": 15, "dropped_claim_items": 0, "dropped_evidence_items": 0, "summary": "Extracted 15 claim(s) from 9 chunk(s)." }`
- Credibility note excerpt:
  - `Reuters reports that S&P Global Ratings is monitoring risks to South Africa from coalition instability and external shocks tied to the Middle East conflict. The excerpt attributes the core assessment to S&P and references a Constitutional Court development affecting President Ramaphosa, but the provided text is only a partial snippet and key claims should be checked against the full Reuters piece and underlying S&P statements or court materials.`
- Other evidence / curl outputs:
  - create case: `201`
  - create document: `201`
  - prepare: `200`
  - extract-claims: `200`
  - list case claims: `200`
  - credibility POST/GET: `200`
  - prepared chunk example (`p7`): `More than three-quarters of rated African sovereigns are net importers of fuel and fertilizer, leaving countries such as Egypt, Mozambique and Rwanda most exposed to war-driven price rises, while exporters like Nigeria and Angola are better insulated.`
