# Deep Research token-usage evidence gap — TODO (2026-06-27)

## Verdict
SourceTrace already has provider-neutral token usage primitives in the LLM layer (`sourcetrace.llm.models.TokenUsage` and LiteLLM usage normalization), but Deep Research does **not** currently persist or expose a job-level evidence layer for token usage.

Today, Deep Research artifacts persist execution stats such as duration, rounds, queries, urls, provider names, pre-extraction filtering counts, and evidence-pack counts, but not token usage by job, stage, or provider call.

## Confirmed code facts

### Present today
- `src/sourcetrace/llm/models.py`
  - `TokenUsage(input_tokens, output_tokens, total_tokens)` exists.
- `src/sourcetrace/llm/litellm_client.py`
  - provider responses are normalized into `TokenUsage`.
- `src/sourcetrace/domain/research.py`
  - `ResearchStats` currently stores runtime stats only:
    - `duration_seconds`
    - `rounds`
    - `queries`
    - `urls`
    - `model`
    - `search_providers`
    - pre-extraction counts
    - authority-filter flags
    - packed core/supporting/background counts
  - `ResearchResultArtifact` has no token accounting field.
  - `CompiledResearchArtifact` has no token accounting snapshot.
- `src/sourcetrace/application/research_runtime.py`
  - `FakeResearchWorker` builds and persists `ResearchStats`, `ResearchResultArtifact`, compiled artifact, and compiled lint.
  - no job-level token aggregation/persistence is attached during research execution.

### Missing today
- no `prompt_tokens` / `completion_tokens` / `total_tokens` on `ResearchStats`
- no `llm_usage` structure on `ResearchResultArtifact`
- no by-stage token accounting for:
  - planning analysis
  - subject sheet
  - LLM query refinement
  - official evidence judges
  - official subject precision judge
  - family judge
  - HTML enrichment
  - PDF ingest / analyzer
  - final synthesis
- no normalized provider usage receipts persisted with a research job
- no UI/API exposure of per-job token usage evidence

## Why this matters
If SourceTrace is positioned as evidence-first / traceable deep research, token economics should be inspectable too.

Without this, the system can explain:
- what answer it produced,
- what evidence it used,
- what quality/risk evaluation it made,

but not:
- how much LLM usage a job consumed,
- which stage consumed the usage,
- whether the runtime is economically behaving as intended.

That leaves an architectural gap between evidence-first output semantics and evidence-first runtime/accountability semantics.

## Recommended bounded follow-up

### Slice name
`deep_research_token_usage_evidence_v1`

### Goal
Persist job-scoped LiteLLM token receipts and stable stage rollups for Deep Research LLM-backed calls, including partial and failed jobs, while mirroring only compact totals onto result artifacts when a result exists.

The collector architecture must stay healthy as SourceTrace grows. That means v1 should not rely on manual stage-name bookkeeping inside the current worker alone; it should capture receipts at the LLM seam and attach explicit Deep Research call-site context so new helpers and runtimes do not silently fall out of accounting.

The v1 goal is for an operator to answer:
- how many total tokens were consumed for a job,
- how many LLM calls were made,
- which stable runtime stage and call-site consumed the usage,
- which provider/model receipts contributed to the totals,
- which calls were fully tracked vs missing provider usage vs explicitly estimated.

Cost should be treated as optional in v1: persist it when LiteLLM/provider receipts already provide it, but do not make custom cost estimation part of the required slice.

### Minimal DoD
1. Add a durable **job-scoped** usage structure to the research domain model and persistence layer.
2. Reuse LiteLLM-returned usage/cost metadata as the canonical receipt source when available; do not add a separate custom token-counting path for normal runtime accounting.
3. Capture usage at the LLM seam via a shared collector/wrapper or interceptor rather than only with manual bookkeeping inside Deep Research worker code.
4. Require explicit call-site context for Deep Research LLM-backed calls, at minimum: `job_id`, `feature`, `stage`, `call_site`, and when relevant `round_number` / `attempt`.
5. Aggregate usage per job and per stable stage.
6. Persist compact totals on `ResearchResultArtifact` only when a result exists; do not make result artifacts the only durable home of usage evidence.
7. Expose the usage in job/result API payloads and result HTML/analyst views.
8. Add tests covering full success, partial salvage, hard failure after some LLM activity, start-job planning usage, and newly added Deep Research helper paths using the shared collector.

## Recommended shape

### Source of truth posture
- LiteLLM should remain the execution/receipt layer for token and cost metadata.
- SourceTrace should own:
  - policy,
  - routing/fallback decisions,
  - stage labeling,
  - aggregation,
  - persistence,
  - operator-facing presentation.
