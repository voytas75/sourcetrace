# SourceTrace

SourceTrace is an application project for building an evidence-centric OSINT + LLM system, with research, planning, and later implementation kept in one repository.

## Current state
This repository is in the research-first architecture phase.

Confirmed now:
- product direction is evidence-first and claim-centric
- research, SSOT, and execution blueprint documents are in place
- product package layout exists under `src/sourcetrace/`
- implementation has not started yet

## Repository map
- `docs/architecture/architecture-ssot.md` — canonical product and architecture baseline
- `docs/research/research-ledger.md` — rolling research notes and architecture implications
- `docs/plans/execution-blueprint-v0.md` — provisional plan between research and implementation
- `notes/` — working notes
- `src/sourcetrace/` — future application package layout
- `tests/` — package/layout and later unit/integration tests
- `data/` — local working data directories kept mostly out of git

## Working model
The intended workflow is:
1. gather and review sources
2. update research ledger
3. patch SSOT and execution blueprint when assumptions change
4. freeze an implementation-ready plan later
5. only then start bounded implementation slices

## Near-term focus
- continue review of papers and thematic sources
- refine provenance, claim validation, and retrieval assumptions
- keep the MVP architecture small and auditable
