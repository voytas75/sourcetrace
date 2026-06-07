# Test-use observation template

Use this template while test-driving Sourcetrace through `python -m sourcetrace.local_launcher`.

## Session metadata
- Date:
- Tester:
- Runtime entrypoint:
- Repo commit:
- Notes scope:

## Article / document
- Case ID:
- Document ID:
- Source URL:
- Publisher:
- Title:
- Published at:
- Retrieved at:
- Language:

## Input shape
- Article type:
  - factual brief / longer analysis / quotes-caveats / other
- Raw text length:
- Number of prepared chunks:
- Chunking method:
- Chunk notes:

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
- Claim count:
- `diagnostics.dropped_claim_items`:
- `diagnostics.dropped_evidence_items`:
- Were final persisted claims concise and claim-like?
  - yes / mixed / no
- Did assistant/helpdesk prose appear?
  - no / some claims / most claims / all claims
- Example good claim:
- Example bad claim:
- Notes on extraction quality:

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - yes / mixed / no / unclear
- Did normalization appear to expand into summaries/explanations?
  - no / slightly / heavily
- Did normalization appear to inject assistant wording?
  - no / yes
- Notes on normalization behavior:

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
- Was the credibility note useful?
  - useful / generic / misleading / not tested
- Main credibility note takeaway:
- Notes on credibility quality:

## Verification / review usefulness
- Was verification tested?
  - yes / no
- Was analyst review tested?
  - yes / no
- Notes on verification/review usefulness:

## Outcome classification
- Overall result:
  - usable / usable-with-caveats / engineering-smoke-only / failed
- Biggest blocker:
- Highest-value next fix:
- Keep this article as regression fixture?
  - yes / no

## Pasteable evidence
- Final persisted claims snapshot:
- Diagnostics snapshot:
- Credibility note excerpt:
- Other evidence / curl outputs:
