# Test-use observation — D2 AP photo gallery Romania World Hat Walk

Based on the controlled real-data campaign pass run through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.

## Session metadata
- Date: 2026-05-23
- Tester: Hermes
- Runtime entrypoint: `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`
- Repo commit: `c975280`
- Notes scope: second weak/noisy-source baseline pass for frozen corpus item D2

## Article / document
- Case ID: `campaign-d2-ap-photo-gallery-romania-hat-walk`
- Document ID: `doc-d2-ap-photo-gallery-romania-hat-walk`
- Source URL: `https://apnews.com/photo-gallery/photos-romania-tips-hat-world-hat-walk-c84ec4558065424c9962981bfab98287`
- Publisher: `AP News`
- Author: `Vadim Ghirda / AP photo editors`
- Title: `Photos: Romania tips its hat to World Hat Walk`
- Published at: `2026-05-11T03:23:37Z`
- Retrieved at: `2026-05-23T15:34:00+02:00`
- Language: `en`

## Input shape
- Article type:
  - weak / noisy / repeated-caption photo gallery
- Raw text length:
  - bounded excerpt, 7 seeded caption-like paragraphs
- Number of prepared chunks:
  - `7`
- Chunking method:
  - `paragraph-v1`
- Chunk notes:
  - the seeded text was intentionally repetitive and low-narrative
  - most paragraphs were near-duplicates describing participants posing in Bucharest during the World Hat Walk
  - this is a good test for whether extraction can avoid over-producing trivial claims from repeated caption text

## Extraction outcome
- `POST /api/documents/<doc-id>/extract-claims` status:
  - `200`
- Claim count:
  - `6`
- `diagnostics.dropped_claim_items`:
  - `0`
- `diagnostics.dropped_evidence_items`:
  - `0`
- Were final persisted claims concise and claim-like?
  - yes
- Did assistant/helpdesk prose appear?
  - no
- Example good claim:
  - `People in Bucharest, Romania, posed Sunday for the World Hat Walk, a worldwide event celebrating hats and headwear.`
- Example bad claim:
  - `A participant poses during the World Hat Walk in Bucharest, Romania, on Sunday, May 10, 2026.`
- Notes on extraction quality:
  - extraction did not melt down into nonsense or duplicate spam
  - instead, it compressed the noisy input into a small number of low-value observational claims
  - this is healthier than over-generation, but still weak for analyst usefulness
  - several claims remained almost trivial restatements of individual photo captions
  - most claims also used `chunk-span:unknown`, suggesting weak anchoring on repetitive caption input
  - the main issue here is usefulness degradation, not semantic corruption

## Normalization behavior
- Did normalized output seem to preserve source meaning?
  - yes
- Did normalization appear to expand into summaries/explanations?
  - no
- Did normalization appear to inject assistant wording?
  - no
- Notes on normalization behavior:
  - no separate normalization surface was exposed; judgment is inferred from persisted claims
  - normalization stayed conservative and did not invent narrative structure
  - however, the result remained low-value because the input itself was mostly repeated captions

## Credibility draft
- `POST /api/documents/<doc-id>/credibility` status:
  - `200`
- Was the credibility note useful?
  - yes
- Main credibility note takeaway:
  - the source is high-reliability AP photojournalism for the observed event itself, but the excerpt is short, the gallery format has limited reporting context, and the `up to 60 cities` scale claim is only attributed to organizers
- Notes on credibility quality:
  - credibility behaved proportionally here
  - unlike D1, this was not a low-reliability source, but the system still recognized that photo-gallery format has limited contextual reporting value
  - it correctly separated directly observed event details from broader organizer-supplied claims

## Verification / review usefulness
- Was verification tested?
  - no
- Was analyst review tested?
  - yes
- Notes on verification/review usefulness:
  - review was easy but not especially valuable
  - the operator could trust the basic event observations more than in D1
  - however, the resulting claims were too banal to be a strong decision-ready artifact
  - this is more of a low-yield input problem than a credibility failure

## Outcome classification
- Overall result:
  - usable-with-caveats
- Biggest blocker:
  - repeated caption input yields mostly trivial observational claims with low downstream usefulness
- Highest-value next fix:
  - add low-yield / repeated-caption heuristics so the system can recognize photo-gallery style input and either collapse it into one compact observation summary or explicitly mark it as low-value for claim extraction
- Keep this article as regression fixture?
  - yes

## Pasteable evidence
- Final persisted claims snapshot:
  - `People in Bucharest, Romania, posed Sunday for the World Hat Walk, a worldwide event celebrating hats and headwear.`
  - `A participant in the World Hat Walk stands by a fountain in Bucharest, Romania, on Sunday, May 10, 2026.`
  - `Participants in the World Hat Walk pose for selfie photographs in Bucharest, Romania, Sunday, May 10, 2026.`
  - `A participant poses during the World Hat Walk in Bucharest, Romania, on Sunday, May 10, 2026.`
- Diagnostics snapshot:
  - `{ "chunk_count": 7, "claim_count": 6, "dropped_claim_items": 0, "dropped_evidence_items": 0, "summary": "Extracted 6 claim(s) from 7 chunk(s)." }`
- Credibility note excerpt:
  - `AP News photo gallery showing participants in Bucharest during the World Hat Walk. The excerpt is descriptive and likely based on AP photography, but it is a curated photo feature with limited contextual reporting and includes at least one organizer-supplied claim that needs independent confirmation.`
- Other evidence / curl outputs:
  - create case: `201`
  - create document: `201`
  - prepare: `200`
  - extract-claims: `200`
  - list case claims: `200`
  - credibility POST/GET: `200`
