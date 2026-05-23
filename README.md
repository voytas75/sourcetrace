# SourceTrace

SourceTrace is an application project for building an evidence-centric OSINT + LLM system, with research, planning, and implementation in one repository.

## Current state
This repo is no longer just a research scaffold. It now has a stable bounded product baseline around the local web/API flow, extraction, credibility drafting, and smoke verification.

Confirmed baseline now:
- evidence-first, claim-centric product direction is still the active center
- local stdlib WSGI/API + HTML flow exists under `src/sourcetrace/web/`
- the repo-owned launcher `python -m sourcetrace.local_launcher` wires runtime config + LLM-backed credibility path into that local web surface
- current local verification baseline is `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` -> `293 passed`
- create/write workflow responses now include a common top-level workflow envelope: `status`, `summary`, `next_step`, `resource`, and `resource_id`
- create responses still expose compatibility aliases at top level (`case_id`, `document_id`) for thin clients
- document IDs are now ASCII-safe for non-English titles, and fallback claim IDs stay case-scoped
- `GET /cases/{case_id}` is truthful for missing/partial states: missing cases return real `404`, persisted verification verdicts are preferred, and direct claim/evidence/verification links are exposed
- claim normalization resists basic cross-language drift for Polish source text instead of persisting obvious English rewrite drift
- credibility assessment now ships both backward-compatible `notes` and structured credibility output (`summary`, `strengths`, `concerns`, `verification_checks`)
- credibility runtime also maps semantic assessment fields (`source_reliability`, `information_credibility`, `provenance_distance`, factor arrays) with conservative `unknown` fallback when the draft is weak
- weak-source credibility handling is explicitly hardened for unattributed notes, anonymous reposts, weak scraped snippets, and secondary summaries
- the HTML case view renders structured credibility output directly in each document row, shows a short snippet preview sourced from inline text or the first prepared chunk, and now labels missing credibility explicitly as `Status: Not assessed yet.` with the next credibility endpoint
- inline document continuity is verified end-to-end: `POST /api/cases/{case_id}/documents` accepts `content` or `text`, `prepare` can reuse stored inline text, `extract-claims` now auto-prepares stored inline content when chunks are missing, and document payloads expose `has_inline_content`
- a reusable smoke command now exists as `python -m sourcetrace.smoke_flow` / `sourcetrace-smoke-flow`, supports `--pretty` and `--expect-claims-min N`, and exits non-zero on failed expectations
- GitHub Actions also includes a lightweight `CI Smoke` workflow for the same local launcher + smoke path, although this repo is currently used without a configured remote

## Repository map
- `docs/architecture/architecture-ssot.md` — canonical product and architecture baseline
- `docs/research/research-ledger.md` — rolling research notes and architecture implications
- `docs/plans/execution-blueprint-v0.md` — provisional plan between research and implementation
- `docs/plans/2026-05-23-continuity-pack-usage-note.md` — when to create a decision-ready continuity-pack wrapper over an existing artifact
- `notes/` — working notes
- `src/sourcetrace/` — application package
- `tests/` — unit/integration/doc assertions
- `data/` — local working data directories kept mostly out of git

## Working model
The intended workflow is now:
1. gather and review sources when architecture assumptions still change
2. update research ledger
3. patch SSOT and execution blueprint when assumptions change
4. execute bounded contract-first slices for agreed layers
5. only then move into broader runtime adapters, storage engines, and retrieval implementations

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
5. optional but recommended for durable continuity packs: export `SOURCETRACE_CONTINUITY_PACK_ROOT_DIR` to a writable local directory
6. ensure those exports are visible to the launcher process itself (for example by keeping them in the shell that starts the process, or by sourcing `~/.bashrc` before launch)
7. `bash -lc 'source /home/voytas/.bashrc && cd /home/voytas/projects/sourcetrace && PYTHONPATH=/home/voytas/projects/sourcetrace/src ./.venv/bin/python -m sourcetrace.local_launcher'`
   - or `bash -lc 'source /home/voytas/.bashrc && cd /home/voytas/projects/sourcetrace && PYTHONPATH=/home/voytas/projects/sourcetrace/src uv run sourcetrace-local'`
   - the launcher sets `LITELLM_LOG=ERROR` by default unless you already exported a different value
   - current verified shell-init shape for local launchers is: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL`, `AZURE_OPENAI_API_VERSION`, plus mirrored `SOURCETRACE_LLM_API_KEY`, `SOURCETRACE_LLM_BASE_URL`, `SOURCETRACE_LLM_API_VERSION`
   - if you keep these exports in `~/.bashrc`, place them above the non-interactive guard (`case $- in ... return`) so `bash -lc 'source ~/.bashrc && ...'` actually loads them for automation
   - if `SOURCETRACE_CONTINUITY_PACK_ROOT_DIR` is set, the local launcher switches continuity-pack storage from in-memory to file-backed for `active continuity pack per case`; replace keeps `latest_previous` and clear removes only `active`
   - verify the effective mode with `GET /api/ready` or `GET /api/runtime` and inspect `continuity_pack_persistence.enabled`, `backend`, and `root_dir`

Expected startup: `SourceTrace local server listening on http://127.0.0.1:8000`
Use `Ctrl+C` to stop the server cleanly.

