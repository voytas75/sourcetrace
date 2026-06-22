# Deep Research fresh-topic quality report — 2026-06-22

Status: completed bounded live check
Date: 2026-06-22
Scope: run a small fresh-topic Deep Research benchmark on non-canonical queries, distinguish runtime-smoke behavior from real research-quality behavior, identify blockers, and verify the smallest safe runtime fix.

## 1. Executive verdict

This investigation found and cleared the real runtime blocker.

### What was broken
The live Deep Research path failed after retrieval with:
- `openai.NotFoundError: 404 Resource not found`
- mapped into `sourcetrace.llm.errors.LlmProviderError`

### Root cause
SourceTrace was passing the Azure v1-style base URL directly into LiteLLM for `azure/...` models:
- `https://...openai.azure.com/openai/v1`

But this runtime/provider combination needed the deployment-shaped base URL for Azure model routing:
- `https://...openai.azure.com/openai/deployments/<deployment>`

For this repo’s current runtime, the missing deployment-path rewrite caused `research_synthesis` to fail even after live search was restored.

### Fix
Implemented the smallest safe fix in `src/sourcetrace/llm/litellm_client.py`:
- when model starts with `azure/` and base URL ends with `/openai/v1`, rewrite the base URL to:
  - `/openai/deployments/<model-without-azure-prefix>`

Added a focused regression test for this rewrite.

### Verification outcome
After the fix:
- unit tests passed,
- one live Deep Research run completed end-to-end through the public API,
- the fresh-topic 4-query pack also completed end-to-end.
\nSo the system is now back in a state where fresh-topic quality can be judged honestly.

---

## 2. What was tested

Fresh-topic benchmark pack:

1. `How do I configure passkey authentication in Microsoft Entra ID for users?`
2. `What changed in VMware licensing after the Broadcom acquisition?`
3. `How does retrieval-augmented generation differ from deep research agents?`
4. `What are the latest practical changes in enterprise browser management for Chrome and Edge in 2025?`

Why this set:
- procedural/admin query,
- vendor/licensing change query,
- conceptual comparison query,
- current-practical enterprise operations query.

---

## 3. Blocker chain found during investigation

### Phase 1 — degraded-mode discovery
Initial runtime state showed:
- `research_search_backend = stub`
- `research_search_configured = false`

That first run proved only degraded-mode honesty, not real research quality.
\n### Phase 2 — live retrieval restored
Reintroduced:
- `SOURCETRACE_SEARXNG_BASE_URL=http://127.0.0.1:18080`

Verified runtime then reported:
- `research_search_backend = searxng`
- `research_search_configured = true`

### Phase 3 — live synthesis failure reproduced directly
After restoring retrieval, `POST /api/research/run/{job_id}` returned 500.
The error was reproduced directly in-process and traced to the live Azure/LiteLLM synthesis path.

### Phase 4 — provider fix implemented and verified
After the Azure deployment-path rewrite fix:
- direct live synthesis worked,
- one public API research run completed successfully,
- the full fresh-topic pack completed successfully.

---

## 4. Verification evidence

### Code change
Files changed:
- `src/sourcetrace/llm/litellm_client.py`
- `tests/unit/llm/test_litellm_client.py`

### Automated gate
Executed:
- `pytest -q tests/unit/llm/test_litellm_client.py tests/unit/test_runtime_config.py`

Result:
- `16 passed`

### Direct provider repro before/after
Before fix:
- direct `.venv` LiteLLM call with current repo Azure config returned `404 Resource not found`

After fix behavior was validated through the repo runtime path using the rewritten deployment URL logic.

### Public API end-to-end gate
Verified one live query end-to-end:
- query: `How do I configure passkey authentication in Microsoft Entra ID for users?`
- terminal status: `done`
- providers: `['searxng']`
- findings: `5`
- evaluator:
  - `source_quality = strong`
  - `relevance = strong`
  - `truthfulness = strong`
  - `should_revise_report = false`

### Procedural Unified Search live verification gate
Verified a second live procedural run after restoring the current local launcher wiring to `mycrewhelper` Unified Search:
- query: `How do I create configuration baselines in SCCM?`
- terminal status: `done`
- `result.stats.search_providers = ['procedural_admin_unified_search']`
- top evidence URLs included Microsoft Learn procedural docs for:
  - creating configuration baselines,
  - deploying configuration baselines,
  - common tasks for configuration baselines
- evaluator:
  - `source_quality = strong`
  - `relevance = strong`
  - `truthfulness = strong`
  - `should_revise_report = false`

This matters because `/api/runtime` still reports the configured backend label (`searxng`), but the per-job provider telemetry now confirms that the bounded `procedural_admin` Unified Search path is actually active in live execution.

---

## 5. Fresh-topic benchmark results after fix

