# SourceTrace Local Launcher Readiness SSOT

Status: active readiness SSOT
Scope: canonical readiness plan and checkpoint for the repo-owned local launcher path
Last verified: 2026-05-19

## Purpose
This document is the current SSOT for getting the repo-owned local launcher into a repeatable test-usable state, while keeping README, architecture SSOT, and the execution blueprint aligned with the verified runtime truth.

## Verified current state
- Repo: `/home/voytas/projects/sourcetrace`
- Branch: `main`
- Working tree was clean before this readiness pass.
- `src/sourcetrace/local_launcher.py` exists and is the repo-owned launcher entrypoint.
- `src/sourcetrace/runtime_config.py` is the repo-side task-model routing file.
- The currently wired task names are:
  - `claim_extraction`
  - `claim_normalization`
  - `credibility_draft`
- The launcher builds `build_llm_runtime(...)` and wires only `credibility_draft` into the local WSGI delivery path.
- `build_local_server_runtime()` now auto-loads `litellm.completion` when LiteLLM is installed in the local `.venv`; otherwise it fails early with a clear launcher error before serving misleading `500` responses later.
- Local dev/test environment needed an explicit extras sync; `uv sync --dev --extra dev` restored `pytest` into `.venv`.
- Current local verification baseline is confirmed live:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ./.venv/bin/python -m pytest -q` -> `198 passed`
- The local launcher can be started successfully from a shell that sources `/home/voytas/.bashrc`.
- Live smoke confirmation from the running local server:
  - `GET /` returns the HTML landing page
  - `POST /api/verify` returns `200 OK` with a verification payload
  - `POST /api/dev/documents` returns `201 Created` and seeds the in-memory document state in the same server process
- The live credibility-route probe advanced from `404` to `500` after same-process seeding, which confirms the route now reaches the LLM-backed credibility path and is blocked later than persistence lookup.

## Verified environment boundary
- Provider/bootstrap env vars are not repo-owned config.
- `/home/voytas/.bashrc` contains exports for:
  - `SOURCETRACE_LLM_API_KEY`
  - `SOURCETRACE_LLM_BASE_URL`
  - `SOURCETRACE_LLM_API_VERSION`
- The shell that launched the local server did report successful startup after sourcing `.bashrc`.
- Separate non-server bootstrap probes still did **not** inherit those vars reliably in this Hermes execution context (`None` values were observed).
- Operational consequence: treat `.bashrc`-based bootstrap as partially environment-dependent in automation. For reliable verification runs, pass the required `SOURCETRACE_LLM_*` vars explicitly or verify inside the exact launching shell/process.

## Important current limitation
- The current local launcher path is only confirmed as a runnable local server plus `credibility_draft` wiring point.
- The live smoke completed against:
  - the home route
  - the in-memory verification path
- Broader real analyst flow through LLM-backed `claim_extraction` and `claim_normalization` via the HTTP front door is still **do weryfikacji**.
- A successful server start does not yet prove a successful real external LLM call.
- Current verified status for the first LLM-backed HTTP route:
  - same-process document seeding is now available through `POST /api/dev/documents`
  - `POST /api/documents/{document_id}/credibility` no longer fails at missing in-memory state
  - the latest live probe returned `500 Internal Server Error`, and the captured traceback confirmed the precise cause: the launcher was started without a real LiteLLM completion backend and fell back to `_missing_litellm_completion`
  - the launcher code now fails earlier and more clearly when LiteLLM is absent, but a successful real provider-backed credibility response is still **do weryfikacji** until LiteLLM is installed and the route is re-run

## Readiness verdict
- **Ready now for limited local test use:** yes
- **Ready now for collecting broad product conclusions from real analyst usage:** not yet

Interpretation:
- The project is now ready for thin-path local usage and operator exploration of the current WSGI/dev flow.
- It is not yet ready to treat the local launcher as a fully verified analyst workflow surface.

## Execution plan

### Task 1 — Freeze and document the verified launcher bootstrap contract
Objective: keep one canonical repo doc that reflects the real launch boundary and current readiness truth.

Steps:
1. Keep this file as the readiness SSOT for the launcher path.
2. Sync `README.md`, `docs/architecture/architecture-ssot.md`, and `docs/plans/execution-blueprint-v0.md` to this verified state.
3. Keep all statements about broader LLM-backed HTTP usage under **do weryfikacji** until a live route proves them.

### Task 2 — Keep local environment bootstrap reproducible
Objective: make the next local operator run predictable.

Steps:
1. Use `uv sync --dev --extra dev` for local setup in this repo.
2. Treat `uv sync --dev` alone as insufficient for the current optional-dependency layout.
3. Keep provider bootstrap outside the repo and sourced from shell/runtime env only.
4. When verifying the launcher from Hermes/automation, run via `bash -lc 'source /home/voytas/.bashrc && ...'` or equivalent.

### Task 3 — Verify the first real LLM-backed local route
Objective: move from "server starts" to "local launcher executes real LLM-backed application path".

Steps:
1. Start `PYTHONPATH=src python -m sourcetrace.local_launcher` from a shell that has the exported `SOURCETRACE_LLM_*` vars.
2. Seed or create the minimal required document state for a live credibility request in the same running process.
   - Current dev-only verified route: `POST /api/dev/documents`
3. Execute:
   - `POST /api/documents/{document_id}/credibility`
4. Confirm one of the following with evidence:
   - `200 OK` and payload with drafted advisory notes
   - explicit provider/bootstrap/runtime failure that can be classified precisely
5. Record the verified result back into README + SSOT + blueprint.

### Task 4 — Verify whether HTTP-local usage can already support early analyst feedback
Objective: establish whether the current surface is enough for collecting meaningful usage findings.

Steps:
1. Run the current thin-path local flow end-to-end:
   - verify claim
   - inspect verification artifact
   - record review
   - export report
2. Classify what is already usable for analyst/operator feedback versus what is still only engineering smoke.
3. Keep missing pieces explicit instead of inferring readiness from the existence of routes.

## Confirmed operator commands
- Setup:
  - `uv sync --dev --extra dev`
- Tests:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ./.venv/bin/python -m pytest -q`
- Launcher:
  - `bash -lc 'source /home/voytas/.bashrc && cd /home/voytas/projects/sourcetrace && PYTHONPATH=src ./.venv/bin/python -m sourcetrace.local_launcher'`
- Alternate launcher path:
  - `bash -lc 'source /home/voytas/.bashrc && cd /home/voytas/projects/sourcetrace && PYTHONPATH=src uv run sourcetrace-local'`

## Do weryfikacji
- Whether `POST /api/documents/{document_id}/credibility` completes successfully against the real provider wiring once the running process is seeded with the required in-memory document state.
- Whether installing `litellm` into `.venv` is sufficient for the first real end-to-end credibility success, or whether provider/bootstrap config still needs another correction after that.
- Whether the current local launcher meaningfully exercises `claim_extraction` and `claim_normalization` through the HTTP front door.
- Whether the current route set is sufficient for collecting product-level usage conclusions rather than only engineering smoke feedback.
- Whether README examples should be narrowed or expanded after the first live credibility-route smoke.