Notes:
- the repo declares a minimal `pyproject.toml` and uses `src/` package layout
- `.env` is still not loaded by the repo; any required external secrets must come from the process environment only
- `src/sourcetrace/runtime_config.py` is the repo-owned place for task-to-profile bindings and profile-level routing defaults
- the local launcher auto-loads `litellm.completion` from the project `.venv`; if LiteLLM is missing, the launcher fails early with a clear startup error instead of a later route-time `500`
- the local launcher currently wires `credibility_draft` through the web delivery path; broader extraction/normalization web consumption is still do weryfikacji
- the local web run is still a thin in-memory/dev path, not a production server shape
- `.github/workflows/ci-smoke.yml` now provides a minimal GitHub Actions smoke lane: focused smoke CLI pytest, launcher boot, readiness wait, reusable smoke flow, and server-log dump on failure

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
3. Fast reusable smoke (recommended after restart; requires an already running local server on `127.0.0.1:8000`):
   - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.smoke_flow`
   - or installed script: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src sourcetrace-smoke-flow`
   - pretty JSON: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.smoke_flow --pretty`
   - stricter minimum claim expectation: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.smoke_flow --expect-claims-min 2`
   - Expected: JSON report with `prepare_chunk_count`, `extract_claim_count`, `credibility_has_summary`, `html_has_snippet`, and `html_has_summary`
   - Operational contract: the command exits `0` on pass and `1` on failed expectations; on failure it still prints the report JSON to stdout plus a failure summary JSON to stderr
4. Check operational routes first:
   - `curl http://127.0.0.1:8000/api/health`
   - Expected: `200 OK` with `{ "status": "ok" }`
   - `curl http://127.0.0.1:8000/api/ready`
   - Expected: `200 OK` with JSON containing `status: ready`, `checks`, and `diagnostics.continuity_pack_persistence`
   - `curl http://127.0.0.1:8000/api/runtime`
   - Expected: `200 OK` with JSON containing `runtime.entrypoint` and `runtime.continuity_pack_persistence`
   - `curl http://127.0.0.1:8000/api/capabilities`
   - Expected: `200 OK` with JSON listing `routes.product`, `routes.dev`, and runtime capability flags
5. Create a case:
   - `curl -X POST http://127.0.0.1:8000/api/cases \
      -H 'Content-Type: application/json' \
      -d '{
        "case_id": "case-1",
        "title": "Bridge reopening",
        "description": "Track public claims."
      }'`
   - Expected: `201 Created` with JSON containing `case.case_id`
6. Create or inspect a continuity pack for that case:
   - assign one from an existing artifact:
     - `curl -X POST http://127.0.0.1:8000/api/cases/case-1/continuity-pack \
        -H 'Content-Type: application/json' \
        -d '{
          "artifact_path": "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
        }'`
   - inspect the case continuity-pack read surface:
     - `curl http://127.0.0.1:8000/api/cases/case-1/continuity-pack`
   - Expected: `200 OK` with `resource: case_continuity_pack`, `continuity_pack.assigned`, nested `latest_previous`, `artifacts.active`, `artifacts.latest_previous`, and convenience `actions`
   - Semantics: for an existing case this route is now a read model, so after clear it still returns `200 OK` with an empty continuity-pack state instead of `404`
   - Replace semantics: assigning a new continuity pack moves the previous active one into `latest_previous`
   - Clear semantics: `DELETE /api/cases/case-1/continuity-pack` removes only the active assignment; `latest_previous` remains available when present
7. Attach a document to that case:
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
   - Current verified continuity: the same route also accepts inline `text` (alias for `content`), and the returned document payload exposes `has_inline_content: true` when inline text was stored for later prepare reuse
7. Prepare chunks for the document:
   - `curl -X POST http://127.0.0.1:8000/api/documents/doc-1/prepare \
      -H 'Content-Type: application/json' \
      -d '{
        "raw_text": "The bridge reopened after inspection.\n\nTraffic resumed.",
        "chunking_method": "paragraph-v1"
      }'`
   - Expected: `200 OK` with JSON containing `chunks`
   - Current verified diagnostics: the response also includes `diagnostics.chunk_count`, `diagnostics.status`, `diagnostics.summary`, and `diagnostics.next_step` so the caller can tell whether prepare produced usable chunks and what to do next.
   - Current verified continuity: if the document was created earlier with inline `content` or `text`, `POST /api/documents/{document_id}/prepare` can now be called with an empty JSON body and it will reuse the previously stored inline text instead of returning `empty`.
   - Current verified continuity: `POST /api/documents/{document_id}/extract-claims` now also auto-prepares stored inline content when chunks are still missing, so inline note flows do not silently fall into empty extraction just because prepare was skipped.
