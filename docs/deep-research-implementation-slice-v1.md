# Deep Research implementation slice v1

Status: draft v1
Date: 2026-06-19
Scope: first concrete implementation slice for adding a Deep Research subsystem to SourceTrace.

Inputs:
- `docs/architecture/architecture-ssot.md`
- `docs/plans/execution-blueprint-v0.md`
- `~/.openclaw/workspace-main/notes/odysseus/deep-research-decision-log-v1-2026-06-19.md`

---

## 1. Purpose

This document translates the Deep Research decision log into the first bounded implementation slice inside SourceTrace.

This slice is meant to create a **real subsystem skeleton**, not a fake placeholder.
It should establish the correct boundaries, storage model, runtime lifecycle, and minimal delivery path.

---

## 2. Slice verdict

The first implementation slice should build **backend lifecycle + storage + minimal delivery contracts**, but **not** the full research engine.

That means v1 slice should include:
- job and artifact schema,
- repository interfaces,
- background job manager seam,
- status + progress delivery contract,
- minimal start/cancel/result/list endpoints,
- thin fake-worker path for end-to-end lifecycle verification,
- tests.

It should **not yet** include:
- full iterative search/extract/synthesize loop,
- continuation,
- visual report layer,
- advanced queue UX,
- real provider orchestration.

Reason: if lifecycle and artifact boundaries are wrong, engine work becomes rework.

---

## 3. Slice objective

Prove that SourceTrace can host Deep Research as a separate async subsystem with a durable artifact model.

Success in this slice means:
1. a client can start a research job,
2. the system persists the job,
3. a worker can move it through lifecycle states,
4. progress events can be observed,
5. a result artifact can be saved and reopened,
6. the whole path is testable without a real long-running LLM engine.

---

## 4. Architectural fit inside SourceTrace

Deep Research should be added as a new bounded area under existing SourceTrace layering.

Recommended placement:
- `src/sourcetrace/domain/research/`
- `src/sourcetrace/application/research/`
- `src/sourcetrace/storage/research/`
- `src/sourcetrace/web/research/`

If the current codebase favors flatter package placement, keep the same logical separation even if the exact paths differ.

### Boundary rule
Deep Research is adjacent to claim/report workflows, but it is not merely another report view.
It owns its own run lifecycle and artifact persistence.

---

## 5. Scope in

This slice includes:
- research job domain model,
- research result artifact model,
- progress event model,
- in-memory or existing local storage-backed repository implementation consistent with current SourceTrace style,
- application use cases for start/status/cancel/result/list,
- fake research worker for lifecycle simulation,
- minimal HTTP surface for lifecycle operations,
- regression tests.

---

## 6. Scope out

This slice explicitly excludes:
- real search adapter integration,
- real extraction pipeline integration,
- LLM planner/query/synthesis prompts,
- continuation from prior report/findings,
- archive/pin/hidden-image UI metadata,
- analyst-grade report rendering,
- queue prioritization and scheduler sophistication,
- external job broker adoption if a smaller local seam is enough for this slice.

---

## 7. Proposed deliverables

## 7.1 Domain contracts
Create contracts for:
- `ResearchJob`
- `ResearchJobStatus`
- `ResearchPhase`
- `ResearchProgressEvent`
- `ResearchSettings`
- `ResearchResultArtifact`
- `ResearchCompletionMode`

Minimum fields:

### ResearchJob
- `job_id`
- `owner_id`
- `query`
- `status`
- `created_at`
- `started_at`
- `completed_at`
- `settings`
- `error`

### ResearchResultArtifact
- `job_id`
- `owner_id`
- `query`
- `status`
- `completion_mode`
- `result`
- `raw_report`
- `category`
- `stats`
- `sources`
- `raw_findings`
- `created_at`
- `completed_at`

### ResearchProgressEvent
- `job_id`
- `status`
- `phase`
- `round`
- `queries`
- `query_preview`
- `total_sources`
- `new_sources`
- `total_findings`
- `url`
- `title`
- `message`
- optional `final`

---

## 7.2 Storage seam

Add explicit storage interfaces for:
- `ResearchJobRepository`
- `ResearchResultRepository`
- optional `ResearchProgressEventStore`

Capabilities required now:
- create job
- get job by id
- update job
- list jobs by owner
- save result artifact
- get result by job id
- append/list progress events or expose current progress snapshot

Decision for this slice:
use the **smallest existing SourceTrace storage style** that fits current repo posture.

