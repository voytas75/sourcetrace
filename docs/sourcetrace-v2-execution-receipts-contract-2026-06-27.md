# SourceTrace v2 execution receipts contract (2026-06-27)

## Verdict
SourceTrace v2 should treat execution receipts as a **first-class append-only truth layer**.

This is not only about token usage.
It is the shared contract for describing what actually happened during execution.

Without this, the system will drift back toward reconstructing truth from worker state, scattered logs, and feature-local bookkeeping.

## Purpose
Execution receipts should answer:
- what ran,
- in what job/run/stage context,
- with which provider/model/runtime path,
- with what usage/latency/retry behavior,
- what degraded or failed,
- what output or artifact boundary was produced.

## Core principle
Capture once at stable seams, then project later.

That means:
- receipt capture should happen at execution seams,
- business attribution should come from explicit execution context,
- UI/API/diagnostics should be projections over persisted receipts,
- not reconstructed guesses.

## Minimal receipt categories for v2

### 1. Stage execution receipts
For each stage execution:
- job_id
- run_id
- stage_id
- call_site
- attempt
- start/end time
- status
- degradation reason if any

### 2. LLM execution receipts
For each LLM-backed call:
- provider
- model
- logical profile
- mode (`text` / `structured`)
- input/output/total tokens when available
- optional cost when provider supplies it
- timeout/retry/fallback path
- finish reason
- coverage status (`tracked`, `provider_missing_usage`, `estimated`, `non_llm_backend`)

### 3. Tool/backend receipts
For non-LLM external work when it matters:
- backend kind
- adapter name
- execution duration
- retry/fallback behavior
- coverage notes

### 4. Artifact emission receipts
For important artifact boundaries:
- result artifact emitted
- compiled artifact emitted
- diagnostics emitted
- projection rendered
- emission status/failure

## Minimal execution context
Every receipt family should be attributable through stable context:
- `job_id`
- `run_id`
- `feature`
- `stage_id`
- `call_site`
- optional `attempt`
- optional `round_number`
- optional parent/causal receipt id

If a receipt cannot be tied back to stable execution context, the design is too weak.

## Stable identifiers
V2 should use typed/stable identifiers for:
- feature
- stage
- receipt kind
- status
- degradation reason
- coverage status

Do not use free-form strings as the only durable accounting/diagnostic key.

## Append-only posture
Execution receipts should be append-only.

Why:
- preserves truthful run history,
- supports debugging and operator inspection,
- avoids mutable “last known state” becoming the only truth,
- makes projection/re-aggregation safer.

Derived summaries can be rebuilt from receipts when necessary, but receipts remain the durable source.

## Relationship to logs
Receipts are **not the same thing as logs**.

- logs are diagnostic narration,
- receipts are typed execution truth.

Logs may reference receipt IDs or correlation fields.
But logs should not be the only durable representation of important execution facts.

## Relationship to artifacts
Receipts are not a replacement for artifacts.

Use this separation:
- receipts = execution truth,
- result artifact = one run’s output truth,
- compiled artifact = durable knowledge truth,
- diagnostics/lint = operator quality truth.

This separation should stay explicit.

## Suggested minimal schema families
A healthy minimal set for v2:
- `ExecutionReceipt`
- `StageExecutionReceipt`
- `LlmExecutionReceipt`
- `BackendExecutionReceipt`
- `ArtifactEmissionReceipt`
- `ExecutionRollup`

Where `ExecutionRollup` is a derived summary, not the only truth source.

## Required operator-visible truths
V2 should make it easy to answer:
- which stage ran,
- which profile/provider/model actually executed,
- what usage/cost/latency was observed,
- whether fallback/degradation happened,
- whether missing coverage exists,
- which artifact boundaries were successfully produced.

## What should stay out of early v2
Do not overload receipts with everything at once.
Avoid:
- overly granular workflow-engine events,
- arbitrary nested blobs without schema discipline,
- giant “universal telemetry object” design,
- trying to model every future backend before the first proving slice.

Keep receipts typed, bounded, and composable.

## Minimal proving requirement
The first v2 slice should prove that:
- receipts are captured at stable seams,
- receipts survive partial failure,
- receipts can drive operator/API projection,
- token usage and provider provenance are not reconstructed from logs,
- stage attribution remains correct when new helper paths are added.

## Bottom line
SourceTrace v2 should treat execution receipts as a foundational architecture layer.
That is the clean way to keep:
- token accounting,
- runtime provenance,
- degradation truth,
- operator inspectability,

healthy as the system grows.
