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
- the current LLM layer is still intentionally provider-bootstrap-light: SourceTrace-owned task config binds task intent to logical profiles, profile config owns concrete routing (`model`, `temperature`, `max_output_tokens`), the repo does not load `.env` itself, and LiteLLM remains only a hidden adapter shape until a separate runtime configuration contract is implemented, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `165 passed`
- a minimal LLM bootstrap contract is now present without breaking provider-neutral seams: `SourceTraceLlmConfig` can declare explicit external env var names through `LlmBootstrapConfig`, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `168 passed`
- that same LLM boundary now also includes a small process-env bootstrap resolver: `resolve_llm_bootstrap_config(...)` reads only the declared env var names, fails fast on missing/blank values, still does not load `.env`, and keeps provider details outside request/application surfaces, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `173 passed`
- the same LiteLLM adapter boundary now also wires those resolved bootstrap inputs into provider-facing callables: `build_litellm_completion_caller(...)`, `build_litellm_text_generator(...)`, and `build_litellm_structured_generator(...)` inject `api_key`/`base_url`/`api_version` without widening request or application surfaces, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `176 passed`
- the LLM layer now also exposes a small runtime assembly entrypoint: `build_llm_runtime(...)` resolves env bootstrap, binds the LiteLLM structured generator, and assembles a claim-extraction-ready runtime bundle without adding `.env` loading or provider leakage to higher layers, with local verification baseline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `178 passed`
- that same runtime assembly now depends only on the public `build_claim_extraction_gateway(...)` factory rather than reaching into a private extraction symbol, keeping the composition boundary explicit without changing behavior or widening surfaces
- that same runtime assembly now also exposes a text-generation-backed `credibility_draft` gateway for the existing `credibility_draft` task alias, still resolving bootstrap from process env only and still keeping provider details hidden behind the local LiteLLM adapter boundary
- that `credibility_draft` gateway is now also consumable from the existing application credibility seam, so an assessment callable can draft advisory notes without changing the request/outcome contract or leaking provider details upward
- the application layer now exposes `build_llm_credibility_assessor(...)`, a public helper that binds the `credibility_draft` gateway into `CredibilityAssessmentOutcome` while keeping generated text in advisory notes and leaving credibility bands/provenance at `unknown`
- that same runtime assembly now also exposes a text-generation-backed `claim_normalization` gateway for the existing `claim_normalization` task alias, using the same env-resolved edge injection path and keeping provider details out of higher layers
- the application extraction runtime can now optionally consume that `claim_normalization` gateway to normalize extracted `exact_text` before claim records are materialized, while preserving the previous fallback behavior when no normalizer is wired
- a minimal local front door now exists for the delivery surface: `python -m sourcetrace.web` (and installed console script `sourcetrace-web`) starts a pure-stdlib WSGI server against the in-memory delivery/runtime path for thin local end-to-end smoke runs
- a repo-owned local launcher now also exists: `python -m sourcetrace.local_launcher` (and installed console script `sourcetrace-local`) loads `src/sourcetrace/runtime_config.py`, builds `build_llm_runtime(...)`, and wires the `credibility_draft` gateway into the local web delivery path
- the runtime-config file `src/sourcetrace/runtime_config.py` is now the default place to set SourceTrace-owned task models for `claim_extraction`, `claim_normalization`, and `credibility_draft`
- the local root route `GET /` now returns a small HTML landing page listing the available smoke-test routes instead of the previous `{"error": "not_found"}` JSON payload
- the local web delivery path can now optionally compose that credibility helper through `create_default_delivery(..., credibility_draft=...)` and expose it via `POST /api/documents/{document_id}/credibility` for WSGI smoke coverage, without adding `.env` loading or provider fields to web requests
- current local verification baseline is `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` -> `246 passed`
- the repo-owned launcher `python -m sourcetrace.local_launcher` is now live-smoke verified against the current Azure/OpenAI-backed environment: local start, health/runtime probes, document prepare, claim extraction, persisted case claims, credibility draft, and HTML case view all complete successfully when the launcher process inherits the required `SOURCETRACE_LLM_*` / `AZURE_OPENAI_*` env from shell init
- current live smoke confirmed that extraction preserves attribution-bearing claim text on a simple quoted/caveated note (`The minister said ...`, `A watchdog said ...`) and that the same claims appear consistently in both `GET /api/cases/{case_id}/claims` and `GET /cases/{case_id}` HTML
- current live smoke also confirmed that advisory credibility output reaches `POST /api/documents/{document_id}/credibility` on the real provider path, and live markdown/prose responses are now condensed more readably into compact `Summary` / `Strengths` / `Concerns` notes instead of always surfacing as a long raw draft block
- minimal inline case/document ingest is now less hostile for product-level smoke runs: `POST /api/cases` can auto-generate `case_id`, `POST /api/cases/{case_id}/documents` can accept inline `title` + `content` and auto-fill `document_id` / `source_type` / `retrieved_at` / `content_hash`, and `POST /api/documents/{document_id}/prepare` now re-surfaces existing prepared chunks instead of returning an unexplained empty success for already-prepared inline documents
- current live smoke also confirmed that credibility assessment now consumes prepared inline document text instead of only metadata, producing content-aware notes (e.g. Apollo 11 summary/strengths/verification checks) while still flagging weak provenance for unattributed inline notes
- the repo now also declares a minimal `pyproject.toml` so local setup can be standardized with `uv sync --dev --extra dev`, `uv run pytest -q`, and `uv run python -m sourcetrace.web`

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
Run locally with uv:
1. `uv sync --dev --extra dev`
2. `uv run pytest -q`
3. `uv run python -m sourcetrace.web`

