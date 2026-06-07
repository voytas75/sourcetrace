# SourceTrace public-readiness analysis

Status: draft analysis for the next publication phase
Date: 2026-06-06
Scope: assess what still blocks or weakens a future switch from private GitHub repo to a public-facing repository

## Decision

SourceTrace is **not yet public-ready**.

The repo is already in a good **private-publication baseline** state:
- clean repo hygiene,
- working README baseline,
- LICENSE / CHANGELOG / CONTRIBUTING present,
- green core GitHub workflows on `main`,
- no open Dependabot or vulnerability alerts,
- sane repository settings.

But it is **not yet ready for public exposure** because the current tracked surfaces still describe the project as:
- not a finished public product,
- private-development / owner-operated,
- partially local-only and operator-facing,
- only partly verified for broader LLM-backed flows.

So the real decision is:
- **do not flip to public yet**,
- first do one bounded public-readiness pass over messaging, docs boundaries, and contribution posture.

## Confirmed current state

### Repo/platform baseline
Confirmed live on GitHub:
- repo is private,
- default branch is `main`,
- issues are on,
- wiki is off,
- squash merge is on,
- merge commit and rebase merge are off,
- topics are set,
- latest `CI Smoke` and `Tests` runs on `main` are green,
- open Dependabot alerts: `0`,
- open vulnerability alerts: `0`.

### Repository-facing files present
Confirmed in repo root:
- `README.md`
- `LICENSE`
- `CHANGELOG.md`
- `CONTRIBUTING.md`

### Current public-surface blockers in tracked docs
Confirmed in tracked files:

#### `README.md`
Public-readiness blockers or caution flags still present:
- "not a finished public product"
- "not a hosted SaaS service"
- "this repo is being prepared for private GitHub publication; it is still developer/operator-facing rather than public-polished"
- explicit caution that broader extraction / normalization / credibility behavior should be treated as local-runtime dependent unless re-verified live
- explicit note that some docs under `docs/plans/` are stable anchors while process-shaped notes stay local-only

Interpretation:
- this is honest and correct for a private repo,
- but it is not the framing wanted on a public-facing landing page.

#### `CONTRIBUTING.md`
Current stance says:
- "SourceTrace is not open to broad public contribution yet"
- "default mode: private development"
- issues / plans / research notes may exist only locally and may not appear in the remote repo

Interpretation:
- acceptable for a private repo,
- not aligned with a normal public-repo expectation unless intentionally keeping the project in a read-only / owner-driven state.

#### `CHANGELOG.md`
Current wording still centers private publication:
- "prepared the repository for private GitHub publication"

Interpretation:
- harmless internally,
- but should be reframed once public-readiness work starts.

### Documentation-boundary risk
Confirmed from repo contents:
- many tracked files still live under `docs/plans/`
- several of them contain working-language markers such as `do weryfikacji`
- several contain research / execution / checkpoint wording rather than stable reader-facing product docs

Interpretation:
- not automatically wrong,
- but public readers will treat tracked docs as intentional public documentation,
- so the current docs tree is still mixed: some files are SSOT-worthy, some are process/history-heavy.

## Main gaps before going public

### 1. Public landing-page framing is not finished
The current README is truthful, but still optimized for:
- private publication,
- operator/developer readers,
- internal honesty about incomplete runtime boundaries.

Before public switch, README should answer more clearly:
- what SourceTrace is,
- who it is for,
- what works today,
- what is explicitly experimental,
- how an outside reader should evaluate the repo.

### 2. Contribution posture is unresolved
There is no contradiction yet, but there is an unresolved product decision:
- public repo with open contribution posture,
- or public repo but owner-operated / limited-contribution.

That decision should be made explicitly and then reflected in `CONTRIBUTING.md` and repo settings.

### 3. Public docs boundary is still mixed
`docs/plans/` currently contains both:
- stable design / SSOT material,
- process-heavy notes, checkpoints, debug ledgers, and research-run artifacts.

