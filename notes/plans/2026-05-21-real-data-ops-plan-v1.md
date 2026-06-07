# SourceTrace Real-Data Controlled Test-Use Ops Plan v1

Status: active operational plan
Parent SSOT: `docs/plans/2026-05-21-real-data-test-use-ssot.md`
Corpus ledger: `docs/plans/2026-05-21-real-data-campaign-corpus-v1.md`
Last updated: 2026-05-21

## Purpose
This plan turns the real-data SSOT into an execution sequence with checkpoints, evidence expectations, and explicit Definition of Done.

The target is not broad analyst readiness.
The target is an evidence-backed controlled test-use verdict and a bounded next engineering slice.

## Campaign objective
Produce a first reproducible quality map for SourceTrace on 10 real documents using the local launcher runtime.

## Execution boundary
- Use `python -m sourcetrace.local_launcher` as the runtime under test.
- Treat findings as product-quality evidence, not anecdotal bugs.
- Keep extraction, normalization, credibility, verification, runtime, and UX findings separate.
- Do not upgrade the product claim beyond `controlled test-use` from this campaign alone.

## Campaign phases

### Phase 0 — Freeze and preflight
**Goal:** lock the corpus and confirm baseline before running the campaign.

**Inputs**
- `docs/plans/2026-05-21-real-data-test-use-ssot.md`
- `docs/plans/2026-05-21-real-data-campaign-corpus-v1.md`
- local pytest baseline

**Steps**
1. Freeze the 10-document corpus ledger.
2. Confirm repo state and note any local changes.
3. Confirm local regression baseline with:
   - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ./.venv/bin/python -m pytest -q`
4. Confirm the launcher still starts locally.
5. Confirm the observation template exists.

**Checkpoint output**
- frozen corpus ledger
- current repo/test status
- explicit note of any non-blocking metadata gaps

**Definition of Done**
- corpus is frozen
- baseline test command is known-good or any failure is documented
- operator can start Phase 1 without re-deciding document selection

---

### Phase 1 — Start set observation pass (3 docs)
**Goal:** establish initial signal across three different document shapes.

**Documents**
- A1
- A2
- A3

**Per-document procedure**
1. Create case.
2. Attach/import document.
3. Run `prepare`.
4. Run `extract-claims`.
5. Run `credibility`.
6. Read back claims/chunks/output artifacts.
7. Save one observation note.

**What to inspect**
- chunk count and shape
- whether claims stay short and source-faithful
- whether grounding stays on the right chunk/span or falls back poorly
- whether credibility notes are cautious and useful
- whether operator read-back is understandable

**Checkpoint 1 output**
- 3 observation notes
- first bucket-level pattern summary
- early failure-mode list with seam labels

**Definition of Done**
- all 3 start-set notes exist
- each note has pasteable evidence
- at least one preliminary verdict exists for Bucket A behavior

---

### Phase 2 — Caveat / uncertainty pass (2 docs)
**Goal:** test attribution, hedging, and mixed-certainty handling before deeper analysis slices.

**Documents**
- C1
- C2

**Focus questions**
- Are quotes and attribution markers preserved?
- Are forecasts still represented as forecasts?
- Are caveats flattened into stronger claims?
- Does credibility reflect uncertainty rather than restating the article?

**Checkpoint 2 output**
- 2 additional observation notes
- caveat-preservation verdict
- list of repeatable failure modes in attribution/uncertainty handling

**Definition of Done**
- both C-bucket notes exist
- uncertainty handling is classified as acceptable / usable-with-caveats / poor
- any recurring flattening pattern is captured with evidence

---

### Phase 3 — Analytical stress pass (3 docs)
**Goal:** pressure-test extraction/normalization on longer analytical material.

**Documents**
- B1
- B2
- B3

**Focus questions**
- Do claims remain concise and traceable?
- Does normalization preserve meaning rather than summarize?
- Where does analytical drift start: extraction, normalization, or review layer?
- Does evidence linking remain useful on longer context windows?

**Checkpoint 3 output**
- 3 additional observation notes
- analytical drift map
- ranked list of systematic failure modes on longer articles

**Definition of Done**
- all B-bucket notes exist
- dominant analytical failure mode is named and evidenced
- at least one candidate next bounded slice is visible from real evidence

---

### Phase 4 — Weak / noisy source pass (2 docs)
**Goal:** verify weak-source handling and credibility caution behavior.

**Documents**
- D1
- D2

**Focus questions**
- Does the system become appropriately cautious?
- Does extraction degrade gracefully or become noise?
- Can an operator quickly see why the input is weak?
- Are output artifacts still useful or misleading?

**Checkpoint 4 output**
- 2 additional observation notes
- weak-source handling verdict
- guidance on whether D-type inputs should remain in controlled test-use scope

**Definition of Done**
- both D-bucket notes exist
- credibility usefulness on weak/noisy input is classified
- noisy-input failure modes are separated from runtime bugs

---

### Phase 5 — Campaign synthesis
**Goal:** convert raw notes into a product-quality verdict.

**Inputs**
- 10 observation notes
- corpus ledger
- checkpoint summaries

**Steps**
1. Group findings by seam:
   - prepare/chunking
   - extraction
   - normalization
   - credibility
   - verification/review UX
   - runtime/bootstrap
2. Group findings by bucket:
   - A factual
   - B analytical
   - C quotes/caveats
   - D weak/noisy
3. Rank severity and repeatability.
4. Write one final campaign verdict.
5. Name the next 1–3 bounded engineering slices.

**Definition of Done**
- a campaign summary exists
- each bucket has a verdict
- dominant failure modes are ranked
- next engineering work is chosen from observed evidence rather than intuition

## Required evidence per observation note
Each note should include at least:
- source metadata
- route/runtime metadata
- one raw source snippet
- one prepared chunk snippet or chunk reference
- one persisted claim excerpt
- one credibility excerpt when available
- explicit classification of outcome

## Failure mode classification schema
Use these labels consistently:
- `prepare_chunking`
- `extraction_quality`
- `grounding_traceability`
- `normalization_quality`
- `credibility_quality`
- `verification_review_ux`
- `runtime_bootstrap`
- `api_html_contract`

For each finding also record:
- severity: `low` / `medium` / `high`
- repeatability: `one-off` / `recurring` / `likely_systematic`
- bucket(s) affected
- recommended next action

## Checkpoint summary format
For each checkpoint produce a short status block:
- completed documents
- newly observed failure modes
- confirmed stable behavior
- verdict shift if any
- next documents to run

## Campaign-level Definition of Done
The campaign is done when:
- all 10 frozen documents have observation notes
- each bucket has at least one explicit verdict
- dominant failure modes are evidence-backed
- the readiness statement remains bounded to `controlled test-use`
- the next bounded engineering slice is chosen from campaign evidence

## Non-goals
- proving trusted analyst readiness
- expanding scope beyond the frozen corpus during execution
- fixing every issue mid-campaign unless the issue blocks campaign continuation
- turning weak/noisy-source failures into generic product regressions without evidence

## Recommended next action
Run Phase 1 now: A1, A2, A3 and produce Checkpoint 1 before touching the rest of the corpus.