| Query | Providers | Source quality | Relevance | Truthfulness | Verdict |
|---|---|---|---|---|---|
| Entra passkeys procedural query | `['searxng']` | strong | strong | strong | strong pass |
| VMware licensing after Broadcom | `['searxng']` | mixed | mixed | strong | usable but authority-noisy |
| RAG vs deep research agents | `['searxng']` | mixed | strong | strong | good answer, source mix should tighten |
| Enterprise browser management 2025 | `['searxng']` | weak | weak | mixed | still weak current-news class |

Generated benchmark summary totals:
- Entra passkeys: `12/12`
- VMware licensing: `10/12`
- RAG vs deep research agents: `11/12`
- Enterprise browser management 2025: `7/12`

---

## 6. Per-query judgment

### A. Entra passkeys — strong pass
This is the cleanest result.

Top evidence came from Microsoft Learn pages directly about:
- enabling passkeys in Authenticator,
- enabling passkeys (FIDO2),
- registering passkeys,
- passkey authentication concepts in Entra ID.

This is exactly what the system should do on a procedural/admin query.

Verdict:
- strong evidence quality,
- strong relevance,
- strong truthfulness,
- no corrective action needed for this query class from this run.

### B. VMware licensing after Broadcom — usable but noisy
The answer was coherent and evaluator truthfulness remained strong.
But the top sources were largely secondary/vendor commentary rather than clearly dominant primary-source Broadcom/VMware material.

Verdict:
- answer is usable,
- source authority needs tightening,
- this is not a runtime bug anymore — this is source-selection quality work.

### C. RAG vs deep research agents — good answer, source mix should tighten
The answer itself was strong and relevant.
Top sources included Microsoft Learn, which is good.
But a weaker community-style source still mixed into the result set.

Verdict:
- concept answer is good,
- source curation for conceptual queries can still be improved.

### D. Enterprise browser management 2025 — weakest remaining class
This is now the clear weak point in the fresh-topic pack.
The answer tried to stay cautious, which is good, but evaluator still rated it:
- source_quality = weak
- relevance = weak
- truthfulness = mixed
- should_revise_report = true

The report indicates a familiar pattern for current-news / recency-sensitive queries:
- partial evidence,
- uneven attribution,
- not enough directly attributable, fresh, operator-grade sources.

Verdict:
- current-news remains the weakest live class in this fresh-topic sample.

---

## 7. Overall quality judgment

Now that the runtime bug is fixed, the benchmark gives a real product signal.

### Strong now
- procedural/admin query path
- general runtime correctness
- evaluator honesty
- end-to-end live execution
- live `procedural_admin` Unified Search routing in the current local launcher path

### Good but not fully clean
- conceptual comparison queries
- vendor/licensing change queries with mixed primary/secondary source sets

### Weakest remaining area
- current-news / recency-sensitive enterprise operations queries

That is the main takeaway.

---

## 8. Recommended next fixes

### Fix 1 — keep the Azure deployment-path rewrite
**Priority: already implemented; keep and retain test coverage**

This was the real execution blocker.
Without it, Deep Research live runs were not trustworthy.

### Fix 2 — improve source-authority handling for vendor/licensing change queries
**Priority: high**

The VMware query shows the system can answer sensibly, but it still leans too hard on secondary commentary.

Best next bounded slice:
- stronger primary-source preference when the query is about vendor policy/licensing changes,
- stronger demotion of advisory/blog content unless primary sources are absent.

### Fix 3 — improve current-news / recency-sensitive retrieval
**Priority: highest quality slice**

The browser-management-2025 query is the clearest weak point.
Needed improvements likely include:
- better recency-sensitive source selection,
- stronger attribution requirements,
- maybe query shaping for release notes / official admin docs / changelogs,
- better fallback when only partial vendor coverage is found.

### Fix 4 — improve query-class reporting for conceptual queries
**Priority: medium**

The benchmark helper still heuristically labels some fresh conceptual queries awkwardly.
That is a reporting issue more than a core product issue.

---

## 9. Recommended next action

Do not reopen broad rescue mode.
The right next slice is now visible.

Recommended order:
1. keep the Azure provider fix,
2. keep the restored local-launcher Unified Search wiring and ensure `mycrewhelper` is available in the `sourcetrace` runtime environment,
3. treat runtime correctness as restored,
4. choose **one** bounded quality slice,
5. best candidate: **current-news / recency-sensitive retrieval quality**,
6. rerun this same fresh-topic pack after that slice.

If a second slice is needed later, the next best target is:
- stronger authority preference for vendor/licensing-change queries.

---

## 10. Bottom line

This session started as a new-topic quality check and turned into a useful diagnostic chain.
It ended in a better place than expected:
- the live Deep Research runtime bug was found,
- the smallest sensible fix was implemented,
- live end-to-end execution was restored,
- and the fresh-topic benchmark now points to a real next quality target.

**Final verdict:**
- runtime bug: fixed
- live benchmark path: restored
- strongest class in this sample: procedural/admin
- weakest class in this sample: current-news / recency-sensitive operational research