Run the repo-owned launcher with runtime-config + LLM wiring:
1. `uv sync --dev --extra dev`
2. export `SOURCETRACE_LLM_API_KEY`
3. export `SOURCETRACE_LLM_BASE_URL`
4. export `SOURCETRACE_LLM_API_VERSION`
5. ensure those exports are visible to the launcher process itself (for example by keeping them in the shell that starts the process, or by sourcing `~/.bashrc` before launch)
6. `bash -lc 'source /home/voytas/.bashrc && cd /home/voytas/projects/sourcetrace && PYTHONPATH=/home/voytas/projects/sourcetrace/src ./.venv/bin/python -m sourcetrace.local_launcher'`
   - or `bash -lc 'source /home/voytas/.bashrc && cd /home/voytas/projects/sourcetrace && PYTHONPATH=/home/voytas/projects/sourcetrace/src uv run sourcetrace-local'`
   - the launcher sets `LITELLM_LOG=ERROR` by default unless you already exported a different value
   - current verified shell-init shape for local launchers is: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL`, `AZURE_OPENAI_API_VERSION`, plus mirrored `SOURCETRACE_LLM_API_KEY`, `SOURCETRACE_LLM_BASE_URL`, `SOURCETRACE_LLM_API_VERSION`
   - if you keep these exports in `~/.bashrc`, place them above the non-interactive guard (`case $- in ... return`) so `bash -lc 'source ~/.bashrc && ...'` actually loads them for automation

Expected startup: `SourceTrace local server listening on http://127.0.0.1:8000`
Use `Ctrl+C` to stop the server cleanly.

Notes:
- the repo now declares a minimal `pyproject.toml` and uses `src/` package layout
- `.env` is still not loaded by the repo; any required external secrets must come from the process environment only
- `src/sourcetrace/runtime_config.py` is now the repo-owned place for task-to-profile bindings and profile-level routing defaults
- the local launcher auto-loads `litellm.completion` from the project `.venv`; if LiteLLM is missing, the launcher now fails early with a clear startup error instead of a later route-time `500`
- the local launcher currently wires `credibility_draft` through the web delivery path; broader extraction/normalization web consumption is still do weryfikacji
- the local web run is still a thin in-memory/dev path, not a production server shape

## LLM runtime config example
Production bootstrap lives outside the repo, in the process environment of whatever launches Sourcetrace:
- `SOURCETRACE_LLM_API_KEY`
- `SOURCETRACE_LLM_BASE_URL`
- `SOURCETRACE_LLM_API_VERSION`

For Azure / Microsoft Foundry GPT-5.x through LiteLLM, keep task semantics in `SourceTraceLlmConfig.tasks[...]`, keep concrete routing in `SourceTraceLlmConfig.profiles[...]`, and keep bootstrap inputs only in `LlmBootstrapConfig`:

