# Observation note — A1 Reuters South Africa risks

Based on template: `docs/plans/test-use-observation-template.md`
Campaign corpus source: `docs/plans/2026-05-21-real-data-campaign-corpus-v1.md`

## Session metadata
- Date: 2026-05-21
- Tester: Wojciech Napierała / Hermes-assisted
- Runtime entrypoint: `python -m sourcetrace.local_launcher`
- Repo commit: `cbd29e6`
- Notes scope: first live campaign run for A1 using the current local launcher path

## Article / document
- Case ID: `campaign-a1-reuters-south-africa-risks`
- Document ID: `doc-a1-reuters-south-africa-risks`
- Source URL: `https://www.reuters.com/world/africa/sp-says-it-is-watching-south-africa-coalition-middle-east-conflict-risks-wider-2026-05-13/`
- Publisher: `Reuters` in source URL, but persisted document metadata stayed incomplete because the document was seeded as inline summary text
- Title: `S&P says it is watching South Africa coalition, Middle East conflict risks for wider Africa`
- Published at: `2026-05-13T12:35:41Z` in campaign corpus; persisted document metadata stored `null`
- Retrieved at: `2026-05-21T09:25:17.060999`
- Language: `en` in campaign corpus; persisted document metadata stored `null`

## Input shape
- Article type:
  - factual brief
- Raw text length:
  - approximately 3983 chars after inline summary seeding
- Number of prepared chunks:
  - 16
- Chunking method:
  - `paragraph-v1`
- Chunk notes:
  - this run used a web-extracted Reuters summary artifact, not the raw original Reuters HTML/article body
  - chunk 1 was only the generated heading, while most substantive content started in later chunks
  - despite 16 prepared chunks, extracted claims anchored only to `chunk-1`, which is operationally suspicious

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
  - `ready`
- Claim count:
  - 19
- `diagnostics.dropped_claim_items`:
  - 0
- `diagnostics.dropped_evidence_items`:
  - 0
- Were final persisted claims concise and claim-like?
  - mixed
- Did assistant/helpdesk prose appear?
  - some claims
- Example good claim:
  - `More than three-quarters of rated African sovereigns are net importers of fuel and fertilizer.`
- Example bad claim:
  - `This means the coalition government is facing even more strain, as the economy is already under pressure from higher oil prices and increased borrowing costs.`
- Notes on extraction quality:
  - core claims were mostly short and readable
  - several claims were clearly summary-style rewrites rather than direct claim extraction
  - one material factual distortion appeared: `Countries that import more than they export` replaced the source concept `net importers of fuel and fertilizer`
  - all persisted claims reported `source_span_reference: chunk-span:unknown`
  - all extracted claims were linked to `doc-a1...:chunk-1`, even though the substantive evidence lived across many later chunks; this looks like an evidence-link/runtime issue, not just wording quality

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - mixed
- Did normalization appear to expand into summaries/explanations?
  - slightly
- Did normalization appear to inject assistant wording?
  - yes
- Notes on normalization behavior:
  - compared with the earlier BBC example, the drift was milder, but still visible
  - the system sometimes converted source-backed statements into explanatory paraphrases (`This means...`, `is watching to see if...`)
  - the output stayed readable, but it was not fully source-tight
  - the strongest issue in this run was not only wording drift, but evidence anchoring collapsing to one non-substantive chunk

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `ready`
- Was the credibility note useful?
  - useful
- Main credibility note takeaway:
  - the system correctly recognized this input as a secondary prepared summary of a Reuters report rather than a fully evidenced original article ingest
- Notes on credibility quality:
  - the note was materially useful because it surfaced the real weakness of this run: incomplete metadata and summary-based seeding
  - strengths/concerns were specific rather than generic
  - the output explicitly recommended verification of Reuters attribution and the underlying S&P material
  - this is a good sign for credibility usefulness, but it also reflects that the ingestion path for this run was weaker than the ideal campaign input

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - no
- Notes on verification/review usefulness:
  - this run covered case creation, document attach, prepare, extract, persisted claim read-back, and credibility
  - verification and analyst review remain untested in this note

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - extraction/evidence anchoring attached every claim to `chunk-1` with unknown source span, which weakens traceability
- Highest-value next fix:
  - fix claim-to-chunk/source-span grounding so claims anchor to the real originating chunk(s), then retest on the same article class
- Keep this article as regression fixture?
  - yes

## Retest after bounded grounding fix
- Retest date:
  - 2026-05-21
- Runtime used:
  - `python -m sourcetrace.local_launcher`
- Retest case/document:
  - `campaign-a1-reuters-south-africa-risks-retest`
  - `doc-a1-reuters-south-africa-risks-retest`
- Prepare result:
  - `Prepared 12 chunk(s).`
- Extract result:
  - `Extracted 22 claim(s) from 12 chunk(s).`
- What improved:
  - the bounded fix is real at seam level: a focused runtime regression and direct local repro now correctly infer `chunk-2` / `p2` from a unique claim-text match
  - in live retest, at least one claim (`claim-20`) anchored correctly to `chunk-10` with `source_span_reference: p10`
- What did not improve enough:
  - most claims still anchored to `chunk-1`
  - most claims still carried `source_span_reference: chunk-span:unknown`
- Interpretation:
  - the first root cause was real and fixed for exact/unique text matches
  - however, live A1 still shows a second-order issue: many extracted claims are paraphrased enough that exact-text chunk inference does not fire, so they still fall back to the first chunk
  - this means the system is better than before, but not yet good enough to call grounding solved on realistic summary-style outputs
- Updated blocker statement:
  - grounding improved from `always wrong` to `sometimes recoverable`, but traceability is still too weak for trusted analytical use
- Updated highest-value next fix:
  - add a second bounded grounding heuristic for paraphrased claims, likely based on overlap/similarity against candidate chunks, while staying conservative on ambiguous matches

## Pasteable evidence
- Final persisted claims snapshot:
  - `S&P Global Ratings says South Africa faces a “double blow” from domestic political uncertainty and external headwinds from the Middle East conflict.`
  - `More than three-quarters of rated African sovereigns are net importers of fuel and fertilizer.`
  - `This means the coalition government is facing even more strain, as the economy is already under pressure from higher oil prices and increased borrowing costs.`
- Diagnostics snapshot:
  - prepare: `Prepared 16 chunk(s).`
  - extract: `Extracted 19 claim(s) from 16 chunk(s).`
  - extract diagnostics: `dropped_claim_items=0`, `dropped_evidence_items=0`
  - evidence anchoring: all returned claims carried `source_span_reference: chunk-span:unknown`
- Credibility note excerpt:
  - `Secondary summary of a Reuters report about S&P Global Ratings monitoring South Africa coalition stability and Middle East conflict spillovers for African sovereign credit.`
  - `Provided text is an excerpted summary, not the full article.`
  - `Cannot confirm whether wording accurately reflects Reuters or S&P.`
- Other evidence / curl outputs:
  - case create returned `status: ready`
  - document attach returned `has_inline_content: true`
  - persisted document metadata for `publisher`, `published_at`, and `language` remained `null`
