# SourceTrace Real-Data Test-Use SSOT

Status: active execution SSOT
Scope: canonical plan for the first controlled test-use phase on real articles/documents
Last verified: 2026-05-21

## Purpose
This document is the current SSOT for moving SourceTrace from local bounded smoke validation into a controlled real-data test-use phase.

The goal is not to declare analyst readiness yet.
The goal is to:
- exercise the current local launcher on real documents,
- capture quality failures and workflow friction with evidence,
- classify what is already usable versus what is still engineering-smoke-only,
- turn real observations into the next bounded fixes.

## Readiness verdict
- **Ready now for controlled real-data test use:** yes
- **Ready now for normal analyst usage without strong caution:** not yet

Interpretation:
- the repo is ready for a bounded observation pass on real documents,
- it is not yet ready to treat extraction, normalization, or credibility output as broadly trustworthy final analyst output,
- findings from this phase should be treated as product-quality evidence, not as edge-case bug reports only.

## Confirmed current baseline
- Repo: `/home/voytas/projects/sourcetrace`
- Branch: `main`
- Working tree was clean at review time.
- Local regression baseline is green:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ./.venv/bin/python -m pytest -q`
  - result: `262 passed in 0.47s`
- The repo-owned local runtime entrypoint exists:
  - `python -m sourcetrace.local_launcher`
- The thin local web entrypoint also exists, but it is **not** the preferred path for real-data test use when LLM-backed behavior matters:
  - `python -m sourcetrace.web`
- Reusable smoke exists:
  - `python -m sourcetrace.smoke_flow`
- CI smoke exists:
  - `.github/workflows/ci-smoke.yml`
- Test-use note-taking artifacts already exist:
  - `docs/plans/test-use-observation-template.md`
  - `docs/plans/test-use-observation-example-bbc.md`
- Continuity-pack guidance for decision checkpoints now exists:
  - `docs/plans/2026-05-23-continuity-pack-usage-note.md`

## Important known limitation
The current main product-quality risk is still extraction/normalization quality on real articles.

Confirmed now:
- the project can run the bounded local flow end-to-end,
- but persisted claim text can still degrade into assistant-style or over-explanatory prose on some real analytical articles,
- the current fallback and cleanup rules improved this path but have not closed it fully.

Operational consequence:
- treat extraction quality,
- normalization quality,
- and credibility usefulness
as separate observation categories during this phase.

Do not collapse them into one generic verdict like "LLM quality".

## Phase objective
Produce a first evidence-backed quality map for SourceTrace over real documents.

This phase should answer:
1. Which article/document shapes already work acceptably?
2. Which shapes fail predictably?
3. Where the main degradation enters:
   - prepare/chunking,
   - extraction,
   - normalization,
   - credibility draft,
   - verification/review workflow,
   - operator UX/readability.
4. Whether the current system is already:
   - `usable`,
   - `usable-with-caveats`,
   - `engineering-smoke-only`
   for each tested document class.

## Controlled test-use rules
1. Use the repo-owned launcher for real-data passes:
   - `python -m sourcetrace.local_launcher`
   - not the thin `sourcetrace.web` path when real LLM-backed behavior is the subject.
2. Keep the phase bounded and evidence-first.
3. Record every notable problem with a concrete example.
4. Separate product-quality observations from runtime/setup failures.
5. Prefer a small curated set of real documents over broad uncontrolled testing.
6. Keep this phase local and operator-driven; do not frame it as production validation.

## Test dataset shape for the first pass
Use **10 documents total** in the first campaign.

### Bucket A — straightforward factual briefs (3)
Goal: establish best-case baseline.

Pick documents that are:
- short,
- factual,
- low-ambiguity,
- light on quotes and caveats,
- close to classic news-brief structure.

Questions:
- are extracted claims concise and faithful?
- is normalization still conservative on already-good text?
- are credibility notes at least non-harmful?

### Bucket B — longer analytical articles (3)
Goal: pressure-test the current extraction/normalization seam.

Pick documents that are:
- longer,
- explanatory,
- multi-paragraph,
- richer in context and interpretation.

Questions:
- do claims stay short and traceable,
- or drift into assistant/explainer prose?
- does normalization preserve source meaning,
- or over-smooth into summaries/explanations?

### Bucket C — quotes / caveats / mixed certainty (2)
Goal: test preservation of attribution and uncertainty.

Pick documents that include:
- explicit quotes,
- warnings,
- uncertainty bands,
- caveats,
- mixed or competing interpretations.

Questions:
- does the system preserve attribution markers,
- caveats,
- and uncertainty cues?
- does it flatten nuanced claims into overconfident statements?

### Bucket D — weak / secondary / noisy source shapes (2)
Goal: test credibility usefulness and weak-source handling.

Pick documents that are closer to:
- repost/aggregation,
- unattributed note,
- secondary summary,
- scraped or weakly contextualized source text.

Questions:
- do credibility notes become appropriately cautious?
- does the system expose the weakness clearly enough for an operator?
- does extraction still produce something useful or mostly noise?

## Execution plan

### Task 1 — Freeze the test set and metadata
Objective: choose the initial 10 documents and make the pass reproducible.

Steps:
1. Select 10 real documents using the 4 buckets above.
2. For each document, record:
   - source URL,
   - publisher,
   - title,
   - published_at,
   - retrieved_at,
   - language,
   - article type bucket.
3. Use stable `case_id` / `document_id` naming for the campaign.
4. Keep a lightweight list of the chosen corpus in one campaign note.

Done when:
- the first-pass corpus is fixed,
- each item has enough metadata to reproduce the test,
- the bucket distribution is visible.

### Task 2 — Run document-by-document observation passes
Objective: collect one structured observation note per document.

Steps for each document:
1. Start the launcher:
   - `python -m sourcetrace.local_launcher`
2. Seed/create the document in the same running process.
3. Run:
   - prepare
   - extract-claims
   - credibility
   - relevant read-back endpoints
4. Inspect:
   - route response,
   - persisted claims,
   - chunks,
   - credibility output,
   - HTML/resource surfaces when useful.
5. Save the observation using:
   - `docs/plans/test-use-observation-template.md`

Done when:
- every tested document has one observation note with evidence.

### Task 3 — Classify findings by seam
Objective: avoid one undifferentiated bug pile.

Classify every finding as one of:
- prepare/chunking issue,
- extraction quality issue,
- normalization quality issue,
- credibility quality issue,
- verification/review usefulness gap,
- API/HTML delivery contract issue,
- runtime/bootstrap/operator issue.

For each finding, capture:
- severity: low / medium / high
- repeatability: one-off / recurring / likely systematic
- evidence snippet
- recommended next fix

Done when:
- findings can be grouped into bounded engineering slices instead of free-form notes.

### Task 4 — Produce first campaign verdict
Objective: convert raw notes into a product-quality picture.

Summarize across the 10 documents:
- what already works,
- what works only with caveats,
- what is still engineering-smoke-only,
- which document classes are most risky,
- what the next 1–3 highest-value fixes are.

Done when:
- SourceTrace has a first evidence-backed real-data quality verdict,
- the next bounded improvement slice can be chosen from observed reality rather than assumption.

## Observation format
Use one note per document.

Canonical template:
- `docs/plans/test-use-observation-template.md`

Minimum required fields per note:
- session metadata,
- article/document metadata,
- input shape,
- extraction outcome,
- normalization behavior,
- credibility draft quality,
- verification/review usefulness,
- outcome classification,
- pasteable evidence.

## Evidence standard
A finding counts as strong enough for follow-up only if it includes at least one of:
- raw source paragraph,
- prepared chunk snippet,
- final persisted `exact_text`,
- route diagnostics snapshot,
- credibility note excerpt,
- HTTP/API payload excerpt,
- HTML/UI snapshot text.

Without evidence, keep the note as weak observation only.

## Current classification scale
Use this exact classification per tested document:
- `usable`
- `usable-with-caveats`
- `engineering-smoke-only`
- `failed`

Interpretation:
- `usable` = acceptable behavior for that document shape under current constraints
- `usable-with-caveats` = useful but with clear caution areas
- `engineering-smoke-only` = demonstrates system plumbing more than analyst usefulness
- `failed` = not operationally useful for that test item

## Exit criteria for this phase
This first real-data phase is complete when:
- 10 real documents have been tested,
- every document has a structured observation note,
- findings are grouped by seam,
- at least one repeated/high-confidence failure mode is identified,
- a next bounded engineering slice can be chosen from observed evidence.

## Not in scope
- declaring production readiness,
- scaling to broad corpus ingestion,
- introducing new storage/backend architecture during the same pass,
- changing the product boundary based only on one anecdotal result,
- treating credibility draft output as a final trust signal.

## Document sync rule
This file is now the canonical SSOT for the real-data test-use phase.

Repo-facing alignment:
- `README.md` already contains the operator-facing checklist and observation-template pointers for this phase.
- `docs/architecture/architecture-ssot.md` should continue to describe product direction and current limitations, not replace this execution SSOT.
- `docs/plans/execution-blueprint-v0.md` should be patched to point at this phase as the current recommended next operational step.

## Current recommended next step
Run the first 10-document controlled campaign through `python -m sourcetrace.local_launcher`, capture one observation note per document, and use the resulting evidence to choose the next bounded quality slice.
