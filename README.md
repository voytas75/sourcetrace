# SourceTrace

SourceTrace is an application project for building an evidence-centric OSINT + LLM system, with research, planning, and later implementation kept in one repository.

## Current state
This repository is past the pure research-first phase and now has a bounded contract-first implementation baseline plus a first narrow runtime and delivery path.

Confirmed now:
- product direction is evidence-first and claim-centric
- research, SSOT, and execution blueprint documents are in place
- product package layout exists under `src/sourcetrace/`
- `domain` contracts are implemented
- `application` request/outcome contracts are implemented
- `application` execution seams are implemented
- lower-level retrieval and persistence seams are implemented in `pipeline.interfaces` and `storage.interfaces`
- first in-memory runtime path is implemented for persistence, lexical retrieval, and verification orchestration
- minimal analyst-facing delivery surface is implemented in `web/` as a pure-stdlib WSGI/API + HTML/Markdown baseline
- inspection payloads now include derived evidence summary fields and review/report-entry status hints
- delivery routes now distinguish invalid requests and missing verification/report artifacts explicitly
- the in-memory retrieval/runtime path is hardened for duplicate document selection and thin-path end-to-end coverage
- local verification baseline is `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `123 passed`
- bounded LLM integration is now implemented under `src/sourcetrace/llm/`, with an application extraction runtime seam and local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `157 passed`
- the LLM-backed extraction runtime now supports optional storage-backed claim persistence via `ClaimRepository`, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `158 passed`
- the same LLM-backed extraction runtime now also emits and optionally persists initial `ClaimEvidenceLink` records through the existing `ClaimRepository` seam, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `158 passed`
- initial extraction-side `ClaimEvidenceLink` semantics are now less misleading: they stay at `INSUFFICIENT_EVIDENCE` until verification and include span-aware rationale text, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `158 passed`
- initial extraction-side `ClaimEvidenceLink` metadata is now payload-aware: when the LLM claim payload includes evidence snippet/rationale/score fields, the runtime maps them into the initial link while preserving provisional `INSUFFICIENT_EVIDENCE` semantics, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `158 passed`
- initial extraction-side evidence mapping now supports multi-link payloads: one claim can emit multiple provisional `ClaimEvidenceLink` records with ordered `evidence_rank` and per-item `chunk_id`/snippet/rationale/score metadata, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `158 passed`
- initial extraction-side evidence normalization is now defensive against noisy payloads: invalid evidence entries are ignored, accepted entries keep dense `evidence_rank` ordering, and the runtime falls back to a single provisional link only when no valid evidence item remains, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `160 passed`
- top-level extraction claim normalization is now also defensive: invalid `payload["claims"]` entries are ignored before claim construction, accepted claims keep dense fallback IDs, and evidence links are emitted only for normalized claim items, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `162 passed`
- extraction outcomes now also expose lightweight normalization diagnostics: `dropped_claim_items` and `dropped_evidence_items` report how many payload entries were ignored before mapping, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `163 passed`
- extraction runtime string normalization is now trim-aware: whitespace-only claim/evidence fields are treated as missing, accepted strings are stripped before mapping, and dropped-item diagnostics stay aligned with that normalization, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `164 passed`
- source-span fallback is now slightly refined for single-chunk extraction requests: when normalized claim span fields are blank, the runtime can fall back to the lone request chunk’s `position_reference` instead of `chunk-span:unknown`, while multi-chunk requests keep the previous conservative behavior, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `165 passed`
- extraction runtime normalization helpers are now slightly cleaner internally: repeated trim-aware string lookups were consolidated behind small helper functions without changing claim/evidence filtering, diagnostics, or fallback behavior, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `165 passed`
- the current LLM layer is still intentionally provider-bootstrap-light: SourceTrace-owned task config covers only task routing (`model`, `temperature`, `max_output_tokens`), the repo does not load `.env` itself, and LiteLLM remains only a hidden adapter shape until a separate runtime configuration contract is implemented, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `165 passed`
- a minimal LLM bootstrap contract is now present without breaking provider-neutral seams: `SourceTraceLlmConfig` can declare explicit external env var names through `LlmBootstrapConfig`, while env resolution/loading itself still remains outside the repo-owned runtime, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `168 passed`

## Repository map
- `docs/architecture/architecture-ssot.md` — canonical product and architecture baseline
- `docs/research/research-ledger.md` — rolling research notes and architecture implications
- `docs/plans/execution-blueprint-v0.md` — provisional plan between research and implementation
- `notes/` — working notes
- `src/sourcetrace/` — future application package layout
- `tests/` — package/layout and later unit/integration tests
- `data/` — local working data directories kept mostly out of git

## Working model
The intended workflow is now:
1. gather and review sources when architecture assumptions still change
2. update research ledger
3. patch SSOT and execution blueprint when assumptions change
4. execute bounded contract-first slices for agreed layers
5. only then move into runtime adapters, storage engines, and retrieval implementations

## Near-term focus
- keep repo-facing docs aligned with the delivered post-LLM.x baseline
- decide the next bounded integration slice for the LLM-backed path after the new minimal bootstrap contract: whether to add a runtime resolver for env process inputs, whether `.env` should stay out of repo scope, and how real provider wiring plugs into the hidden LiteLLM path
- keep the MVP architecture small, auditable, and implementation-light until heavier runtime choices are explicit
