# Test-use observation — BBC C1 UK growth forecast / IMF risks and caveats

Based on the controlled real-data campaign pass run through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.

## Session metadata
- Date: 2026-05-23
- Tester: Hermes
- Runtime entrypoint: `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`
- Repo commit: `c975280`
- Notes scope: first quotes/caveats/mixed-certainty baseline pass for frozen corpus item C1

## Article / document
- Case ID: `campaign-c1-bbc-uk-growth-risks`
- Document ID: `doc-c1-bbc-uk-growth-risks`
- Source URL: `https://www.bbc.com/news/articles/cm2p72mmddyo`
- Publisher: `BBC News`
- Author: `Michael Race; Faisal Islam`
- Title: `UK growth forecast upgraded by IMF but risks remain`
- Published at: `2026-05-18T00:00:00Z`
- Retrieved at: `2026-05-23T13:58:00+02:00`
- Language: `en`

## Input shape
- Article type:
  - quotes / caveats / mixed certainty
- Raw text length:
  - bounded analytical excerpt, 8 seeded paragraphs
- Number of prepared chunks:
  - `8`
- Chunking method:
  - `paragraph-v1`
- Chunk notes:
  - the seeded excerpt was intentionally rich in institutional attribution (`IMF said`, `Luc Eyraud said`), forecast language, and explicit caveats
  - this is a good pressure test for whether the system preserves who-says-what and uncertainty language rather than flattening them into bare propositions

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
  - `200`
- Claim count:
  - `13`
- `diagnostics.dropped_claim_items`:
  - `0`
- `diagnostics.dropped_evidence_items`:
  - `0`
- Were final persisted claims concise and claim-like?
  - yes
- Did assistant/helpdesk prose appear?
  - no
- Example good claim:
  - `IMF forecasts are only predictions and can be wrong because of world events.`
- Example bad claim:
  - `Markets and investors put a premium on predictable government policy.`
- Notes on extraction quality:
  - the system preserved several caveat-bearing statements more cleanly than expected
  - importantly, it retained one explicit uncertainty statement almost verbatim: `IMF forecasts are only predictions and can be wrong because of world events.`
  - however, attribution thinning remained clearly visible across the pass
  - `The International Monetary Fund said...` became `The International Monetary Fund has upgraded its forecast...` with `chunk-span:unknown`
  - `Luc Eyraud said...` collapsed into `Markets and investors put a premium on predictable government policy.`
  - several claims preserved risk/caveat semantics but still lost speaker/source framing that matters for analyst review
  - this means the system can preserve uncertainty language better than it preserves attribution language

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mostly
- Did normalization appear to expand into summaries/explanations?
  - no
- Did normalization appear to inject assistant wording?
  - no
- Notes on normalization behavior:
  - no separate normalization surface was exposed; judgment is inferred from persisted claims
  - the output did not over-explain or become chatty
  - the main weakness was still flattening attributed judgments into unattributed propositions
  - compared with bucket B, this C1 pass handled explicit caveat phrasing somewhat better, but still did not robustly preserve `X said` structure

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `200`
- Was the credibility note useful?
  - yes
- Main credibility note takeaway:
  - the BBC summary is a reasonable secondary-source baseline, but key numbers and policy language should be checked against the underlying IMF publication because the excerpt may simplify the original caveats
- Notes on credibility quality:
  - this was one of the healthier credibility outputs so far
  - the note correctly identified the main review task: distinguish BBC framing from IMF wording
  - the verification checks were specific and proportionate

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - yes
- Notes on verification/review usefulness:
  - review was workable and easier than B1
  - the operator could still use the output as a first-pass briefing artifact
  - but final analyst confidence would still require reconstructing explicit IMF attribution from the source article or primary IMF text

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - explicit speaker attribution and institutional provenance still flatten too easily into unattributed claims
- Highest-value next fix:
  - preserve `X said / IMF said / mission chief said / article notes` markers in extracted claims, especially for forecasts, caveats, and policy judgments
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `The International Monetary Fund has upgraded its forecast for the UK's growth this year.`
  - `A prolonged conflict in the Middle East risked hitting growth and resulting in higher energy and food prices.`
  - `Markets and investors put a premium on predictable government policy.`
  - `IMF forecasts are only predictions and can be wrong because of world events.`
- Diagnostics snapshot:
  - `{ "chunk_count": 8, "claim_count": 13, "dropped_claim_items": 0, "dropped_evidence_items": 0, "summary": "Extracted 13 claim(s) from 8 chunk(s)." }`
- Credibility note excerpt:
  - `BBC News report summarizing an IMF forecast upgrade for UK growth and associated risks. The outlet and named authors support reliability, but the document is a secondary news account and the provided excerpt is brief, so key figures, context, and quotations should be checked against the underlying IMF publication.`
- Other evidence / curl outputs:
  - create case: `201`
  - create document: `201`
  - prepare: `200`
  - extract-claims: `200`
  - list case claims: `200`
  - credibility POST/GET: `200`
