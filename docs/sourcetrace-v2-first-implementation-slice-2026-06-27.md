# SourceTrace v2 first implementation slice (2026-06-27)

## Verdict
The first implementation slice should build the **minimum independent v2 spine**, not a compatibility-heavy half-step sitting on top of v1.

The goal is to prove that v2 can stand on its own as a cleaner core system.
So the slice should be deliberately small, but structurally complete.

## Slice goal
Build the first independent end-to-end v2 path with:
- its own package spine,
- its own runtime config contract,
- its own native logging layer,
- its own execution receipt layer,
- its own stage-composition flow,
- its own API projection,
- one bounded research result artifact.

This slice should **not** depend on reusing v1 orchestrators.

## Minimal scope
Include only:
- one v2 package tree
- one bounded research workflow
- four stage modules
- one LLM adapter path
- one API projection path
- native logging with text/json modes
- receipt capture with rollups

Recommended stages:
1. `planning`
2. `query_refinement`
3. `evidence_judge`
4. `synthesis`

## Explicit exclusions
Do not include in the first slice:
- compiled artifact parity
- PDF subsystem parity
- search-provider plurality
- queue/background runtime sophistication
- migration of all old artifacts\n- UI richness
- workflow engine abstraction
- budget policy engine
- plugin system

Keep it independent and narrow.

## Concrete build order

### Step 1 — Create the v2 package spine
Add the initial package layout under `src/sourcetrace_v2/` with empty or skeletal modules for:
- `core/domain`
- `core/contracts`
- `execution/context`
- `execution/stages`
- `execution/receipts`
- `runtime/config`
- `runtime/logging`
- `adapters/llm`
- `projections/api`
- `app/composition`

This step proves the independence boundary.

### Step 2 — Define minimal core types
Define only the types needed for the first slice:
- `ResearchJob`
- `ResearchRun`
- `ResearchResultArtifact`
- `StageExecutionReceipt`
- `LlmExecutionReceipt`
- `ExecutionRollup`
- stable stage/status identifiers

No speculative overexpansion.

### Step 3 — Implement runtime config
Implement the smallest useful config layer:
- profile schema
- feature-policy schema
- loader/validator
- profile resolver
- log config section

This step ensures stage code can depend on logical profiles instead of raw model strings.

### Step 4 — Implement native logging
Implement:
- logger bootstrap
- text formatter
- JSON formatter
- correlation helper
- redaction helper

Logging should be functional before the workflow is wired.

### Step 5 — Implement receipt collection
Implement:
- append-only receipt emission contract
- stage receipts
- LLM receipts
- simple rollup builder

This is one of the key architecture proofs.

### Step 6 — Implement stage module contract + four stages
Build the shared stage interface and then implement:
- planning
- query refinement
- evidence judge
- synthesis

These can be minimal, but they must use:
- explicit context
- explicit receipts
- logical profile resolution
- stable stage identifiers

### Step 7 — Implement one LLM adapter path
Add one concrete LLM adapter path behind the v2 adapter boundary.
Prefer a single provider path first.

The point is not provider breadth.
The point is proving the seam.

### Step 8 — Implement one API projection
Expose one minimal JSON result/status projection that can answer:
- what ran,
- which stages completed,
- what model/profile/provider executed,
- what token usage was observed,
- what result artifact was produced,
- what degraded or failed.

### Step 9 — Add vertical slice tests
Add tests proving:
- profile resolution works
- logs can run in text/json modes
- receipts are captured at the shared seam
- partial failure still preserves truthful receipts
- adding a stage does not require rewriting the whole flow

## Minimum DoD
The first slice is done when all of the following are true:
1. v2 has its own package spine under `src/sourcetrace_v2/`.
2. No v1 orchestrator is imported into the v2 core execution path.
3. Stage code uses logical profiles, not raw provider/model strings.
4. Native logging works in both text and JSON mode.
5. Execution receipts are persisted or at least durably collected as typed records.
6. One bounded workflow can run end-to-end through the four stages.
7. One API projection can show result + receipt-backed execution truth.
8. Partial failure does not destroy the execution truth surface.

## Architectural guardrail
If during the first slice the fastest path starts looking like:
- reusing the old worker,
- copying v1 runtime semantics whole,
- moving truth into logs,
- or putting too much control flow back into one large execution file,

then stop and correct the architecture.
That would defeat the purpose of v2.

## Why this slice is the right start
Because it proves the hardest thing first:
not whether SourceTrace can produce another answer,
but whether SourceTrace v2 can grow as an independent, cleaner system.

That is the real test.

## Bottom line
The first implementation slice should be a **small but fully independent v2 spine**.

If this slice is clean, future growth has a chance.
If this slice already compromises the independence boundary, v2 will inherit the same architectural drag it is supposed to escape.
