# SourceTrace v2 minimal proving slice (2026-06-27)

## Verdict
The first v2 proof should be small, end-to-end, and architecture-revealing.

It should not try to rebuild all of Deep Research.
It should prove that the new core is actually easier to extend and easier to reason about.

## Goal
Build one minimal vertical slice that proves all of the following at once:
- typed job/run/stage lifecycle,
- stage-composition instead of giant orchestrator growth,
- execution receipts as first-class truth,
- profile-based runtime config,
- one result artifact projection,
- one operator/API projection,
- one logging path with correlation.

## Recommended proving slice
Use a bounded research flow with only a few stages:

1. `planning`
2. `query_refinement`
3. `evidence_judge`
4. `synthesis`

This is enough to test:
- multiple LLM-backed stages,
- stable stage attribution,
- receipts and rollups,
- partial failure semantics,
- result projection,
- operator inspectability.

## Explicit non-goals for the proving slice
Do **not** include in the first proof:
- full Deep Research parity,
- compiled artifact sophistication,
- broad PDF/backend coverage,
- many provider integrations,
- plugin framework,
- dynamic workflow editing,
- full budget/quota system,
- advanced UI.

Keep the first proof brutally narrow.

## Minimal entities required
The first proving slice should likely include:
- `ResearchJob`
- `ResearchRun`
- `StageExecutionReceipt`
- `LlmExecutionReceipt`
- `ExecutionRollup`
- `ResearchResultArtifact`
- one operator/API projection model

That is enough to prove the spine without building the whole system.

## Required behaviors

### 1. Job lifecycle
Must support at least:
- queued
- running
- done
- error

### 2. Stage lifecycle
Each stage execution should be independently attributable and inspectable.

### 3. LLM profile resolution
Each LLM-backed stage should run via logical profile mapping, not raw model strings embedded in stage code.

### 4. Receipt capture
Each stage should emit receipts at stable seams, including:
- stage execution status,
- provider/model provenance,
- token usage when available,
- fallback/degradation truth when relevant.

### 5. Result projection
The proving slice should output one minimal result artifact with:
- run summary,
- output text,
- compact rollup,
- stable links to execution truth.

### 6. Operator/API surface
The proving slice should have at least one operator-facing JSON projection that can answer:
- what ran,
- what failed or degraded,
- what model/profile executed,
- how much usage was consumed,
- what final result was emitted.

## Recommended architecture inside the proving slice

### Stage modules
Each stage should be a bounded module with:
- input contract,
- output contract,
- required execution context,
- explicit emitted receipts,
- explicit failure semantics.

### Shared receipt collector
Receipt capture should be shared.
Do not hand-roll bookkeeping differently per stage.

### Shared runtime profile resolver
LLM-backed stages should resolve logical profile -> concrete runtime at one shared boundary.

### Shared projection layer
Operator/API payloads should be projections over typed artifacts and receipts, not direct runtime state dumps.

## Success criteria
The proving slice is successful if adding one more stage after the first implementation feels bounded.

A healthy test:
- adding a new stage should mostly mean adding one stage module,
- one stage mapping entry,
- maybe one projection extension,
- not rewriting the central execution logic.

## Failure signals
The proving slice should be treated as a warning sign if:
- stage logic starts collapsing back into one big orchestrator,
- receipts are partially reconstructed from logs,
- profile resolution leaks raw provider/model strings into business logic,
- operator/API projections depend on ad hoc runtime state,
- adding one extra stage already requires touching too many unrelated files.

## Why this slice is enough
This slice is small, but it exercises the exact architectural properties that matter most:
- composability,
- execution truth,
- attribution,
- inspectability,
- bounded extension cost.

If those work here, broader v2 growth has a chance.
If they do not, a larger build will only hide the architectural problem.

## Bottom line
The first SourceTrace v2 proving slice should be a narrow end-to-end research flow that proves:
- the core is smaller,
- the seams are stronger,
- receipts are real,
- config is sane,
- extension cost is lower than in v1.
