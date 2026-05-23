# Test-use observation — D1 AP News / EIN Presswire war-market trends paid content

Based on the controlled real-data campaign pass run through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.

## Session metadata
- Date: 2026-05-23
- Tester: Hermes
- Runtime entrypoint: `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`
- Repo commit: `c975280`
- Notes scope: first weak/noisy-source baseline pass for frozen corpus item D1

## Article / document
- Case ID: `campaign-d1-ap-einpresswire-war-market-trends`
- Document ID: `doc-d1-ap-einpresswire-war-market-trends`
- Source URL: `https://apnews.com/press-release/ein-presswire-newsmatics/7-historical-stock-market-trends-triggered-by-the-impact-of-wars-2f663c743ed6be026e581bd5ade65dc5`
- Publisher: `AP News / EIN Presswire paid content`
- Author: `James W. Graves / EIN Presswire paid content`
- Title: `7 Historical Stock Market Trends Triggered By The Impact Of Wars`
- Published at: `2026-05-08T18:16:00-04:00`
- Retrieved at: `2026-05-23T15:20:00+02:00`
- Language: `en`

## Input shape
- Article type:
  - weak / secondary / noisy / promotional source
- Raw text length:
  - bounded excerpt, 6 seeded paragraphs
- Number of prepared chunks:
  - `6`
- Chunking method:
  - `paragraph-v1`
- Chunk notes:
  - the seeded input explicitly included the paid-content disclaimer
  - the rest of the excerpt consisted of broad investment theses and promotional market-history framing rather than narrow factual reporting
  - this is a good pressure test for whether extraction and credibility react differently to weak source posture

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
  - `U.S. stock markets have historically recovered and often grown after conflicts stabilize or end, especially since World War II.`
- Example bad claim:
  - `Short-term volatility often leads to long-term growth.`
- Notes on extraction quality:
  - extraction stayed mechanically clean, but it did not internalize the weak-source caveat into claim selection
  - the paid-content disclaimer was present in the input, yet the extractor still produced a large set of broad advisory/generalizing claims as if they were ordinary analyst-grade artifacts
  - many claims were slogan-like or thesis-like rather than evidence-ready, e.g. `Thinking beyond obvious sectors can improve results.` and `Markets are unemotional even when people are not.`
  - several claims also fell back to `chunk-span:unknown`
  - this means extraction remains proposition-friendly even when the source posture is weak, promotional, or only lightly evidenced

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mostly
- Did normalization appear to expand into summaries/explanations?
  - no
- Did normalization appear to inject assistant wording?
  - no
- Notes on normalization behavior:
  - no separate normalization surface was exposed; judgment is inferred from persisted claims
  - the issue was not added style, but insufficient skepticism in what gets preserved as a claim candidate
  - broad promotional theses remained intact rather than being de-emphasized

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `200`
- Was the credibility note useful?
  - yes
- Main credibility note takeaway:
  - the system correctly recognized that this is sponsored paid content hosted on AP News, not editorial AP reporting, and should not be treated as independently verified market analysis
- Notes on credibility quality:
  - this was one of the best credibility behaviors seen in the campaign so far
  - the note explicitly flagged:
    - sponsored press release status
    - AP newsroom non-involvement
    - promotional/investment framing
    - possible selective historical presentation
  - source reliability was correctly set to `low`
  - information credibility was correctly set to `low`

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - yes
- Notes on verification/review usefulness:
  - the combined output was useful only if the operator read the credibility layer alongside extraction
  - extraction alone would overstate the practical usefulness of the source
  - credibility made the problem legible, but there is still a gap because extraction does not down-rank or otherwise mark promotional theses as weak artifacts

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - extraction quality does not yet adapt enough to low-credibility / sponsored-source posture; it still emits broad claims too eagerly
- Highest-value next fix:
  - propagate weak-source posture into extraction/review surfaces so sponsored/promotional theses are marked, filtered, or downgraded earlier
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `U.S. stock markets have historically recovered and often grown after conflicts stabilize or end, especially since World War II.`
  - `War-driven volatility often creates buying opportunities for disciplined investors because the underlying fundamentals of most companies do not change dramatically.`
  - `Short-term volatility often leads to long-term growth.`
  - `Investors should stay disciplined, focus on fundamentals, and build portfolio resilience rather than reacting emotionally to war-related headlines.`
- Diagnostics snapshot:
  - `{ "chunk_count": 6, "claim_count": 13, "dropped_claim_items": 0, "dropped_evidence_items": 0, "summary": "Extracted 13 claim(s) from 6 chunk(s)." }`
- Credibility note excerpt:
  - `Paid press release/opinion-style market commentary distributed via EIN Presswire and hosted on AP News. It presents a broad historical claim that wars cause short-term volatility but markets often recover, framing this as a potential investing opportunity. Because it is sponsored content and not AP reporting, it should not be treated as an independently verified news source.`
- Other evidence / curl outputs:
  - create case: `201`
  - create document: `201`
  - prepare: `200`
  - extract-claims: `200`
  - list case claims: `200`
  - credibility POST/GET: `200`
