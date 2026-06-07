# Test-use observation example — BBC climate article

Based on the live smoke run against `python -m sourcetrace.local_launcher` after the normalization fallback fixes.

## Session metadata
- Date: 2026-05-19
- Tester: Hermes
- Runtime entrypoint: `python -m sourcetrace.local_launcher`
- Repo commit: `18a69a0` was the active docs+heuristics baseline before the final observation-template slice
- Notes scope: real-article extraction quality check after normalization fallback refinement

## Article / document
- Case ID: `case-bbc-2`
- Document ID: `doc-bbc-2`
- Source URL: `https://www.bbc.com/news/articles/c5y5p9rzd4ko`
- Publisher: BBC News
- Title: Global temperatures dip in 2025 but more heat records on way, scientists warn
- Published at: `2026-01-13T00:00:00+00:00`
- Retrieved at: `2026-05-19T22:00:00+00:00`
- Language: `en`

## Input shape
- Article type:
  - longer analysis
- Raw text length:
  - bounded excerpt of 4 paragraphs, not full article body
- Number of prepared chunks:
  - 4
- Chunking method:
  - `paragraph-v1`
- Chunk notes:
  - each paragraph became a separate chunk
  - input mixed straightforward factual statements with explanatory climate context

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
  - `200`
- Claim count:
  - 4
- `diagnostics.dropped_claim_items`:
  - `0`
- `diagnostics.dropped_evidence_items`:
  - `0`
- Were final persisted claims concise and claim-like?
  - mixed
- Did assistant/helpdesk prose appear?
  - some claims
- Example good claim:
  - `The last three years were the world's warmest ever recorded, bringing the planet closer to breaching international climate targets.`
- Example bad claim:
  - `You're absolutely right. Even with the natural cooling influence of La Niña, global temperatures in 2025 remained significantly higher than those from a decade ago...`
- Notes on extraction quality:
  - first half of the output was acceptable and close to source text
  - later claims expanded into explanatory assistant-style prose instead of short extractive claims
  - the current guardrails reduced some bad rewrites, but did not eliminate them on a real analytical article

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mixed
- Did normalization appear to expand into summaries/explanations?
  - heavily
- Did normalization appear to inject assistant wording?
  - yes
- Notes on normalization behavior:
  - this run is consistent with normalization being one of the main leak points for assistant-style text
  - the fallback catches some conversational rewrites, but long explanatory rewrites can still survive

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - not tested in this specific smoke run
- Was the credibility note useful?
  - not tested
- Main credibility note takeaway:
  - n/a
- Notes on credibility quality:
  - this observation focused on extraction/normalization only

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - no
- Notes on verification/review usefulness:
  - this run was intentionally bounded to claim extraction quality on a real article

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - assistant-style rewrites still appear in some persisted claims for longer analytical text
- Highest-value next fix:
  - tighten normalization fallback further, likely using stronger shape/length heuristics instead of phrase-only detection
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `Global temperatures in 2025 did not quite reach the heights of 2024, thanks to the cooling influence of the natural La Niña weather pattern in the Pacific, new data from the European Copernicus climate service and the Met Office shows.`
  - `The last three years were the world's warmest ever recorded, bringing the planet closer to breaching international climate targets.`
  - `You're absolutely right. Even with the natural cooling influence of La Niña, global temperatures in 2025 remained significantly higher than those from a decade ago...`
  - `Your statement is accurate and reflects the consensus among climate scientists...`
- Diagnostics snapshot:
  - `{ "dropped_claim_items": 0, "dropped_evidence_items": 0 }`
- Credibility note excerpt:
  - n/a
- Other evidence / curl outputs:
  - extract route status `200`
  - persisted claims route status `200`
