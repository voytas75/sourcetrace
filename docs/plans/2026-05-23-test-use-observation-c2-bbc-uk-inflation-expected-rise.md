# Test-use observation — BBC C2 UK inflation / expected rise / mixed certainty

Based on the controlled real-data campaign pass run through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.

## Session metadata
- Date: 2026-05-23
- Tester: Hermes
- Runtime entrypoint: `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`
- Repo commit: `c975280`
- Notes scope: second quotes/caveats/mixed-certainty baseline pass for frozen corpus item C2

## Article / document
- Case ID: `campaign-c2-bbc-uk-inflation-expected-rise`
- Document ID: `doc-c2-bbc-uk-inflation-expected-rise`
- Source URL: `https://www.bbc.com/news/articles/c4g0e0p4p2go`
- Publisher: `BBC News`
- Author: `BBC summary extract`
- Title: `Inflation falls to 2.8%, but is expected to rise from here`
- Published at: `2026-05-20T00:00:00Z` (`do weryfikacji` against article metadata)
- Retrieved at: `2026-05-23T14:08:00+02:00`
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
  - the seeded excerpt mixed hard stats, expectations, named expert comments, and explanatory background
  - this is a good test for whether the system distinguishes data from forecasts and keeps attribution attached to forward-looking statements

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
  - mostly
- Did assistant/helpdesk prose appear?
  - no
- Example good claim:
  - `The article says 2.8% is likely as low as it gets for some time.`
- Example bad claim:
  - `inflation will trend higher through much of 2026, heading towards 4% by the end of the year`
- Notes on extraction quality:
  - caveat-bearing and expectation-bearing language survived in some form, which is good
  - however, attribution flattening was more visible here than in C1
  - multiple claims lost speaker identity entirely, e.g. `economists broadly expect ...`, `inflation will trend higher ...`, `the 7% fall in the energy price cap ... would be short-lived`, and `annual costs ... continued to rise ...`
  - some claim texts were also awkwardly clipped or lowercased, which weakens analyst readability
  - `chunk-span:unknown` appeared again on straightforward numeric claims such as the top-line inflation rate and food/drink inflation
  - overall this pass confirms that the system can preserve uncertainty semantics better than source attribution, but with notable degradation when multiple quoted/expert voices are mixed into one short article

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mostly
- Did normalization appear to expand into summaries/explanations?
  - no
- Did normalization appear to inject assistant wording?
  - no
- Notes on normalization behavior:
  - no separate normalization surface was exposed; judgment is inferred from persisted claims
  - the main issue was not over-explanation but de-attribution and partial sentence flattening
  - several outputs preserved the gist but lost provenance and sentence completeness

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `200`
- Was the credibility note useful?
  - yes
- Main credibility note takeaway:
  - BBC is a decent secondary baseline, but the excerpt is not enough to treat forecast and causal claims as self-sufficient; review should separate observed CPI facts from forward-looking inflation expectations
- Notes on credibility quality:
  - the note correctly distinguished current data from forecasts
  - it also correctly flagged vague attribution as a concern
  - this is exactly the review problem seen in extraction

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - yes
- Notes on verification/review usefulness:
  - review was possible, but less clean than C1
  - the operator would still need to reconstruct who said what for several forecast statements before trusting them as decision-ready artifacts

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - forecast and expert-judgment claims still lose source ownership too easily, and some extracted fragments degrade stylistically
- Highest-value next fix:
  - preserve attribution labels and sentence integrity for quoted/expert forecast statements (`economists expect`, `Yael Selfin said`, `Lindsay James said`, `Grant Fitzner said`)
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `UK inflation fell to 2.8% in the year to April, down from 3.3% in March.`
  - `economists broadly expect inflation to rise again, potentially reaching around 4% by the end of the year`
  - `inflation will trend higher through much of 2026, heading towards 4% by the end of the year`
  - `the 7% fall in the energy price cap in April was good for consumers but would be short-lived`
- Diagnostics snapshot:
  - `{ "chunk_count": 8, "claim_count": 12, "dropped_claim_items": 0, "dropped_evidence_items": 0, "summary": "Extracted 12 claim(s) from 8 chunk(s)." }`
- Credibility note excerpt:
  - `BBC News summary reporting UK CPI at 2.8% in April and citing expectations of renewed inflation increases driven by energy costs and conflict-related fuel pressures. The excerpt includes some concrete figures but limited attribution detail and appears to be a secondary news summary rather than primary statistical material.`
- Other evidence / curl outputs:
  - create case: `201`
  - create document: `201`
  - prepare: `200`
  - extract-claims: `200`
  - list case claims: `200`
  - credibility POST/GET: `200`
