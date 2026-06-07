# SourceTrace docs boundary review

Status: draft SSOT for public-vs-local documentation boundary
Date: 2026-06-07
Scope: classify current documentation and propose a simpler structure for a future public GitHub repository

## Decision

Use a simple two-zone model:
- `docs/` = tracked public documentation meant for repository readers
- `notes/` = local-only/process-oriented working material that should not define the public docs surface

The target structure should be:
- keep `docs/` as the public repo-visible docs root
- keep `docs/` flat, without public subfolders
- narrow `docs/` to canonical product, architecture, setup, and selected stable background docs
- use `notes/` as the default home for process/history-heavy artifacts that should stay available locally without shaping the public docs experience

This means both of these should be treated as cleanup targets:
- the current `docs/plans/` directory is too mixed for a public-ready repo shape
- the current foldered docs layout is more complex than needed for the intended public surface

## Confirmed current state

### Current tracked docs tree
Confirmed in repo:
- `docs/architecture/architecture-ssot.md`
- `docs/research/research-ledger.md`
- `docs/plans/execution-blueprint-v0.md`
- `docs/plans/local-launcher-readiness-ssot.md`
- `docs/plans/2026-06-05-verification-control-plane-ssot.md`
- `docs/plans/2026-05-26-source-trace-research-to-backlog-plan.md`
- many additional `docs/plans/*.md` files that are checkpoint, observation, debug-ledger, continuity-pack example, or campaign-history shaped

### Confirmed existing local-only home
Confirmed in repo before this decision pass:
- `notes/` already existed as a natural non-public-facing home
- the user explicitly does **not** want an index-style `notes/README.md`

Interpretation:
- `notes/` should stay lightweight and local-only
- it does not need a tracked README/index file
- this is still a simpler and more consistent choice than introducing a brand-new local-only directory

### Confirmed role mismatch
Confirmed from file contents:
- `docs/architecture/architecture-ssot.md` is canonical product/architecture material
- `docs/plans/execution-blueprint-v0.md` is a durable implementation-facing bridge doc, but still uses planning language
- `docs/research/research-ledger.md` is useful background, but it is long-lived research accumulation rather than primary public product documentation
- many files under `docs/plans/` are not canonical docs; they are execution artifacts, handoff notes, experiment observations, campaign checkpoints, or debug ledgers

### Confirmed public-surface problem
A public reader currently sees one mixed `docs/` tree where canonical docs and execution residue coexist.
That makes it hard to answer:
- what is the current product truth,
- what is implementation guidance,
- what is historical process material,
- what should be read first.

The current nested folder layout also adds navigation complexity without giving enough public-facing value in return.

## Recommended boundary model

### Zone 1 — public docs in flat `docs/`
This zone should contain only repo-visible documentation that is reasonable to present to outside readers.

Recommended classes:
- product / architecture SSOT
- developer-facing setup or usage docs that are stable enough to expose
- selected implementation overview docs that explain the system shape
- selected background research summaries only if they still help a repo reader understand the project

Rule:
- public docs should live directly under `docs/`, not in public subfolders

### Zone 2 — local-only artifacts in `notes/`
This zone should contain process-shaped material that is useful to the owner/operator but should not define the public docs surface.

Recommended classes:
- debug ledgers
- saved-state handoff notes
- campaign logs
- observation notes
- bucket checkpoints
- continuity-pack working examples used mainly as process artifacts
- dated public-readiness working analyses after their decisions are absorbed elsewhere

Recommended structure under `notes/`:
- `notes/process/observations/`
- `notes/process/checkpoints/`
- `notes/process/debug-ledgers/`
- `notes/process/campaign-notes/`
- `notes/process/continuity-pack-artifacts/`

The exact subdirectory split is still do weryfikacji, but `notes/` itself is now the preferred local-only home.

## Classification of the current docs

