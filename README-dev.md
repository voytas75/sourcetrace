# SourceTrace developer notes

> Current posture: `sourcetrace_v2` is the active implementation line and the default local runtime surface.
>
> Start with:
> - [`docs/sourcetrace-v2-restart-checkpoint-2026-07-19.md`](docs/sourcetrace-v2-restart-checkpoint-2026-07-19.md) — canonical active-v2 entrypoint and restart guide
> - `docs/sourcetrace-v2-full-closure-map-2026-06-27.md`
> - relevant `docs/sourcetrace-v2-*.md` notes
>
> `docs/STATUS.md` remains historical context. See also: `docs/sourcetrace-v2-docs-posture-2026-06-27.md`.

This file holds developer- and operator-facing details that would overload `README.md`.

Use `README.md` as the public-facing repo entry point.
Use this file for local setup, runtime commands, deeper command references, and development constraints.

## Purpose
- keep `README.md` focused on what SourceTrace is, who it is for, and the smallest honest bootstrap path
- move implementation-shaped and operator-heavy details out of the public landing surface
- preserve a tracked place for developer context that should still live in the repo

## Local setup
```bash
uv sync --dev --extra dev
uv run pytest -q
```

## Runtime commands
SourceTrace v2 now owns the default local operator/runtime surface.

### Command help surfaces
The repo now exposes an app-level help surface for the v2 runtime control command:
- `PYTHONPATH=src python -m sourcetrace_v2.operator.www --help`
- `PYTHONPATH=src python -m sourcetrace_v2.operator.www start --help`
- `PYTHONPATH=src python -m sourcetrace_v2.operator.www status --help`
- `PYTHONPATH=src python -m sourcetrace_v2.operator.www wait --help`
- `PYTHONPATH=src python -m sourcetrace_v2.operator.www write-user-unit --help`

The semantic SSOT draft for agent-/operator-usable help still lives in:
- `docs/agent-operable-help-contract-v1.md`

### Default v2 WWW mode
Use this when you want the repo-owned v2 runtime config plus:
- v2 live LLM wiring,
- v2 search adapter wiring,
- v2 JSONL persistence/readback,
- v2 operator-facing HTTP surface.

Required environment variables for live mode:
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `SOURCETRACE_SEARXNG_BASE_URL`

Optional runtime variables:
- `SOURCETRACE_RESEARCH_DATA_DIR`

Notes:
- persisted runtime state is stored under repo-root `data/research` by default, or under `SOURCETRACE_RESEARCH_DATA_DIR` when set
- the v2 HTTP surface is intentionally minimal and operator-facing rather than legacy Deep Research UI compatible

Installed console scripts declared in `pyproject.toml`:
```bash
uv run sourcetrace-web serve
uv run sourcetrace-www-start
uv run sourcetrace-www-wait --host 127.0.0.1 --port 8000 --timeout-seconds 15
uv run sourcetrace-www-status
uv run sourcetrace-www-stop
uv run sourcetrace-www-write-user-unit
```

Module-entrypoint equivalents:
```bash
PYTHONPATH=src ./.venv/bin/python -m sourcetrace_v2.operator.www start
# default wrapper behavior also exports SOURCETRACE_RESEARCH_DATA_DIR=<repo>/data/research unless you override it
PYTHONPATH=src ./.venv/bin/python -m sourcetrace_v2.operator.www wait --host 127.0.0.1 --port 8000 --timeout-seconds 15
PYTHONPATH=src ./.venv/bin/python -m sourcetrace_v2.operator.www status
PYTHONPATH=src ./.venv/bin/python -m sourcetrace_v2.operator.www stop
```

Direct foreground server:
```bash
PYTHONPATH=src ./.venv/bin/python -m sourcetrace_v2.operator.www serve --host 127.0.0.1 --port 8000
```

### Direct v2 operator CLIs
```bash
uv run sourcetrace-v2-run "deep research architecture" --json-pretty
uv run sourcetrace-v2-readback execution JOB_ID RUN_ID --artifacts-dir "$PWD/data/research" --json-pretty
uv run sourcetrace-v2-readback compiled JOB_ID RUN_ID --artifacts-dir "$PWD/data/research" --json-pretty
```

## v2 operator flow
For the default v2 operator surface, the flow is:
1. `POST /api/v2/run` with `query`
2. inspect persisted execution view at `GET /api/v2/execution/{job_id}/{run_id}`
3. inspect persisted compiled view at `GET /api/v2/compiled/{job_id}/{run_id}`

Current v2 endpoints:
- `GET /`
- `GET /api/health`
- `GET /api/ready`
- `GET /api/runtime`
- `POST /api/v2/run`
- `GET /api/v2/execution/{job_id}/{run_id}`
- `GET /api/v2/compiled/{job_id}/{run_id}`

### Current quality posture
- v2 is the active implementation/runtime surface
- operator truth still depends on retrieval quality, selected evidence quality, and trust alignment quality
- the [2026-07-19 active-v2 restart checkpoint](docs/sourcetrace-v2-restart-checkpoint-2026-07-19.md) is the canonical restart guide; `docs/STATUS.md` and 2026-06-28 readiness docs are supporting history

## Local verification
### Minimal smoke checklist
1. Start the v2 runtime.
2. Open the landing page:
```bash
curl http://127.0.0.1:8000/
```
3. Check health:
```bash
curl http://127.0.0.1:8000/api/health
```
4. Check readiness/runtime:
```bash
curl http://127.0.0.1:8000/api/ready
curl http://127.0.0.1:8000/api/runtime
```
5. Verify the v2 run surface:
```bash
curl -X POST http://127.0.0.1:8000/api/v2/run \
  -H 'Content-Type: application/json' \
  -d '{"query":"deep research architecture"}'
```
6. Run the reusable v2 CLI smoke against the live env:
```bash
uv run sourcetrace-v2-run "deep research architecture" --json-pretty
```

### Useful repo-owned v2 helpers
- `uv run sourcetrace-v2-run`
- `uv run sourcetrace-v2-readback`

## Development constraints
- prefer small slices over broad refactors
- preserve evidence-first boundaries
- do not commit secrets, datasets, generated runtime state, or local process notes
- treat `README.md` and tracked docs as GitHub-facing surfaces; avoid references to local-only artifacts
- keep uncertain claims marked as `do weryfikacji` until verified

## Documentation usage
Start from:
- `README.md` for public repo framing
- [`docs/sourcetrace-v2-restart-checkpoint-2026-07-19.md`](docs/sourcetrace-v2-restart-checkpoint-2026-07-19.md) for the active v2 entrypoint, verification posture, and next action
- `docs/sourcetrace-v2-full-closure-map-2026-06-27.md` for closure sequencing
- `docs/sourcetrace-v2-docs-posture-2026-06-27.md` for active-vs-legacy docs posture
- relevant `docs/sourcetrace-v2-*.md` contract/brief/checkpoint notes for the slice you are touching

`docs/deep-research-status-checkpoint-2026-06-22.md` and other old Deep Research docs are legacy migration/reference material, not the default runtime/operator path.
Use tracked docs for durable product truth.
Keep transient working notes and local process artifacts outside public-facing repo surfaces.