- Avoid introducing a separate custom token-counting path for primary runtime accounting unless a provider path truly returns no usage metadata and a fallback estimate is explicitly marked as an estimate.

### New domain objects
Candidate additions:
- `ResearchTokenUsage`
  - `input_tokens`
  - `output_tokens`
  - `total_tokens`
  - `calls`
  - optional `total_cost_usd`
- `ResearchStageTokenUsage`
  - `stage`
  - `usage`
  - `models`
  - `providers`
  - optional `coverage_status` (`tracked`, `provider_missing_usage`, `estimated`, `non_llm_backend`)
- `ResearchUsageReceipt`
  - `job_id`
  - `feature`
  - `stage`
  - `call_site`
  - optional `round_number`
  - optional `attempt`
  - `model`
  - `provider`
  - `input_tokens`
  - `output_tokens`
  - `total_tokens`
  - optional `response_cost_usd`
  - optional `finish_reason`
  - optional `coverage_status` (`tracked`, `provider_missing_usage`, `estimated`, `non_llm_backend`)
  - optional `receipt_source` (`litellm_response_usage`, `litellm_response_cost`, `estimated_fallback`)
- `ResearchJobUsageRecord`
  - `job_id`
  - `owner_id`
  - `totals`
  - `by_stage`
  - `receipts`
  - `created_at`
  - `updated_at`

### Attachment points
- primary durable home: job-scoped usage record keyed by `job_id`
- append-only receipt capture should happen at the shared LLM seam, with Deep Research passing explicit call-site context
- `ResearchResultArtifact.llm_usage_summary` as compact mirrored totals when a result exists
- optionally `ResearchStats.llm_calls`, `input_tokens`, `output_tokens`, `total_tokens`
- do **not** require compiled artifact inclusion in v1
- do **not** use progress-event `details` as the accounting source of truth

### LLM seams to track first
Track actual current LLM-backed seams rather than an abstract pipeline list. Start with:
- `planning_analysis` (when `ResearchJobManager` is wired with `LlmPlanningAnalyzer`)
- `subject_sheet`
- `query_refinement`
- `search_relevance_judge`
- `official_evidence_judge`
- `official_subject_precision_judge`
- `official_evidence_family_judge`
- `official_html_enrichment`
- `synthesis`
- `pdf_ingest` only when the active backend returns a real LLM usage receipt; otherwise mark coverage as `provider_missing_usage` or `non_llm_backend` in v1

Use stable stage ids / constants for rollups. Do not derive accounting from ad hoc string labels in progress payloads.

## Architectural note
Do **not** make this a logging-only feature.
If the data is not part of persisted job artifacts, it is not a real evidence layer.

Also: do **not** replace LiteLLM receipts with custom token-counting logic as the main accounting path.
SourceTrace should aggregate and expose usage, not reinvent provider accounting.

Keep the lifecycle boundary honest:
- usage evidence is first an execution/job concern,
- result artifacts may mirror compact totals,
- compiled artifacts should stay focused on reusable knowledge and should not be widened for runtime economics in v1.

Keep the collection boundary honest too:
- stage-name accounting inside worker code is not enough for long-term growth,
- the durable source should come from interceptor/wrapper-based receipt capture at the LLM seam,
- Deep Research should provide explicit business context for attribution,
- `ResearchSettings.model` should not be treated as accounting truth when actual execution can come from task/runtime config.

## Open design question
Where should the aggregation live: inside `FakeResearchWorker`, inside an application-level helper, or in a lower-level LLM runtime hook?

Current leaning:
- capture receipt at the shared LLM runtime edge,
- require explicit call-site context from Deep Research,
- aggregate in a dedicated application-layer usage collector/service,
- persist in job-scoped research usage artifacts.

A pure worker-local collector is likely too brittle as the app grows.

## Recommendation
Yes: this should be explicitly closed both **architecturally** and **implementation-wise** in SourceTrace.
It fits the product thesis and should be tracked as a bounded deep-research slice, not a vague future improvement.

But the bounded slice should stay narrow:
- job-scoped usage evidence first,
- compact result mirroring second,
- compiled artifact integration deferred unless a later operator need clearly justifies it.
- interceptor-based collection plus explicit call-site context should be treated as part of the v1 architecture, not a later nice-to-have.

## Related architectural direction
This slice also supports a broader extensibility direction for SourceTrace core.
If the project later moves toward a SourceTrace v2 rewrite, this usage/accounting slice should be read as a model for the desired architecture:
- seam-first growth,
- typed execution artifacts,
- stable lifecycle boundaries,
- interception points for cross-cutting concerns,
- clear separation between execution truth, operator truth, and durable knowledge artifacts.

A future v2 should preserve these core architectural properties while avoiding further patch-layer growth on top of legacy runtime orchestration.
