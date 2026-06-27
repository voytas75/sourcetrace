# SourceTrace v2 package layout (2026-06-27)

## Verdict
SourceTrace v2 should be built as an **independent system**, not as a thin continuation of v1 internals.

That does not mean ignoring what v1 learned.
It means v2 should reuse lessons, not inherit structural coupling.

So the package layout should be designed around a new stable spine, with clear boundaries and minimal dependency backflow into v1-era runtime shapes.

## Core rule
V2 should be able to evolve on its own terms.

That means:
- no hidden dependency on v1 runtime modules,
- no importing v1 orchestrators into v2 core,
- no “temporary” direct reuse of v1 internals that become permanent,
- reuse only through explicit, bounded migration/reference layers when necessary.

## Layout goal
The package layout should make it obvious:
- where business truth lives,
- where execution composition lives,
- where adapters live,
- where projections live,
- where config/logging/receipts live,
- and what is explicitly outside the core.

## Recommended top-level shape

```text
src/sourcetrace_v2/
  core/
    domain/
    contracts/
    policies/
  execution/
    context/
    stages/
    workflows/
    receipts/
    rollups/
  runtime/
    config/
    logging/
    bootstrap/
  adapters/
    llm/
    search/
    pdf/
    storage/
    queue/
  projections/
    api/
    html/
    diagnostics/
    exports/
  app/
    services/
    composition/
  testsupport/
```

This is a recommendation, not a prison. But the shape should stay close to this intent.

## Package roles

### `core/`
The stable heart of v2.

Contains:
- domain types,
- stable business contracts,
- policies that define business meaning,
- enums/identifiers for features/stages/statuses.

Must avoid:
- provider specifics,
- web specifics,
- queue specifics,
- runtime adapter details.

### `execution/`
The execution spine.

Contains:
- execution context,
- stage module contracts,
- workflow composition,
- receipt emission,
- rollup logic.

This is where bounded workflow assembly happens.
It should not become a giant bag of business rules or adapter-specific hacks.

### `runtime/`
Cross-cutting runtime support.

Contains:
- config schema and loader,
- logical profile resolution,
- native logging setup,
- correlation context,
- runtime bootstrap support.

This is the right home for config/logging mechanics that are broader than one feature.

### `adapters/`
External integration edges.

Contains:
- LLM adapters,
- search adapters,
- PDF adapters,
- storage adapters,
- queue/background adapters.

Rule:
this layer translates external systems into v2 contracts.
It should not become the place where core business semantics are invented.

### `projections/`
Operator- and output-facing views.

Contains:
- API payload projections,
- HTML projections,
- diagnostics projections,
- export projections.

These should project from typed artifacts and receipts, not from random runtime state.

### `app/`
Application assembly.

Contains:
- service entrypoints,
- composition roots,
- feature assembly,
- boot wiring.

This layer glues the system together.
It should stay thinner than v1-style orchestration-heavy runtime files.

## What should stay out of the core package layout
Do not fold these into core:
- provider bootstrap code,
- LiteLLM-specific logic,
- HTTP framework concerns,
- local launcher specifics,
- raw logging sink mechanics,
- temporary migration shims.

Keep the core hard and small.

## v1 relation rule
If v2 needs to reference v1 during transition, do it only through explicit migration/reference utilities outside the core spine.

For example:

```text
src/sourcetrace_v2/
  migration/
    v1_reference/
    importers/
    mappers/
```

But do **not** make `core/`, `execution/`, or `runtime/` depend on v1 modules.

## Testing implication
The layout should support tests by layer:
- `core` unit tests
- `execution` stage/workflow tests
- `runtime` config/logging tests
- `adapter` integration tests
- `projection` tests
- one or two end-to-end vertical slice tests

If testing a small concept requires booting the whole app, the layout is too entangled.

## Logging and receipts placement
Important explicit split:
- `runtime/logging/` owns logger setup, formatter, correlation helpers
- `execution/receipts/` owns typed execution receipts and receipt collection

Do not mix those two concerns into one module tree.

## Config placement
Important explicit split:
- `runtime/config/` owns loading, validation, profile resolution
- `core/policies/` owns business policy meaning

That avoids config becoming business truth by accident.

## Minimal first implementation target
For the first bounded implementation slice, it is enough to flesh out:
- `core/domain/`
- `core/contracts/`
- `execution/context/`
- `execution/stages/`
- `execution/receipts/`
- `runtime/config/`
- `runtime/logging/`
- `adapters/llm/`
- `projections/api/`
- `app/composition/`

The rest can stay skeletal.

## Bottom line
SourceTrace v2 should have a package layout that makes independence from v1 real, not rhetorical.

The main rule is simple:
**v2 may learn from v1, but core v2 must not be structurally downstream of v1.**