```python
from sourcetrace.llm import (
    LlmBootstrapConfig,
    LlmProfileConfig,
    LlmTaskConfig,
    SourceTraceLlmConfig,
)

llm_config = SourceTraceLlmConfig(
    bootstrap=LlmBootstrapConfig(
        api_key_env_var="SOURCETRACE_LLM_API_KEY",
        base_url_env_var="SOURCETRACE_LLM_BASE_URL",
        api_version_env_var="SOURCETRACE_LLM_API_VERSION",
    ),
    default_timeout_seconds=30.0,
    default_max_output_tokens=1200,
    profiles={
        "claim_extraction_default": LlmProfileConfig(
            model="azure/gpt-5-mini",
            temperature=0.0,
        ),
        "claim_normalization_default": LlmProfileConfig(
            model="azure/gpt-5-mini",
            temperature=0.0,
            max_output_tokens=400,
        ),
        "credibility_assessment_default": LlmProfileConfig(
            model="azure/gpt-5",
            temperature=0.2,
            max_output_tokens=600,
        ),
    },
    tasks={
        "claim_extraction": LlmTaskConfig(profile="claim_extraction_default"),
        "claim_normalization": LlmTaskConfig(profile="claim_normalization_default"),
        "credibility_draft": LlmTaskConfig(profile="credibility_assessment_default"),
    },
)
```

Operationally, that means:
- `tasks[...]` binds SourceTrace task intent to logical profiles
- `profiles[...]` holds SourceTrace-owned routing defaults (`model`, `temperature`, `max_output_tokens`)
- `api_key`, `base_url`, and `api_version` are runtime bootstrap owned by the external launcher/environment
- `build_llm_runtime(...)` resolves bootstrap from `os.environ` and injects it only at the LiteLLM adapter edge
- `create_default_delivery(..., credibility_draft=runtime.credibility_draft)` is the current local wiring point for the credibility web path
- `claim_extraction`, `claim_normalization`, and `credibility_draft` are the currently wired task names in `src/sourcetrace/llm/runtime.py`

Do weryfikacji:
- the exact Azure deployment/model alias string must match your LiteLLM + Azure setup (`azure/gpt-5`, `azure/gpt-5-mini`, or deployment-specific alias)
- if your Azure endpoint requires `api_version=preview`, set that in the launcher environment, not in repo files

## Local smoke flow
1. Start the local server:
   - lightweight in-memory front door only: `uv run python -m sourcetrace.web`
   - repo-owned runtime-config + LLM launcher: `PYTHONPATH=src uv run python -m sourcetrace.local_launcher`
   - installed script variant: `PYTHONPATH=src uv run sourcetrace-local`
2. Open `http://127.0.0.1:8000/`
   - Expected: `200 OK` HTML landing page listing the available smoke-test routes
3. Check operational routes first:
   - `curl http://127.0.0.1:8000/api/health`
   - Expected: `200 OK` with `{ "status": "ok" }`
   - `curl http://127.0.0.1:8000/api/ready`
   - Expected: `200 OK` with JSON containing `status: ready` and `checks`
   - `curl http://127.0.0.1:8000/api/runtime`
   - Expected: `200 OK` with JSON containing `runtime.entrypoint`
   - `curl http://127.0.0.1:8000/api/capabilities`
   - Expected: `200 OK` with JSON listing `routes.product`, `routes.dev`, and runtime capability flags
4. Create a case:
   - `curl -X POST http://127.0.0.1:8000/api/cases \
      -H 'Content-Type: application/json' \
      -d '{
        "case_id": "case-1",
        "title": "Bridge reopening",
        "description": "Track public claims."
      }'`
   - Expected: `201 Created` with JSON containing `case.case_id`
5. Attach a document to that case:
   - `curl -X POST http://127.0.0.1:8000/api/cases/case-1/documents \
      -H 'Content-Type: application/json' \
      -d '{
        "document_id": "doc-1",
        "source_type": "url",
        "source_url": "https://example.test/bridge",
        "publisher": "Example News",
        "author": "Analyst",
        "title": "Bridge update",
        "published_at": "2026-05-18T00:00:00+00:00",
        "retrieved_at": "2026-05-18T00:05:00+00:00",
        "content_hash": "sha256:abc123",
        "language": "en"
      }'`
   - Expected: `201 Created` with JSON containing `document.document_id`
6. Prepare chunks for the document:
   - `curl -X POST http://127.0.0.1:8000/api/documents/doc-1/prepare \
      -H 'Content-Type: application/json' \
      -d '{
        "raw_text": "The bridge reopened after inspection.\n\nTraffic resumed.",
        "chunking_method": "paragraph-v1"
      }'`
   - Expected: `200 OK` with JSON containing `chunks`
