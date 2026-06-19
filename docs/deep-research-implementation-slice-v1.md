# Deep Research implementation slice v1

Status: delivered v1
Date: 2026-06-19
Scope: first concrete implementation slice for adding a Deep Research subsystem to SourceTrace.

Inputs:
- `docs/architecture-ssot.md`
- `docs/execution-blueprint.md`
- `~/.openclaw/workspace-main/notes/odysseus/deep-research-decision-log-v1-2026-06-19.md`

---

## 1. Purpose

This document translates the Deep Research decision log into the first bounded implementation slice inside SourceTrace.

This slice created a **real subsystem skeleton**, not a placeholder.
It established the runtime boundaries, storage model, lifecycle, live-search seam, live LLM synthesis seam, and minimal delivery path.

---

## 2. Slice verdict

This v1 slice delivered the backend lifecycle, persistence, progress delivery, a bounded engine loop, live search integration, live LLM synthesis, and a minimal operator UI.

Delivered in this slice:
- job and artifact schema,
- repository interfaces,
- progress event model,
- bounded job manager/runtime seam,
- start/status/cancel/result/list/run endpoints,
- SSE progress streaming,
- persisted research artifacts and progress events,
- local SearxNG search adapter wiring,
- live LLM-backed research synthesis,
- `/research` operator console,
- regression tests.

Still intentionally out of scope or only partially solved:
- true resumable continuation from prior interrupted research runs,
- advanced queueing and prioritization,
- richer analyst-grade report rendering,
- broader orchestration beyond the current bounded search/extract/synthesize loop.

---

## 3. Slice objective

Prove that SourceTrace can host Deep Research as a separate async subsystem with a durable artifact model and a real execution path.

This objective is now met:
1. a client can start a research job,
2. the system persists the job,
3. the worker moves it through lifecycle states,
4. progress events can be observed via status and SSE,
5. a result artifact is saved and reopened,
6. the system can run with live local search and live LLM synthesis.

---

## 4. Architectural fit inside SourceTrace

Deep Research now exists as a bounded area inside the existing SourceTrace layering, using the current flatter file layout of this repo.

Implemented placement:
- `src/sourcetrace/domain/research.py`
- `src/sourcetrace/application/research.py`
- `src/sourcetrace/application/research_runtime.py`
- `src/sourcetrace/storage/research.py`
- `src/sourcetrace/storage/research_filesystem.py`
- research delivery/routes integrated into:
  - `src/sourcetrace/web/api.py`
  - `src/sourcetrace/web/delivery.py`

### Boundary rule
Deep Research is adjacent to claim/report workflows, but it is not merely another report view.
It owns its own lifecycle, progress model, result artifact, and runtime wiring.

---

## 5. Scope delivered

This slice delivered:
- research job domain model,
- research result artifact model,
- progress event model,
- in-memory and filesystem-backed research persistence,
- application use cases for start/status/cancel/result/list/run,
- bounded research engine/runtime seams,
- live search adapter seam with SearxNG wiring,
- LLM-backed synthesis seam,
- minimal HTTP and HTML delivery path,
- regression tests.

---

## 6. Scope still out

This slice still excludes or only partially addresses:
- true checkpoint resume/continuation after process interruption,
- advanced queue broker/scheduler adoption,
- analyst-grade final report UX,
- broader multi-provider orchestration,
- richer planning/report customization beyond the current bounded runtime.

---

## 7. Delivered implementation summary

### 7.1 Domain contracts
Delivered contracts include:
- `ResearchJob`
- `ResearchJobStatus`
- `ResearchPhase`
- `ResearchProgressEvent`
- `ResearchSettings`
- `ResearchResultArtifact`
- `ResearchCompletionMode`

### 7.2 Storage seam
Delivered storage interfaces and implementations include:
- `ResearchJobRepository`
- `ResearchResultRepository`
- `ResearchProgressEventStore`
- in-memory implementations in `src/sourcetrace/storage/research.py`
- filesystem-backed persistence in `src/sourcetrace/storage/research_filesystem.py`

Filesystem-backed persistence stores research state under `data/research` by default, or under `SOURCETRACE_RESEARCH_DATA_DIR` when set.

### 7.3 Application/runtime use cases
Delivered use cases/runtime orchestration include:
- `start_research_job(...)`
- `get_research_job_status(...)`
- `cancel_research_job(...)`
- `get_research_result(...)`
- `list_research_jobs(...)`
- `run_job(...)`
- bounded runtime composition in `src/sourcetrace/application/research_runtime.py`

### 7.4 Worker/runtime seam
The current runtime is no longer just a fake lifecycle stub.
It now includes a bounded Deep Research loop with search, extraction, synthesis, and finalize seams, while still staying within a local, bounded implementation posture.

### 7.5 Web/API delivery path
Delivered delivery surface:
- `GET /research`
- `POST /api/research/start`
- `GET /api/research/jobs?owner_id=...`
- `GET /api/research/status/{job_id}`
- `GET /api/research/stream/{job_id}`
- `GET /api/research/result/{job_id}`
- `POST /api/research/run/{job_id}`
- `POST /api/research/cancel/{job_id}`

---

## 8. Runtime/operator notes

### Local launcher wiring
The local launcher now wires Deep Research through:
- `SOURCETRACE_SEARXNG_BASE_URL`
- `SOURCETRACE_RESEARCH_DATA_DIR`
- `research_synthesis` task routing from `src/sourcetrace/runtime_config.py`

### Current model routing
Current default task routing in the repo uses:
- `azure/gpt-5.4`
for the Deep Research synthesis path.

### Recovery posture
Current restart posture is recovery-as-error, not true resume:
- interrupted `queued` / `probing` / `running` jobs are recovered as `error`
- error marker: `interrupted_on_recovery`
- final error progress event is appended on recovery

---

## 9. Verification status

This slice has been verified at two levels:
- live runtime verification with local SearxNG and live LLM synthesis,
- automated regression verification via repo test suite.

Current known verification result after the latest sync:
- `387 passed`

---

## 10. Recommended next step

The next sensible step is not more lifecycle plumbing.
The next step should be one of:
- prompt/report quality tuning for the research output,
- a bounded manual operator pass on `/research`,
- or a narrower docs/runtime hardening pass if operator guidance needs to improve first.
