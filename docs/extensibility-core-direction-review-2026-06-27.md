# Extensibility core direction review (2026-06-27)

## Verdict
SourceTrace has a credible base for an extensible core system, but it is not yet consistently shaped to make future expansion cheap and safe.

The good news:
- the repo already has meaningful domain/application/storage boundaries,
- the LLM layer is provider-neutral enough to support growth,
- the product thesis is strong because it is evidence-first and artifact-oriented rather than workflow-magic-first.

The hard truth:
- some of the most important runtime behavior still grows through large orchestrators, manual wiring, ad hoc stage semantics, and feature-local control flow.
- if that continues, SourceTrace will keep adding capabilities, but the cost of extending core behavior will rise faster than the system’s clarity.

So the right direction is not “add features faster.”
The right direction is **seam-first core growth**.

## What is already strong enough to keep

### 1. Evidence-first product thesis
Keep this.
It gives the system a stable center:
- evidence,
- claims,
- review,
- report,
- inspectable artifacts.

That is a much stronger base than an agent-first or workflow-first system.

### 2. Contract-shaped layers
The existing split across:
- domain,
- application,
- storage interfaces,
- LLM boundary,
- web delivery,

is the right instinct and should be protected.

### 3. Artifact model over ephemeral flow
The presence of job/result/compiled/lint-style layers is good.
It enables durable truth surfaces instead of treating logs or transient execution state as the only source of truth.

### 4. Provider-neutral LLM boundary
This is one of the best extensibility decisions already in the repo.
SourceTrace should continue to own:
- task semantics,
- execution intent,
- normalized results,
- operator-facing truth,

while LiteLLM or other providers stay behind a narrow integration seam.

## Where extensibility is still weak

### 1. Too much growth pressure lands in orchestrators
When a system keeps growing by expanding a large worker/runtime file, it becomes harder to:
- add new behavior safely,
- understand lifecycle truth,
- reuse logic across runtimes,
- attach cross-cutting concerns once.

This is the biggest structural risk.

### 2. Cross-cutting concerns do not always have first-class collection seams
Token usage exposed the pattern clearly, but it is broader than token accounting.
The same risk applies to:
- usage receipts,
- prompt provenance,
- retries/attempts,
- latency/cost,
- evaluation traces,
- backend coverage,
- execution diagnostics.

If these are attached manually in feature code, extensibility will degrade as the system grows.

### 3. Stringly-typed semantics will not age well
Free-form labels in progress payloads or worker details are fine for debugging, but they are weak as durable architecture.

If stage semantics, lifecycle meaning, or operator truth depend on ad hoc strings, the system becomes harder to evolve without drift.

### 4. Runtime wiring is still too local in some paths
If adding a new capability requires touching too many places in one runtime path, then the repo is still feature-growth-friendly more than extension-growth-friendly.

That is manageable now, but it will become expensive later.

## Five architectural rules for a modular SourceTrace core

### Rule 1 — Every new responsibility must have a canonical seam
Before adding a feature, answer four questions:
- what is its canonical interface?
- what is its persistence truth?
- what is its execution seam?
- what is its operator-facing truth?

If those answers are unclear, the feature is not ready to be added cleanly.

### Rule 2 — Truth must be artifact-first, not event-first
Events, logs, and progress streams are useful, but they are not the durable truth layer.

Core truth should live in:
- typed artifacts,
- typed records,
- typed repositories,
- typed payload contracts.

Do not make the future system reconstruct important truth from debug/event scraps.

### Rule 3 — Cross-cutting concerns need interception points
Anything that will grow across many features must have a shared capture seam.
Examples:
- LLM usage receipts,
- prompt metadata,
- retries,
- execution provenance,
- evaluation outputs,
- backend coverage.

If capture depends on each call site remembering to do manual bookkeeping, the design is not growth-ready.

### Rule 4 — Business semantics must stay separate from transport/runtime mechanics
Do not collapse:
- task name into business stage,
- provider status into operator meaning,
- result artifact into execution truth,
- compiled artifact into runtime telemetry.

The system becomes easier to extend when these boundaries stay explicit.

### Rule 5 — Prefer composable modules over bigger orchestrators
New capability should usually enter the system as one or more of:
- a new gateway,
- a new evaluator/judge contract,
- a new typed artifact,
- a new repository seam,
- a new runtime adapter,
- a new projection layer.

If the default move is always “grow the worker,” the architecture will eventually fight the product.

## What should not be mistaken for extensibility

### Not this: “everything becomes a plugin”
A plugin platform is not the same thing as a healthy core.
Do not over-abstract prematurely.

### Not this: “one giant orchestrator with many flags”
That looks flexible at first and becomes expensive later.

### Not this: “we can infer it from logs”
That is usually a sign the truth model is underdesigned.

### Not this: “feature shipped” = “core improved”
A system can add features while getting worse at extension.
Those are different curves.

## Practical direction for current SourceTrace
The near-term goal should be:
- keep the current evidence-first product core,
- keep strong boundaries where they already exist,
- stop new cross-cutting behavior from being embedded only in local worker logic,
- introduce stable typed seams where growth is clearly happening.

In plain terms:
- do not let worker growth become the default architecture,
- do not let progress/event strings become durable system semantics,
- do not let runtime-local shortcuts silently define the core.

## Entry into a SourceTrace v2 rewrite
A SourceTrace v2 rewrite is a credible future direction if the goal is to make the core system easier to expand without carrying forward too much patch-layer complexity.

That rewrite should **not** mean abandoning the current thesis.
It should mean preserving the right things and discarding the wrong growth pattern.

### What v2 should preserve
- evidence-first posture,
- claim/review/report separation,
- artifact-oriented truth model,
- provider-neutral LLM boundary,
- explicit operator truth semantics,
- durable inspectability.

### What v2 should reset
- oversized runtime orchestrators as the default growth surface,
- ad hoc stage naming as architecture,
- feature-local bookkeeping for cross-cutting concerns,
- blurred lines between execution truth and knowledge truth,
- too much runtime meaning encoded in local control flow.

### v2 architectural target
A clean v2 should aim for:
- a smaller, harder core,
- typed lifecycle and execution records,
- first-class interception points,
- explicit feature/runtime composition,
- stable projection layers for API/UI/operator surfaces,
- easier addition of new research stages, evaluators, analyzers, and runtimes without editing central orchestration logic every time.

### Practical v2 rule
If a new feature in v2 requires editing the central orchestrator, the runtime adapter, the API projection, and multiple unrelated helpers just to exist, the core is still too soft.
A good v2 should make most extensions feel like adding a bounded module to a stable spine.

## Bottom line
SourceTrace is not yet a uniformly extensible core system.
But it is close enough in structure and strong enough in thesis that pushing toward that direction makes sense.

The key move is this:
**grow the seams, not the orchestrators.**

That principle should guide both:
- current bounded refactors in the existing repo,
- and any future SourceTrace v2 rewrite.