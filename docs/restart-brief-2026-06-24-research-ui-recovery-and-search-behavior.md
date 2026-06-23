# SourceTrace restart brief — 2026-06-24 research UI recovery and search behavior

## State to resume from
This slice is ready to park.

Current bounded state:
- Deep Research local runtime is healthy again through `python -m sourcetrace.www_control start`
- `/research` recovered the newer operator-facing UI instead of the regressed older layout
- `/research/debug` now exists again as the raw/debug surface
- `/api/research/result/{job_id}.html` remains the dedicated external HTML report surface
- fake stub-search success was removed; missing usable search now fails explicitly instead of pretending success
- non-procedural/community queries now use:
  1. exact original user query first
  2. LLM-refined retry only after empty first-pass retrieval

## What this slice completed

### Runtime/persistence contract hardening
Completed in code and verified locally:
- fixed compiled artifact and compiled-lint API access to use `delivery.research_persistence`
- canonicalized Deep Research persistence default to repo-root `data/research`
- fixed `www_control` repo-root/env bootstrapping so launcher exports correct:
  - `PYTHONPATH=<repo>/src`
  - `SOURCETRACE_RESEARCH_DATA_DIR=<repo>/data/research`
- fixed local launcher boot order so Deep Research runtime is only built in the right branch
- merged shell env from `~/.bashrc` in wrapper start path so required LLM bootstrap env is present

### Search/runtime behavior hardening
Completed in code and verified locally:
- removed fake `StubSearchAdapter` fallback success path
- `build_provider_search_adapter(...)` now raises explicit `ResearchSearchError` when no unified or SearxNG backend is configured
- live runtime now reports accurate backend state through `/api/runtime`, including:
  - `procedural_admin_unified_search+searxng`
  - `procedural_admin_unified_search`
  - `searxng`
  - `unavailable`
- procedural/admin path now prefers unified search and falls back to SearxNG when needed
- provider names and full generated query lists are persisted in progress events and visible in the UI/debug path

### Query-policy change for non-procedural/community queries
Completed in code and verified live:
- first pass uses only the exact user query
- if first-pass retrieval yields no usable hits, retry uses `LlmQueryGenerator`
- if both fail, the job ends in explicit error instead of a fake/no-evidence success

### `/research` UI recovery
Recovered and re-verified:
- `/research` now again includes:
  - modern operator layout
  - `Open debug view`
  - `status-chip`
  - `Search hits`
- `/research/debug` is restored as the raw/debug page
- embedded HTML preview is gone from `/research`
- `HTML` in `/research` opens the external HTML report only
- external HTML report remains the improved structured version with:
  - query-aware title
  - executive answer
  - evaluation and confidence
  - evidence highlights
  - sources reviewed

## Verification that passed

### Unit / focused verification
- `python -m py_compile src/sourcetrace/web/api.py`
- direct WSGI/harness verification previously passed for compiled artifact and lint endpoints
- unit coverage added/updated for:
  - compiled artifact endpoints
  - search runtime failure behavior
  - LLM-refined retry behavior support path
  - provider/query progress event persistence

### Live verification
Canonical local restart path used:
```bash
cd /home/openclaw/projects/sourcetrace
source .venv/bin/activate
export SOURCETRACE_SEARXNG_BASE_URL=http://127.0.0.1:18080
python -m sourcetrace.www_control stop
python -m sourcetrace.www_control start
python -m sourcetrace.www_control wait --timeout-seconds 25
```

Verified after restart:
- `/research` returns `200`
- `/research/debug` returns `200`
- `/api/research/result/rj-74219f1b3c99.html` returns `200`
- rendered `/research` HTML contains:
  - `Open debug view`
  - `status-chip`
  - `Search hits`
- rendered `/research` HTML does **not** contain stale embedded `result_html`

## Important boundaries / defer
Do **not** reopen these by inertia in the next session:
- more tuning of `procedural_admin` evaluator thresholds/directness scoring
- more ranking tweaks just because some source mixes are still imperfect

Those are separate future slices only if there is fresh evidence.

## Real remaining open issue
The remaining weakness is mainly on community/non-procedural retrieval coverage quality:
- some broad/community queries still end in true empty retrieval
- after the exact-query-first + LLM-retry policy fix, the next real layer to inspect would be:
  - raw unified/SearxNG outputs
  - `_filter_hits_for_extraction()`
  - extractor usability for community/web sources

That is a different slice from the UI/runtime recovery completed here.

## Files touched in this parked slice
- `src/sourcetrace/web/api.py`
- `src/sourcetrace/web/delivery.py`
- `src/sourcetrace/local_launcher.py`
- `src/sourcetrace/www_control/__init__.py`
- `src/sourcetrace/application/research_runtime.py`
- `src/sourcetrace/application/__init__.py`
- `src/sourcetrace/domain/research.py`
- `src/sourcetrace/storage/research.py`
- `src/sourcetrace/storage/research_filesystem.py`
- `tests/unit/web/test_research_api.py`
- `tests/unit/application/test_application_research.py`
- `README.md`
- `README-dev.md`

## Recommended prompt for the next session
Use this restart point together with:
- `docs/deep-research-procedural-report-hardening-closure-note-2026-06-23.md`
- this file: `docs/restart-brief-2026-06-24-research-ui-recovery-and-search-behavior.md`

Suggested resume prompt:
- "Return to SourceTrace Deep Research after the 2026-06-24 UI recovery/search-behavior checkpoint. Treat the `/research` UI recovery as done. Do not retune procedural evaluator scoring. If we continue quality work, inspect community-query retrieval coverage next."