Interpretation:
- if current runtime is still largely in-memory/in-process, start with in-memory research repositories,
- but shape interfaces so later Postgres persistence is a swap, not a redesign.

That is important: **interface-first, storage-light** for the first slice.

---

## 7.3 Application use cases

Add use cases for:
- `start_research_job(...)`
- `get_research_job_status(...)`
- `cancel_research_job(...)`
- `get_research_result(...)`
- `list_research_jobs(...)`

Possible internal orchestration service:
- `ResearchJobManager`

Responsibilities:
- create durable job record,
- transition `queued -> probing -> running -> done/error/cancelled`,
- persist result artifact,
- append progress events,
- enforce clean lifecycle invariants.

---

## 7.4 Worker seam

Add a worker boundary such as:
- `ResearchWorker`
- or `ResearchEngineRunner`

For this slice, implement a **fake/simulated worker** that:
1. reads the queued job,
2. emits a realistic small progress sequence,
3. writes a dummy result artifact,
4. marks the job `done`,
5. supports a cancellation path.

Purpose:
verify subsystem plumbing before real engine complexity enters.

This fake worker should resemble the real future lifecycle:
- probing
- planning
- searching
- analyzing
- writing
- done

But it should use deterministic stub content.

---

## 7.5 Web/API delivery path

Add a minimal HTTP/API surface:
- `POST /api/research/start`
- `GET /api/research/status/{job_id}`
- `POST /api/research/cancel/{job_id}`
- `GET /api/research/result/{job_id}`
- `GET /api/research/jobs`
- optional progress stream endpoint if current web layer can support it cheaply

If streaming is too disruptive for the first code slice, accept:
- status polling first,
- with the progress-event contract already defined,
- and make SSE the immediate next slice.

That said, if current local delivery path can add SSE cheaply, it is worth doing now because it is part of the target shape.

Recommendation:
- define the event contract now,
- implement polling for sure,
- implement SSE in this slice only if it stays narrow.

---

## 8. Proposed lifecycle contract

Top-level states:
- `queued`
- `probing`
- `running`
- `done`
- `error`
- `cancelled`

Runtime phases for events:
- `probing`
- `planning`
- `searching`
- `reading`
- `analyzing`
- `writing`
- `warning`
- `error`

Completion modes:
- `full`
- `partial_timeout`
- `partial_error`
- `fallback`

Rule:
In this slice, fake-worker completion will normally produce `completion_mode = full`.
A dedicated test should still verify at least one salvage-shaped path.

---

## 9. Proposed test plan

Minimum test pack:

### Domain tests
- status enum validity
- completion mode validity
- artifact contract round-trip

### Application tests
- start creates durable queued job
- manager transitions through legal states only
- cancel from queued/running yields cancelled
- result cannot be fetched before available unless contract allows pending response
- salvage path persists partial artifact shape

### Web/API tests
- start returns `job_id`
- status reflects progress changes
- result endpoint returns artifact after completion
- list endpoint returns owner-scoped jobs
- cancel endpoint updates terminal state correctly

### Thin end-to-end test
- start fake job
- run fake worker
- read status/result
- assert durable artifact exists

---

## 10. DoD for this slice

This slice is done when all of the below are true:
1. research jobs exist as first-class domain/application objects,
2. start/status/cancel/result/list flow works locally,
3. lifecycle transitions are tested,
4. result artifact schema is explicit and persisted,
5. progress contract exists and is exercised,
6. at least one partial-salvage-shaped test exists,
7. the implementation does not yet depend on the real Deep Research engine.

---

## 11. Rollback / containment

If this slice goes wrong, rollback is easy because:
- it is additive,
- it can sit behind isolated endpoints/modules,
- it does not need to mutate existing claim/review/report flows.

Containment rule:
Do not thread Deep Research assumptions through unrelated SourceTrace modules in this slice.
Keep the subsystem local.

---

## 12. Recommended implementation order inside the slice

1. domain contracts
2. repository interfaces + in-memory implementation
3. application manager/use cases
4. fake worker
5. web endpoints
6. tests
7. optional SSE if still narrow

This order minimizes architectural regret.

---

## 13. Next slice after this one

Once this slice is stable, the next slice should be:
`deep-research-engine-loop-v1.md`

That next slice should introduce:
- planner/query/search/extract/synthesize/finalize loop,
- real progress generation,
- deterministic stop rails,
- real partial-result salvage logic.

Not before.