### Keep in public `docs/` as canonical or near-canonical
Recommended to keep visible and eventually normalize into a flat public docs layout:
- `docs/architecture/architecture-ssot.md` — canonical product and architecture SSOT
- `docs/plans/execution-blueprint-v0.md` — likely keep, but later rename/move into a cleaner flat public docs filename
- `docs/plans/local-launcher-readiness-ssot.md` — keep only if the repo still wants an exposed operator/runtime boundary doc
- `docs/plans/2026-06-05-verification-control-plane-ssot.md` — keep only if verification control plane remains a public-facing part of project understanding
- `docs/plans/2026-05-26-source-trace-research-to-backlog-plan.md` — candidate to keep as background/roadmap bridge, but not as primary docs entry point
- `docs/research/research-ledger.md` — candidate to keep as background research ledger, but not as first-line product documentation

### Keep in repo but de-emphasize from public docs map
These may remain tracked, but should not be promoted as core reading:
- stable but specialized SSOT/checkpoint docs for narrow subsystems
- continuity-pack usage notes or examples that are useful for advanced readers but not for the main docs path

### Move to local-only artifact area
These are the strongest candidates to leave the public docs surface:
- dated observation notes
- bucket checkpoints
- campaign synthesis/runbook/corpus artifacts
- saved-state notes
- debug ledgers
- broken/test continuity-pack examples used as process material
- temporary handoff/checkpoint notes
- dated public-readiness working analyses once their decisions are folded into stable docs

## Recommended target structure

A simpler reader-facing structure should look like this:

```text
docs/
  architecture-ssot.md
  execution-blueprint.md
  local-launcher-readiness.md           # if still worth exposing publicly
  verification-control-plane.md         # if still worth exposing publicly
  research-to-backlog.md                # if still worth exposing publicly
  research-ledger.md                    # optional background, not first-line reading
```

And local-only material should live under:

```text
notes/
  process/
    observations/
    checkpoints/
    debug-ledgers/
    campaign-notes/
    continuity-pack-artifacts/
```

This exact naming is not frozen below `notes/`. The important rule is the boundary plus flat public docs.

## Practical migration rule

When deciding where a document belongs, use this test:

Keep in public flat `docs/` if the file is primarily:
- current truth,
- stable explanation,
- reusable setup guidance,
- public-facing technical context.

Move to `notes/` if the file is primarily:
- a record of one run,
- a checkpoint in a sequence,
- a debug diary,
- a handoff/saved-state note,
- a temporary decision artifact superseded by a stable SSOT.

## What should happen next

### Stage 1 — classify without moving files yet
- freeze a simple list of:
  - public canonical docs,
  - public background docs,
  - local-only artifact docs
- update the root docs map to reference only the public canonical set

### Stage 2 — use `notes/` as the local-only artifact home
- treat `notes/` as the default place for future process artifacts
- teach repo structure and ignore rules how to keep future process artifacts out of the public docs surface

### Stage 3 — flatten and normalize public docs names
- move canonical/background docs that remain public into flat `docs/`
- convert dated or plan-shaped filenames into cleaner stable names
- avoid public subfolders unless a later real scale problem proves they are needed

## Potwierdzone
- the current `docs/` tree is mixed and not yet public-ready as a clean reader-facing documentation surface
- a simple two-zone model is enough: flat public `docs/` plus local-only process artifacts in `notes/`
- `notes/` already exists and is the most natural home for that local-only/process layer
- the current nested docs folders are more complex than needed for the intended public surface
- the main problem is structure and promotion, not lack of documentation

## Do weryfikacji
- the exact `notes/process/...` subdirectory split
- whether `research-ledger.md` should stay public or become local/background-only
- whether `local-launcher-readiness-ssot.md` and `verification-control-plane-ssot.md` are public docs or internal operator docs
- how much dated SSOT naming should be normalized in the first cleanup pass

## Current recommended next execution slice

Do one bounded follow-up:
- rewrite the docs target names into the flat `docs/` shape,
- then move one small first batch of obvious process/history artifacts out of `docs/plans/` into `notes/`.
