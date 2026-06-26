# SourceTrace developer notes

This file holds developer- and operator-facing details that would overload `README.md`.

Use `README.md` as the public-facing repo entry point.
Use this file for local setup, runtime variants, deeper command references, and development constraints.

## Purpose
- keep `README.md` focused on what SourceTrace is, who it is for, and the smallest honest bootstrap path
- move implementation-shaped and operator-heavy details out of the public landing surface
- preserve a tracked place for developer context that should still live in the repo

## Local setup
```bash
uv sync --dev --extra dev
uv run pytest -q
```

## Runtime modes
SourceTrace currently has two practical local run modes.

### Command help surfaces
The repo now exposes a meaningful app-level help surface for the runtime control command:
- `PYTHONPATH=src python -m sourcetrace.www_control --help`
- `PYTHONPATH=src python -m sourcetrace.www_control start --help`
- `PYTHONPATH=src python -m sourcetrace.www_control status --help`
- `PYTHONPATH=src python -m sourcetrace.www_control wait --help`
- `PYTHONPATH=src python -m sourcetrace.www_control write-user-unit --help`

The semantic SSOT draft for agent-/operator-usable help lives in:
- `docs/agent-operable-help-contract-v1.md`

### A. Thin web mode
Use this when you want the lightweight local front door without repo-owned LLM runtime wiring.

```bash
uv run python -m sourcetrace.web
```

Equivalent console script declared in `pyproject.toml`:
```bash
uv run sourcetrace-web
```

### B. Local launcher mode
Use this when you want the repo-owned runtime config plus:
- LLM-backed credibility wiring,
- Deep Research search adapter wiring,
- Deep Research LLM synthesis wiring,
- persisted research runtime state.

Required environment variables for this mode:
- `SOURCETRACE_LLM_API_KEY`
- `SOURCETRACE_LLM_BASE_URL`
- `SOURCETRACE_LLM_API_VERSION`

The launcher also mirrors legacy Azure variables when the SourceTrace names are missing:
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_BASE_URL`
- `AZURE_OPENAI_API_VERSION`

Optional runtime variables:
- `SOURCETRACE_CONTINUITY_PACK_ROOT_DIR`
- `SOURCETRACE_SEARXNG_BASE_URL`
- `SOURCETRACE_RESEARCH_DATA_DIR`

Notes:
- when `SOURCETRACE_SEARXNG_BASE_URL` is set, local launcher mode can run live Deep Research search against the configured SearxNG instance
- research runtime state is persisted under the repo-root `data/research` by default, or under `SOURCETRACE_RESEARCH_DATA_DIR` when set
- Deep Research now persists run results, compiled artifacts, and compiled-artifact lint outputs in separate filesystem namespaces under the research data root
- the current Deep Research synthesis task uses repo task routing from `src/sourcetrace/runtime_config.py`
- local launcher runtime verification hardens underspecified synthetic research synthesis into a markdown-shaped fallback so spot-checks stay representative

Installed console scripts declared in `pyproject.toml`:
```bash
uv run sourcetrace-local
uv run sourcetrace-www-start --mode local-launcher
uv run sourcetrace-www-wait --host 127.0.0.1 --port 8000 --timeout-seconds 15
uv run sourcetrace-www-status --mode local-launcher
uv run sourcetrace-www-stop --mode local-launcher
```

Module-entrypoint equivalents:
```bash
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher
# default wrapper behavior also exports SOURCETRACE_RESEARCH_DATA_DIR=<repo>/data/research unless you override it
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control wait --host 127.0.0.1 --port 8000 --timeout-seconds 15
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control status --mode local-launcher
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control stop --mode local-launcher
```

Direct fallback launcher:
```bash
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.local_launcher
```

## Deep Research operator flow
When local launcher mode is configured for research, the operator flow is:
1. open `/research`
2. start a job with `owner_id` and `query`
3. run the job
4. inspect status and progress stream
5. inspect the final result artifact
6. inspect compiled artifact and artifact lint output when needed

Current Deep Research endpoints:
- `GET /research`
- `POST /api/research/start`
- `GET /api/research/jobs?owner_id=...`
- `GET /api/research/status/{job_id}`
- `GET /api/research/stream/{job_id}`
- `GET /api/research/result/{job_id}`
- `POST /api/research/run/{job_id}`
- `POST /api/research/cancel/{job_id}`
- `GET /api/research/compiled/{artifact_id}`
- `GET /api/research/compiled/{artifact_id}/lint`

### Current quality posture
- `procedural_admin` now uses a query-class-specific Unified Search-backed upstream path with fallback to the default search path when official-doc-like signal is missing
- downstream authority-first filtering, evidence packing, evaluator, compiled artifact, and lint layers remain shared across query classes
- the current Deep Research restart point is `docs/deep-research-status-checkpoint-2026-06-22.md`

## Local verification
### Minimal smoke checklist
1. Start one of the local runtimes.
2. Open the landing page:
```bash
curl http://127.0.0.1:8000/
```
3. Check health:
```bash
curl http://127.0.0.1:8000/api/health
```
4. If you started local-launcher mode, also check readiness/runtime:
```bash
curl http://127.0.0.1:8000/api/ready
curl http://127.0.0.1:8000/api/runtime
```
5. For Deep Research-enabled launcher mode, also verify the research surface:
```bash
curl http://127.0.0.1:8000/research
curl -X POST http://127.0.0.1:8000/api/research/start \
  -H 'Content-Type: application/json' \
  -d '{"owner_id":"demo","query":"deep research architecture"}'
```
6. Run the reusable smoke command against an already running server:
```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m sourcetrace.smoke_flow --pretty
```

### Useful repo-owned smoke helpers
- `python -m sourcetrace.smoke_flow`
- `python -m sourcetrace.credibility_smoke`

## Development constraints
- prefer small slices over broad refactors
- preserve evidence-first boundaries
- do not commit secrets, datasets, generated runtime state, or local process notes
- treat `README.md` and tracked docs as GitHub-facing surfaces; avoid references to local-only artifacts
- keep uncertain claims marked as `do weryfikacji` until verified

## Documentation usage
Start from:
- `README.md` for public repo framing
- `docs/architecture-ssot.md` for architecture baseline
- `docs/execution-blueprint.md` for implementation blueprint
- `docs/deep-research-implementation-slice-v1.md` for the original delivered Deep Research slice
- `docs/deep-research-status-checkpoint-2026-06-22.md` for the current Deep Research restart point after the 2026-06-21/22 improvement chain

Use tracked docs for durable product truth.
Keep transient working notes and local process artifacts outside public-facing repo surfaces.
