# Test-use observation — AP B1 tax cuts / inflation / midterms analysis

Based on the first controlled real-data campaign pass run through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.

## Session metadata
- Date: 2026-05-23
- Tester: Hermes
- Runtime entrypoint: `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`
- Repo commit: `c975280`
- Notes scope: first longer-analytical baseline pass for frozen corpus item B1

## Article / document
- Case ID: `campaign-b1-ap-trump-tax-cuts-inflation`
- Document ID: `doc-b1-ap-trump-tax-cuts-inflation`
- Source URL: `https://apnews.com/article/trump-north-carolina-senate-big-beautiful-bill-09c3d170f57f56c74a7e4e35d6cf2dee`
- Publisher: `AP News`
- Title: `Tax cuts collide with inflation as voters weigh Trump's economy in the midterms`
- Published at: `2026-05-13T00:00:00Z`
- Retrieved at: `2026-05-23T13:18:00+02:00`
- Language: `en`

## Input shape
- Article type:
  - longer analytical article
- Raw text length:
  - bounded analytical excerpt, 12 seeded paragraphs
- Number of prepared chunks:
  - 12
- Chunking method:
  - `paragraph-v1`
- Chunk notes:
  - the pass used a bounded extract built from AP summary/excerpt material, not the full original long-form body
  - the seeded input already contained analysis-heavy framing, voter examples, and mixed interpretive claims
  - this makes the pass useful for drift detection, but not yet a final verdict on full-body long-form handling

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
  - `The law does not fully eliminate federal taxes on overtime.`
- Example bad claim:
  - `North Carolina’s U.S. Senate race makes the problem especially clear.`
- Notes on extraction quality:
  - no assistant/helpdesk prose appeared, but analytical framing was often flattened into thin standalone statements
  - several claims were decontextualized reframings rather than cleanly anchored source-preserving claims
  - many key claims fell back to `source_span_reference: chunk-span:unknown`
  - the model split multi-part analytical passages into short claims that lost who-says-what framing and article-level attribution
  - voter-example paragraphs were atomized into small claims like `One voter cannot afford health insurance.` and `One voter is not committed to either party.`, which are technically recoverable but much weaker as analyst artifacts

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mixed
- Did normalization appear to expand into summaries/explanations?
  - somewhat
- Did normalization appear to inject assistant wording?
  - no clear assistant tone, but yes on reframing / summarizing pressure
- Notes on normalization behavior:
  - no separate normalization surface was exposed, so this is inferred from persisted claims
  - compared with bucket A, there was more evidence of summary-like reframing and attribution thinning
  - the issue was not chatty assistant prose, but conversion of analytical narrative into generic proposition-style claims

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `200`
- Was the credibility note useful?
  - somewhat useful
- Main credibility note takeaway:
  - AP is a strong publisher, but the bounded excerpt is too short and too interpretive to judge the underlying sourcing without reviewing the full article
- Notes on credibility quality:
  - the note correctly recognized the excerpt as short and interpretive
  - it was less grounded than the bucket A credibility notes because the seeded text itself exposed less primary attribution detail
  - still useful as a reminder that this article needs fuller source review before high-confidence use

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - yes
- Notes on verification/review usefulness:
  - API read-back was enough to detect summary-like reframing and source-span weakness
  - this pass was materially noisier to review than A2 or A3 because many claims no longer carried the article's original attribution and framing context cleanly

## Outcome classification
- Overall result:
  - engineering-smoke-only
- Biggest blocker:
  - analytical paragraphs are being flattened into weak proposition-style claims with unstable anchoring and reduced attribution context
- Highest-value next fix:
  - preserve attribution/framing structure when extracting from long analytical passages, especially for "article says", campaign-position contrasts, and voter-example sections
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `North Carolina’s U.S. Senate race makes the problem especially clear.`
  - `The benefits of tax cuts are being eroded by inflation.`
  - `Michael Whatley is promoting Trump's tax overhaul as a working-families tax cut.`
  - `One voter cannot afford health insurance.`
  - `The election is framed as a contest between tax relief and affordability pressure rather than a settled judgment on one economic narrative.`
- Diagnostics snapshot:
  - `{ "chunk_count": 12, "claim_count": 15, "dropped_claim_items": 0, "dropped_evidence_items": 0, "summary": "Extracted 15 claim(s) from 12 chunk(s)." }`
- Credibility note excerpt:
  - `AP News article summarizing how Trump's tax-cut agenda and persistent inflation are shaping voter views ahead of the midterms, with North Carolina's Senate race used as a focal example. Based on the excerpt, it appears to be a reported political/economic analysis piece rather than a primary document.`
- Other evidence / curl outputs:
  - create case: `201`
  - create document: `201`
  - prepare: `200`
  - extract-claims: `200`
  - list case claims: `200`
  - credibility POST/GET: `200`
  - prepared chunk example (`p6`): `The article notes that some Republican claims were exaggerated. For example, the law does not fully eliminate federal taxes on overtime.`