7. Run claim extraction:
   - `curl -X POST http://127.0.0.1:8000/api/documents/doc-1/extract-claims \
      -H 'Content-Type: application/json' \
      -d '{"extraction_method":"llm_v1"}'`
   - Expected: `200 OK` with JSON containing `claims` and `diagnostics`
   - Current verified guardrail: if claim normalization returns a conversational/helpdesk-style rewrite, Sourcetrace keeps the original extracted claim text instead of persisting the rewritten assistant-style text.
   - Current verified live nuance: answer-style claim openings like `Yes — ...` / `No — ...` are now also filtered as conversational leakage, so simple inline factual notes produce cleaner claim-like sentences instead of Q&A-style phrasing.
8. In another terminal, submit a minimal verification request:
   - `curl -X POST http://127.0.0.1:8000/api/verify \
     -H 'Content-Type: application/json' \
     -d '{
       "claim": {
         "claim_id": "claim-1",
         "case_id": "case-1",
         "document_id": "doc-1",
         "chunk_id": "doc-1:chunk-1",
         "exact_text": "The bridge reopened after inspection.",
         "source_span_reference": "p1",
         "system_verdict": "insufficient_evidence",
         "rationale": null
       },
       "requested_k": 2
     }'`
   - Expected: `200 OK` with JSON containing `verification.verdict`
9. Inspect the resource reads:
   - `curl http://127.0.0.1:8000/api/cases`
   - `curl http://127.0.0.1:8000/api/cases/case-1`
   - `curl http://127.0.0.1:8000/api/cases/case-1/documents`
   - `curl http://127.0.0.1:8000/api/documents/doc-1`
   - `curl http://127.0.0.1:8000/api/documents/doc-1/chunks`
   - `curl http://127.0.0.1:8000/api/cases/case-1/claims`
   - `curl http://127.0.0.1:8000/api/claims/claim-1`
   - `curl http://127.0.0.1:8000/api/claims/claim-1/verification`
   - `curl http://127.0.0.1:8000/api/claims/claim-1/evidence`
   - `curl http://127.0.0.1:8000/cases/case-1`
   - Expected: each returns `200 OK` after the relevant upstream step is completed
   - Current verified UI nuance: `/cases/{case_id}` now renders a `Document status` table with chunk count, claim count, credibility state, and a concrete next-action endpoint instead of only showing an empty claims table.
10. Record a minimal analyst review so the case report surface has reviewed content:
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
   - `curl http://127.0.0.1:8000/api/claims/claim-1/review`
   - Expected: `200 OK` with JSON containing the persisted review artifact
11. Export the report:
   - `curl http://127.0.0.1:8000/api/reports/case-1`
   - Expected: `200 OK` with canonical report JSON
   - `curl http://127.0.0.1:8000/api/reports/case-1.md`
   - Expected: `200 OK` with `Content-Type: text/markdown; charset=utf-8`
12. Draft advisory document credibility notes:
   - `curl -X POST http://127.0.0.1:8000/api/documents/doc-1/credibility \
      -H 'Content-Type: application/json' \
      -d '{"assessment_method":"llm_draft_v1"}'`
   - Expected: `200 OK` with JSON containing `credibility_assessment.notes`
   - `curl http://127.0.0.1:8000/api/documents/doc-1/credibility`
   - Expected: `200 OK` with the latest persisted `credibility_assessment`
   - The current `llm_draft_v1` output should be treated as an advisory draft.
   - It currently relies mostly on document metadata, source identity, and topic context, not yet on full article-text analysis or claim-by-claim verification.
   - Current live-smoke nuance: JSON-like credibility blobs are normalized more readably, but plain markdown/prose answers from the provider can still arrive as longer advisory notes rather than compact bullet summaries.

## Test-use checklist for collecting findings
- Start with `python -m sourcetrace.local_launcher`, not the thin `sourcetrace.web` path, if you want real LLM-backed extraction/credibility behavior.
- For each article, record:
  - source URL
  - publisher / title / retrieved_at
  - whether extraction returned concise claim-like sentences or assistant-style prose
  - `diagnostics.dropped_claim_items`
  - whether credibility notes were useful or generic
- Prefer 3 article types in the first pass:
  - straightforward factual news brief
  - longer analytical article
  - article with quotes / caveats / mixed certainty
- After `prepare`, always inspect chunks before judging extraction quality:
  - `curl http://127.0.0.1:8000/api/documents/<doc-id>/chunks`
- After `extract-claims`, inspect both:
  - immediate route response
  - persisted case claims via `GET /api/cases/<case-id>/claims`
- Treat these as separate findings:
  - extraction quality
  - normalization quality
  - credibility note quality
  - verification usefulness