8. Run claim extraction:
   - `curl -X POST http://127.0.0.1:8000/api/documents/doc-1/extract-claims \
      -H 'Content-Type: application/json' \
      -d '{"extraction_method":"llm_v1"}'`
   - Expected: `200 OK` with JSON containing `claims` and `diagnostics`
   - Current verified diagnostics: `diagnostics` now includes `claim_count`, `chunk_count`, `status`, `summary`, and `next_step`, so empty extraction results explain whether the next move is to inspect chunks or re-run prepare/extract with better source text.
   - Current verified guardrail: if claim normalization returns a conversational/helpdesk-style rewrite, Sourcetrace keeps the original extracted claim text instead of persisting the rewritten assistant-style text.
   - Current verified guardrail: SourceTrace also resists basic cross-language drift for Polish source text during normalization.
9. In another terminal, submit a minimal verification request:
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
10. Inspect the resource reads:
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
   - Current verified UI nuance: `/cases/{case_id}` now renders a `Document status` table with chunk count, claim count, credibility state, a concrete next-action endpoint, and a short `Snippet:` preview sourced from inline text (or the first prepared chunk when inline text is unavailable).
   - Current verified UI nuance: the same HTML view shows summary/strengths/concerns/verification checks directly in each document row and returns a real `404` for missing cases instead of rendering `Case None`.
11. Record a minimal analyst review so the case report surface has reviewed content:
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
12. Export the report:
   - `curl http://127.0.0.1:8000/api/reports/case-1`
   - Expected: `200 OK` with canonical report JSON
   - `curl http://127.0.0.1:8000/api/reports/case-1.md`
   - Expected: `200 OK` with `Content-Type: text/markdown; charset=utf-8`
13. Draft advisory document credibility notes:
   - `curl -X POST http://127.0.0.1:8000/api/documents/doc-1/credibility \
      -H 'Content-Type: application/json' \
      -d '{"assessment_method":"llm_draft_v1"}'`
   - Expected: `200 OK` with JSON containing `credibility_assessment.notes`
   - `curl http://127.0.0.1:8000/api/documents/doc-1/credibility`
   - Expected: `200 OK` with the latest persisted `credibility_assessment`
   - The current `llm_draft_v1` output should be treated as an advisory draft.
   - It currently relies mostly on document metadata, source identity, and topic context, not yet on full article-text analysis or claim-by-claim verification.
   - Current verified semantics/UI behavior: the same payload now also includes structured fields (`summary`, `strengths`, `concerns`, `verification_checks`), maps semantic assessment fields when the draft provides them, and is hardened toward semantic JSON output with stabilisation scenarios in test coverage.
   - Current verified weak-source nuance: unattributed notes, anonymous reposts, and weak scraped snippets now settle more conservatively, while secondary news summaries stay secondary unless they clearly embed the primary material.

## Test-use checklist for collecting findings
- Current execution SSOT for the first real-data campaign:
  - `docs/plans/2026-05-21-real-data-test-use-ssot.md`
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
- Continuity-pack guidance:
  - `docs/plans/2026-05-23-continuity-pack-usage-note.md`
- Current continuity-pack examples:
  - `docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md`
  - `docs/plans/2026-05-23-source-trace-research-continuity-pack-cerebroscope.md`
- Runtime continuity-pack model is now `active + latest_previous` per case, not full history.
- `GET /api/cases/{case_id}/continuity-pack` now acts as a read model for existing cases: it returns `200 OK` with current continuity-pack state, artifact pointers, and convenience actions even after clear.
- Replace keeps the former active pack as `latest_previous`; clear removes only `active`.
- Use a continuity pack selectively when an existing observation or research artifact already contains enough evidence for a real next-step decision, but still needs a decision-ready wrapper.
- Current known limitation from live smoke: some long assistant-style rewrites can still slip through normalization fallback on real articles; the fallback is improved, and leading `Yes/No` answer-style openings are now filtered, but the cleanup is still not fully semantic.
- Current verified contrast note continuity: inline note-style contrast inputs no longer fall into `empty` just because `extract-claims` ran before an explicit `prepare`, but exact claim shape can still vary between the stronger restriction clause and an additional reopening clause.

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

## Reusable payload template
```json
{
  "document_id": "{{document_id}}",
  "case_id": "{{case_id}}",
  "source_type": "url",
  "source_url": "{{source_url}}",
  "publisher": "{{publisher}}",
  "author": "{{author}}",
  "title": "{{title}}",
  "published_at": "{{published_at_iso}}",
  "retrieved_at": "{{retrieved_at_iso}}",
  "content_hash": "{{content_hash}}",
  "language": "{{language}}"
}
```

## systemd --user example
Generate a user unit from the repo wrapper:
- `cd /home/voytas/projects/sourcetrace && ./.venv/bin/sourcetrace-www-write-user-unit`
- then: `systemctl --user daemon-reload`

## Minimal failure cases
- `POST /api/documents/missing-doc/credibility`
  - Expected: `404 Not Found` with `{"error": "document_not_found", "status": "missing"}`
- `GET /api/claims/missing-claim/verification`
  - Expected: `404 Not Found` with `{"error": "verification_not_found", "status": "missing"}`
- `GET /api/reports/missing-case.json`
  - Expected: `404 Not Found` with `{"error": "report_not_found", "status": "missing"}`
- `POST /api/reviews` with an incomplete payload
  - Expected: `400 Bad Request` with `status: invalid_request`