For a public repo, this increases reader confusion:
- unclear what is canonical product documentation,
- unclear what is historical process residue,
- unclear which documents should be trusted as current truth.

### 4. Broader live-product claims remain only partially verified
Tracked docs still correctly warn that some LLM-backed HTTP/runtime paths remain only partly verified or environment-dependent.

That is not a blocker to publishing code publicly by itself.
But it **is** a blocker to stronger public claims like:
- ready-to-run product,
- reliable end-to-end analyst workflow,
- externally reproducible provider-backed behavior.

So public messaging must stay bounded unless a live verification pass broadens the evidence.

## Recommended public-readiness stages

## Stage 1 — public-surface messaging cleanup
Purpose:
- make root GitHub surfaces coherent for an external reader without overstating maturity.

Primary files:
- `README.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`

Bounded changes:
- remove private-publication wording,
- replace developer/operator-only framing with public-but-bounded framing,
- decide whether contribution stance is:
  - owner-operated / limited contributions, or
  - open to external PRs/issues,
- keep capability claims strictly aligned to verified behavior.

Done condition:
- a public visitor can read root docs and understand the project without seeing stale private-repo language.

## Stage 2 — docs boundary cleanup
Purpose:
- separate canonical public docs from process/history-heavy notes.

Primary paths:
- `docs/architecture/`
- `docs/plans/`
- possibly a new public-facing docs subset such as `docs/overview/` or tighter SSOT-only map

Bounded changes:
- classify tracked docs into:
  - canonical public docs,
  - retained internal-history docs,
  - candidates to move, summarize, or de-emphasize,
- narrow README documentation map to the canonical public subset,
- avoid deleting useful history unless there is a clear replacement.

Done condition:
- public readers can distinguish current truth from historical process notes.

## Stage 3 — public-claim verification pass
Purpose:
- verify what can be claimed safely on a public landing page.

Suggested focus:
- local bootstrap path,
- core smoke path,
- one realistic repo-owned LLM-backed path if credentials/runtime are available,
- docs consistency between README and verified behavior.

Done condition:
- public-facing claims map cleanly to verified runtime evidence.

## Stage 4 — optional public-repo posture hardening
Purpose:
- finalize how the repo should behave once public.

Possible slices:
- issue templates / labels review,
- contribution expectations,
- security policy / support policy,
- branch protection if repo becomes public and platform features become available.

Done condition:
- repo policy matches intended public operating model.

## Risks and cautions

### Risk: premature public flip with truthful-but-confusing docs
If the repo becomes public before docs cleanup:
- outside readers will see mixed signals,
- the project may look more chaotic or less intentional than it really is,
- process notes may be mistaken for product docs.

### Risk: overstating maturity during cleanup
A public-readiness rewrite should not turn into marketing.
The safe target is:
- public, honest, bounded, inspectable,
- not polished fiction.

### Risk: accidental scope drift into product work
Public-readiness does **not** require broad runtime changes.
The first pass should stay mostly in docs / repo-surface territory unless verification reveals a must-fix contradiction.

## Recommended next slice

**Next slice:** do a bounded public-surface rewrite of:
- `README.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`

with this rule:
- make them public-facing,
- keep them honest,
- do not expand capability claims beyond what is already verified.

## Summary verdict

### Potwierdzone
- private-publication baseline is solid,
- repo hygiene and GitHub settings are in good shape,
- public-readiness blockers are mostly **messaging and docs-boundary blockers**, not repo-security blockers.

### Do weryfikacji
- final contribution stance for a future public repo,
- how much of `docs/plans/` should remain prominently exposed as canonical docs,
- whether broader LLM-backed flows should be re-verified before public messaging is strengthened.

### Final recommendation
Do **not** switch to public yet.
First close one bounded docs-facing public-readiness slice, then re-evaluate.