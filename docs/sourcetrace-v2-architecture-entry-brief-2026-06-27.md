# SourceTrace v2 architecture entry brief (2026-06-27)

## Decision frame
SourceTrace v2 should be treated as a **clean-core rewrite**, not as continued patch-layer growth on the current runtime.

The reason is not that the current system is worthless.
The reason is that the current system already contains the right product thesis and several good boundaries, but it is at risk of becoming harder to extend if too much future capability is added by enlarging orchestration-heavy runtime paths.

So the v2 move should be:
- preserve the product thesis,
- preserve the strongest domain boundaries,
- preserve evidence-first/operator-truth discipline,
- rebuild the execution spine around a smaller, harder, more composable core.

## What v2 is trying to achieve
V2 should optimize for one thing above all:

**cheap, safe extension of core behavior without weakening evidence truth or operator inspectability.**

That means:
- new research stages should be easy to add,
- new evaluators/judges should be easy to add,
- new runtime adapters should be easy to add,
- new artifact projections should be easy to add,
- new cross-cutting concerns should be capturable once at stable seams,
- and none of those should require central orchestrator growth as the default move.

## Non-goals
V2 should **not** be framed as:
- “rewrite everything because the old code is messy”,
- “make everything a plugin”,
- “replace evidence-first with agent autonomy”,
- “optimize for novelty over inspectability”,
- “rebuild all features before stabilizing the core”.

## What v2 must preserve from current SourceTrace

### 1. Evidence-first thesis
Keep the core order:
- evidence first,
- claims second,
- review before trust,
- report after evidence and review.

### 2. Separation of truth layers
Preserve explicit differences between:
- execution truth,
- operator truth,
- durable knowledge truth.

### 3. Provider-neutral LLM boundary
Keep SourceTrace-owned task semantics, normalized models, and operator meaning outside provider-specific adapters.

### 4. Artifact-first posture
Important truth should live in typed artifacts and typed records, not only in logs, progress streams, or inferred runtime state.

### 5. Inspectability as a product property
The analyst/operator must still be able to inspect:
- why the system said something,
- what evidence it used,
- how confidence was formed,
- what runtime path produced the result,
- what degraded or failed.

## What v2 should intentionally reset

### 1. Central orchestrator growth as the default architecture
V2 should not keep accumulating meaning primarily inside one large runtime worker or one large execution file.

### 2. Feature-local bookkeeping for cross-cutting concerns
Usage, retries, provenance, evaluation traces, backend coverage, and similar concerns should not depend on every feature remembering manual instrumentation.

### 3. Ad hoc stage semantics
Stable stage meaning should come from typed identifiers and explicit execution context, not from free-form labels in progress details.

### 4. Blurred artifact boundaries
Result artifacts, compiled knowledge artifacts, diagnostics, and runtime receipts should stay separate unless there is a deliberate projection between them.

### 5. Runtime-local truth leaks
Task config, provider details, route presence, or helper-local behavior should not be allowed to silently define product truth.

## Proposed v2 architectural spine

### Layer 1 — Core domain
The core domain should stay small and hard.
It should define stable concepts such as:
- case,
- source/document,
- chunk/evidence unit,
- claim,
- review decision,
- research job,
- result artifact,
- compiled artifact,
- diagnostics/lint,
- execution receipt.

This layer should contain business truth, not runtime glue.

### Layer 2 — Application contracts
This layer should expose bounded application operations such as:
- start research job,
- advance research stage,
- persist result,
- compile result into durable artifact,
- evaluate artifact quality,
- record execution receipt,
- render operator-facing projections.

Each operation should have explicit request/outcome contracts.

### Layer 3 — Execution composition
This layer should assemble workflows from composable stage modules.

A stage module should look more like:
- explicit input contract,
- explicit output contract,
- explicit execution context,
- explicit emitted receipts/events/artifacts,
- explicit failure semantics.

Not like “call giant orchestrator and inspect side effects later.”

### Layer 4 — Integration adapters
Adapters should own external mechanics only:
- search providers,
- LiteLLM/provider calls,
- PDF tools,
- HTML fetch/render,
- persistence backend specifics,
- queue/background runtime,
- web/API transport.

Adapters should not become the place where SourceTrace business truth is invented.

### Layer 5 — Projection surfaces
API, HTML, analyst UI, exports, and diagnostics should be treated as projections over typed truth records and artifacts.

That keeps operator surfaces extensible without forcing core model distortion.

## Extension model for v2
A healthy v2 should make most future additions fall into one of these categories:
- add a new stage module,
- add a new evaluator/judge module,
- add a new adapter,
- add a new artifact projection,
- add a new receipt/diagnostic stream,
- add a new policy layer over existing typed truth.

If a change requires editing the central execution spine in many unrelated places, that is a signal the core is too soft.

## Cross-cutting concerns in v2
Anything likely to spread across the app should have a first-class capture seam from day 1.

Examples:
- token usage,
- provider/model provenance,
- prompt/version provenance,
- retries/attempts,
- latency/cost,
- backend coverage,
- evaluation outcomes,
- degradation/failure reasons.

Rule:
**capture once at the seam, attribute with explicit business context, project later as needed.**

That is much healthier than reconstructing truth from scattered helper logic.

## Recommended execution model
V2 should prefer:
- typed execution context,
- stable stage identifiers,
- append-only receipts for execution truth,
- small aggregators/projectors,
- stage modules that can be composed into bounded workflows.

That would allow:
- Deep Research v2,
- lighter direct-answer flows,
- non-research extraction/evaluation flows,
- future hybrid workflows,

without forcing all of them through one monolithic control path.

## Migration posture
Do not try to migrate everything at once.

The right posture is:
1. define the v2 architectural spine,
2. define a minimal end-to-end slice that proves it,
3. port one meaningful workflow onto it,
4. compare operator truth, inspectability, and extension cost against v1,
5. only then decide broader migration pace.

## Best first proving slice for v2
The best first proof is not “all of Deep Research.”
That is too large.

A better first proof would be a bounded research slice that includes:
- one job lifecycle,
- a few stage modules,
- typed execution receipts,
- token/provenance capture,
- result artifact generation,
- one compiled artifact projection,
- operator-facing API/HTML projection.

That is enough to prove whether the new spine is actually better.

## Decision recommendation
If the strategic goal is a core system that can grow without increasingly expensive architectural drag, then a SourceTrace v2 rewrite is a rational direction.

But it should be a **disciplined rewrite around a harder core**, not a broad restart.

The test for success is simple:

> in v2, adding a new stage or cross-cutting concern should mostly mean adding a bounded module to a stable spine, not enlarging a central orchestrator.

## Bottom line
SourceTrace v2 should be conceived as:
- a rewrite that preserves thesis,
- a rewrite that reduces orchestration sprawl,
- a rewrite that makes extension cheaper,
- a rewrite that keeps evidence truth and operator inspectability first.

In one sentence:

**v2 should be smaller in core, stronger in seams, and easier to grow without losing truth.**
