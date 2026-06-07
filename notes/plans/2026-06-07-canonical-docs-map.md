# SourceTrace canonical docs map

Status: draft SSOT for public documentation entrypoints
Date: 2026-06-07
Scope: define the smallest clear set of public-facing documentation for SourceTrace repository readers

## Decision

The public docs map should expose only a small set of canonical docs.

Use this split:
- public canonical docs = the default reading path for repo readers
- public background docs = optional deeper context, not required for first understanding
- `notes/` = local-only/process artifacts, not part of the public docs map

Public target rule:
- the public docs surface should be a flat `docs/` directory without public subfolders

## Public canonical docs

These should be the main docs promoted from `README.md`.

### Current source files
1. `docs/architecture/architecture-ssot.md`
   - role: canonical product and architecture baseline
   - why it stays: this is the clearest durable product-truth document in the repo
   - target flat name: `docs/architecture-ssot.md`

2. `docs/plans/execution-blueprint-v0.md`
   - role: implementation overview and module-map bridge
   - why it stays: it explains how the repo is structured and how the system is intended to be built
   - target flat name: `docs/execution-blueprint.md`

## Public background docs

These may remain visible, but should not be the first-line entrypoint from `README.md`.

### Current source files
1. `docs/research/research-ledger.md`
   - role: background research context
   - why it is background only: useful for understanding design influences, but too long and too indirect for the primary docs path
   - target flat name: `docs/research-ledger.md`

2. `docs/plans/local-launcher-readiness-ssot.md`
   - role: local runtime/operator boundary
   - why it is background only: useful for advanced readers and operators, but too runtime-specific for the main public docs path
   - target flat name: `docs/local-launcher-readiness.md`

3. `docs/plans/2026-06-05-verification-control-plane-ssot.md`
   - role: verification-focused subsystem SSOT
   - why it is background only: important but too specialized for the smallest public reading path
   - target flat name: `docs/verification-control-plane.md`

4. `docs/plans/2026-05-26-source-trace-research-to-backlog-plan.md`
   - role: research-to-backlog bridge
   - why it is background only: valuable as roadmap context, but not primary product documentation
   - target flat name: `docs/research-to-backlog.md`

## Not part of the public docs map

Do not promote these from `README.md` as primary reading:
- files under `notes/`
- checkpoint notes
- observation notes
- campaign artifacts
- debug ledgers
- saved-state handoff notes
- temporary public-readiness analyses
- continuity-pack working artifacts used mainly as process/history material

They may remain in the repo for now, but they should not define the public reading path.

## Public reading order

Recommended reading order for a new repo reader:
1. `README.md`
2. canonical docs in flat `docs/`
3. optional background docs as needed

## README rule

`README.md` should link only to:
- public canonical docs directly
- optional background docs as a clearly separate secondary section

It should not present process/history-heavy plan artifacts as equal peers to the canonical docs.

## Potwierdzone
- the repo already has enough material for a small public docs path
- the problem is overexposure of mixed artifacts, not lack of documentation
- the smallest stable canonical set is currently: architecture SSOT + execution blueprint
- `notes/` is now the preferred local-only home for process artifacts
- flat `docs/` is the preferred public target shape

## Do weryfikacji
- whether `research-ledger.md` should stay public long-term or become local/background-only
- whether runtime/operator SSOT docs should stay public once cleaner implementation docs exist
- whether all background docs should be renamed in the first move or only the canonical pair first

## Current recommended next execution slice

Move the canonical pair first into the flat `docs/` shape, then update `README.md` links to match before moving any process/history artifacts into `notes/`.
