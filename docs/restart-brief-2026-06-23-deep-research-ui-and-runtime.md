# SourceTrace restart brief — 2026-06-23

## Current state
SourceTrace Deep Research local runtime is working again on `http://127.0.0.1:8000`.

Confirmed working:
- `/research` UI loads
- `Run job` works again
- live search is enabled
- HTML report option is present in the `/research` result view

Verified runtime indicators:
- `research_search_backend = "searxng"`
- `research_search_configured = true`
- active process env included a correct full Azure URL for:
  - `SOURCETRACE_LLM_BASE_URL=https://udtazureopenai.openai.azure.com/openai/v1`

## What was completed before this brief
### Deep Research runtime / quality work
Already completed earlier in this thread:
- restored live Deep Research search from stub mode to SearxNG-backed mode
- fixed Azure LiteLLM deployment-path mismatch in `src/sourcetrace/llm/litellm_client.py`
- restored bounded `procedural_admin` Unified Search wiring from `mycrewhelper`
- verified live procedural provider telemetry via `result.stats.search_providers = ['procedural_admin_unified_search']`
- added HTML report backend route for case reports

### `/research` UI slice completed and pushed
Committed and pushed:
- commit: `0f6760b`
- message: `Add HTML view for deep research results`

This slice added:
- research-result HTML endpoint:
  - `GET /api/research/result/{job_id}.html`
- `/research` result view toggle options:
  - HTML
  - Markdown
  - JSON

Main files involved:
- `src/sourcetrace/web/api.py`
- `src/sourcetrace/web/__init__.py`
- `src/sourcetrace/web/delivery.py`
- `tests/unit/web/test_research_api.py`
- `tests/unit/web/test_web_delivery.py`
- `tests/unit/web/test_full_api_routes.py`

Focused verification already passed for that slice:
- `15 passed`

## Runtime incident from this session
There was a confusing runtime/startup incident after restart.

Observed symptoms:
- user initially did not see HTML in `/research`
- later `Run job` appeared to do nothing
- logs showed `POST /api/research/run/{job_id}` returning `500`

What turned out to be true:
- one earlier restart attempt had failed because the port was already in use
- an older runtime process had still been serving on `:8000`
- after cleaning up and restarting properly, `/research` served the new UI
- later verification showed the active process had the correct env value:
  - `SOURCETRACE_LLM_BASE_URL=https://udtazureopenai.openai.azure.com/openai/v1`
- final user confirmation: `ok, dziala już`

Important caution:
- some earlier diagnosis around `/openai/v1` vs full URL was likely based on a mixed/stale process state during restart confusion
- current known-good state is: runtime works, search works, run works

## Useful verification commands
### Runtime health
```bash
curl -s http://127.0.0.1:8000/api/runtime
```
Expected:
- `research_search_backend = "searxng"`
- `research_search_configured = true`

### UI HTML toggle presence
```bash
curl -s http://127.0.0.1:8000/research | grep 'Final report'
```

### Inspect active process env
```bash
pid=$(ss -ltnp '( sport = :8000 )' | awk 'NR==2 { if (match($0,/pid=[0-9]+/)) print substr($0,RSTART+4,RLENGTH-4) }')
tr '\0' '\n' < /proc/$pid/environ | egrep '^(SOURCETRACE_|AZURE_)'
```

## Most useful next step after resume
Return to the original product question now that runtime is working again:

### Check whether evaluator verdicts are still weak on live runtime
Target example:
- `How to configure conditional access in Entra ID?`

Goal of the next pass:
- verify whether the earlier `weak / weak / mixed` result still happens **after** live runtime recovery
- distinguish:
  - real evaluator/retrieval weakness
  - versus prior degraded/stale runtime effects

Suggested verification flow:
1. start a fresh research job for the Entra conditional-access query
2. run it on the live runtime
3. inspect:
   - `result.stats.search_providers`
   - `result.evaluation.source_quality_verdict`
   - `result.evaluation.relevance_verdict`
   - `result.evaluation.truthfulness_verdict`
4. decide whether the next bounded slice should target:
   - retrieval/query shaping
   - evaluator thresholds
   - procedural authority routing

## Notes
- active project root: `/home/openclaw/projects/sourcetrace`
- do work only under `/home/openclaw/projects/`
- runtime dependency caveat still matters: local procedural Unified Search path depends on `mycrewhelper` being available in the SourceTrace runtime environment