- If you see assistant/helpdesk prose in claims, save:
  - raw input paragraph
  - final persisted `exact_text`
  - whether the bad text appeared in all claims or only some
- Recommended note-taking format:
  - `docs/plans/test-use-observation-template.md`
- Example filled note:
  - `docs/plans/test-use-observation-example-bbc.md`
- Current known limitation from live smoke: some long assistant-style rewrites can still slip through normalization fallback on real articles; the fallback is improved, and leading `Yes/No` answer-style openings are now filtered, but the cleanup is still not fully semantic.

## Example: run credibility on your own document payload
1. Start the repo-owned launcher so the in-memory document repository and LLM-backed credibility path live in the same process:
   - `bash -lc 'source /home/voytas/.bashrc && cd /home/voytas/projects/sourcetrace && PYTHONPATH=src ./.venv/bin/python -m sourcetrace.local_launcher'`
   - or use the wrapper: `bash -lc 'source /home/voytas/.bashrc && cd /home/voytas/projects/sourcetrace && ./.venv/bin/sourcetrace-www-start'`
   - readiness probe: `bash -lc 'cd /home/voytas/projects/sourcetrace && ./.venv/bin/sourcetrace-www-wait'`
   - status: `bash -lc 'cd /home/voytas/projects/sourcetrace && ./.venv/bin/sourcetrace-www-status'`
   - stop it later with: `bash -lc 'cd /home/voytas/projects/sourcetrace && ./.venv/bin/sourcetrace-www-stop'`
2. Seed your own document payload into that running process:
   - `curl -X POST http://127.0.0.1:8000/api/dev/documents \
       -H 'Content-Type: application/json' \
       -d '{
         "document_id": "doc-custom-1",
         "case_id": "case-custom-1",
         "source_type": "url",
         "source_url": "https://example.test/your-article",
         "publisher": "Your chosen publisher",
         "author": "Your chosen author",
         "title": "Your article title",
         "published_at": "2026-05-19T10:00:00+00:00",
         "retrieved_at": "2026-05-19T10:05:00+00:00",
         "content_hash": "sha256:replace-me",
         "language": "en"
       }'`
   - Expected: `201 Created` with JSON echoing `document.document_id`
3. Run credibility on the exact document you seeded:
   - `curl -X POST http://127.0.0.1:8000/api/documents/doc-custom-1/credibility \
       -H 'Content-Type: application/json' \
       -d '{"assessment_method":"llm_draft_v1"}'`
   - Expected: `200 OK` with JSON containing `credibility_assessment.notes` and `method`
4. Repeat with another payload by changing only `document_id`, `case_id`, and the document metadata block above.

## Reusable payload template
Use this as a copy-paste starting point for your own runs.

## systemd --user example
If another user should manage the WWW runtime with `systemctl --user`, write the unit file:
- `bash -lc 'cd /home/voytas/projects/sourcetrace && ./.venv/bin/sourcetrace-www-write-user-unit'`

Then reload and manage it:
- `systemctl --user daemon-reload`
- `systemctl --user enable --now sourcetrace-www.service`
- `systemctl --user status sourcetrace-www.service`
- `systemctl --user stop sourcetrace-www.service`

The generated unit defaults to the `local-launcher` mode and sources `~/.bashrc` before start, so the managing user still needs the required `SOURCETRACE_LLM_*` bootstrap env in their shell init.

```json

  "document_id": "{{document_id}}",
  "case_id": "{{case_id}}",
  "source_type": "url",
  "source_url": "{{source_url}}",
  "publisher": "{{publisher}}",
  "author": "{{author}}",
  "title": "{{title}}",
  "published_at": "{{published_at_iso8601}}",
  "retrieved_at": "{{retrieved_at_iso8601}}",
  "content_hash": "{{content_hash}}",
  "language": "{{language}}"
}
```

Minimal fields you will usually want to change first:
- `document_id`
- `case_id`
- `source_url`
- `publisher`
- `author`
- `title`
- `published_at`
- `retrieved_at`
- `content_hash`
- `language`

## Minimal failure cases
- Missing credibility assessment source document:
  - `POST /api/documents/missing-doc/credibility`
  - Expected: `404 Not Found` with `{"error": "document_not_found", "status": "missing"}`
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
- keep repo-facing docs aligned with the delivered credibility runtime launch path
- decide the next bounded integration slice after credibility helper + WSGI consumption, without widening request/application surfaces or pulling `.env` loading into the repo
- keep the MVP architecture small, auditable, and implementation-light until heavier runtime choices are explicit
