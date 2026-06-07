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
Use this when you want the repo-owned runtime config plus LLM-backed credibility wiring.

Required environment variables for this mode:
- `SOURCETRACE_LLM_API_KEY`
- `SOURCETRACE_LLM_BASE_URL`
- `SOURCETRACE_LLM_API_VERSION`

The launcher also mirrors legacy Azure variables when the SourceTrace names are missing:
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_BASE_URL`
- `AZURE_OPENAI_API_VERSION`

Optional continuity-pack persistence:
- `SOURCETRACE_CONTINUITY_PACK_ROOT_DIR`

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
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control wait --host 127.0.0.1 --port 8000 --timeout-seconds 15
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control status --mode local-launcher
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control stop --mode local-launcher
```

Direct fallback launcher:
```bash
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.local_launcher
```

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
5. Run the reusable smoke command against an already running server:
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
- `notes/plans/local-launcher-readiness-ssot.md` for verified launcher/runtime boundary
- `notes/plans/2026-06-05-verification-control-plane-ssot.md` for current verification-first execution SSOT

Use tracked docs for durable product truth.
Keep transient working notes and local process artifacts outside public-facing repo surfaces.
