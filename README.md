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
- a minimal LLM bootstrap contract is now present without breaking provider-neutral seams: `SourceTraceLlmConfig` can declare explicit external env var names through `LlmBootstrapConfig`, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `168 passed`
- that same LLM boundary now also includes a small process-env bootstrap resolver: `resolve_llm_bootstrap_config(...)` reads only the declared env var names, fails fast on missing/blank values, still does not load `.env`, and keeps provider details outside request/application surfaces, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `173 passed`
- the same LiteLLM adapter boundary now also wires those resolved bootstrap inputs into provider-facing callables: `build_litellm_completion_caller(...)`, `build_litellm_text_generator(...)`, and `build_litellm_structured_generator(...)` inject `api_key`/`base_url` without widening request or application surfaces, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `176 passed`
- the LLM layer now also exposes a small runtime assembly entrypoint: `build_llm_runtime(...)` resolves env bootstrap, binds the LiteLLM structured generator, and assembles a claim-extraction-ready runtime bundle without adding `.env` loading or provider leakage to higher layers, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `178 passed`
- that same runtime assembly now depends only on the public `build_claim_extraction_gateway(...)` factory rather than reaching into a private extraction symbol, keeping the composition boundary explicit without changing behavior or widening surfaces
- a minimal local front door now exists for the delivery surface: `python -m sourcetrace.web` (and installed console script `sourcetrace-web`) starts a pure-stdlib WSGI server against the in-memory delivery/runtime path for thin local end-to-end smoke runs
- the repo now also declares a minimal `pyproject.toml` so local setup can be standardized with `uv sync --dev`, `uv run pytest -q`, and `uv run python -m sourcetrace.web`

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

## Local environment bootstrap
Recommended local developer bootstrap now:
1. `uv sync --dev`
2. `uv run pytest -q`
3. `uv run python -m sourcetrace.web`

Notes:
- the repo now declares a minimal `pyproject.toml` and uses `src/` package layout
- `.env` is still not loaded by the repo; any required external secrets must come from the process environment only
- the local web run is still a thin in-memory/dev path, not a production server shape

## Local smoke flow
1. Start the local server:
   - `uv run python -m sourcetrace.web`
2. In another terminal, submit a minimal verification request:
   - `curl -X POST http://127.0.0.1:8000/api/verify \
     -H 'Content-Type: application/json' \
     -d '{
       "claim": {
         "claim_id": "claim-1",
         "case_id": "case-1",
         "document_id": "doc-1",
         "chunk_id": "chunk-1",
         "exact_text": "The bridge reopened after inspection.",
         "source_span_reference": "p1",
         "system_verdict": "insufficient_evidence",
         "rationale": null
       },
       "requested_k": 2
     }'`
   - Expected: `200 OK` with JSON containing `verification.verdict`
3. Inspect the verification artifact:
   - `curl http://127.0.0.1:8000/api/claims/claim-1/verification`
   - Expected: `200 OK` with JSON containing `evidence_links` and `evidence_summary`
4. Record a minimal analyst review so the case report surface has reviewed content:
   - `curl -X POST http://127.0.0.1:8000/api/reviews \
     -H 'Content-Type: application/json' \
     -d '{
       "claim_id": "claim-1",
       "case_id": "case-1",
       "human_review_status": "reviewed_accept",
       "analyst_disposition": "confirmed_support",
       "final_verdict": "support",
       "review_notes": "Accepted for report."
     }'`
   - Expected: `200 OK` with JSON containing the persisted review payload
5. Export the markdown report:
   - `curl http://127.0.0.1:8000/api/reports/case-1.md`
   - Expected: `200 OK` with `Content-Type: text/markdown; charset=utf-8`

## Minimal failure cases
- Missing verification artifact:
  - `GET /api/claims/missing-claim/verification`
  - Expected: `404 Not Found` with `{"error": "verification_not_found", "status": "missing"}`
- Missing report artifact:
  - `GET /api/reports/missing-case.json`
  - Expected: `404 Not Found` with `{"error": "report_not_found", "status": "missing"}`
- Invalid review request:
  - `POST /api/reviews` with an incomplete payload
  - Expected: `400 Bad Request` with `status: invalid_request`

## Near-term focus
- keep repo-facing docs aligned with the delivered post-LLM.x baseline
- decide the next bounded integration slice for the LLM-backed path after the runtime composition cleanup: whether to broaden the assembled runtime to additional task gateways without widening request/application surfaces or pulling `.env` loading into the repo
- keep the MVP architecture small, auditable, and implementation-light until heavier runtime choices are explicit
