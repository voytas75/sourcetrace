# SourceTrace v2 full closure map — 2026-06-27

## Goal

Close SourceTrace v2 as a small but real system without widening into v1 parity work.

This map assumes the following are already done:
- runtime spine
- runtime/bootstrap correction
- execution-truth receipts
- persistence marker + persisted readback envelope
- retrieval stage + evidence-input projection
- one real provider-backed search path (SearxNG)
- Unified Search readiness with fallback
- retrieval-aware result summary
- compact `selected_evidence` projection

## What “full v2” should mean

A full v2 should be:
- end-to-end runnable,
- persistently inspectable,
- evidence-aware,
- minimally knowledge-bearing,
- quality-checkable,
- still bounded.

It should **not** mean:
- full v1 feature parity,
- broad provider breadth,
- queue/background sophistication,
- large orchestration framework work.

## Closure slices

### Slice 1 — selected-evidence policy v1

Upgrade `selected_evidence` from pure top-rank carry-forward to one bounded quality rule.

Target:
- keep the current projection contract,
- add one simple deterministic selection rule beyond rank,
- preserve inspectability.

Examples of acceptable bounded rules:
- prefer unique providers/domains when ties are close,
- require non-empty title/url/snippet shape for promotion,
- cap promotion to evidence that survives one minimal relevance guard.

DoD:
- `selected_evidence` still exists as a compact projection,
- at least one non-rank rule is encoded and tested,
- existing `evidence_input` raw block remains intact.

### Slice 2 — explain/debug contract v1

Expose why evidence was selected instead of only what was selected.

Target:
- compact operator/debug fields,
- no large scoring subsystem,
- no hidden heuristics.

Candidate fields:
- `selection_basis`,
- `selection_notes`,
- `dropped_count`,
- optional compact `rejected_reasons` summary.

DoD:
- minimal/result/readback payloads show compact selection explanation,
- tests pin the new fields,
- empty/partial/not-found paths still project cleanly.

### Slice 3 — compiled artifact contract v1

Create the first minimal knowledge-layer artifact above the run artifact.

Target:
- separate reusable research truth from one run result,
- keep the contract compact.

Candidate fields:
- `artifact_id`,
- `job_id`,
- `run_id`,
- `summary`,
- `selected_evidence`,
- optional `status` or `confidence_note`.

DoD:
- compiled artifact dataclass/contract exists,
- one projection exists,
- artifact is derived from current run artifact without introducing a large new pipeline.

### Slice 4 — compiled artifact persistence + readback v1

Make the compiled artifact durable and inspectable.

Target:
- separate persistence/readback seam,
- same bounded read-model discipline used for run persistence.

DoD:
- compiled artifact can be saved and loaded,
- one HTTP/readback path exists,
- incomplete/absent states are explicit if needed,
- focused tests pin persistence and projection behavior.

### Slice 5 — eval corpus v1

Add a small but real retrieval/evidence-selection evaluation set.

Target:
- confidence over behavior,
- not benchmark theater.

Suggested size:
- 5–10 representative queries,
- expected retrieval/evidence-shape assertions,
- at least one stub path and one provider-backed path.

DoD:
- corpus lives in repo,
- assertions are runnable,
- slices above can be checked against stable expectations.

### Slice 6 — bounded benchmark/quality pass

Run one small quality pass over retrieval + selected evidence.

Target:
- prove the current bounded system is coherent,
- identify the next real weakness from evidence, not taste.

DoD:
- one short report/checkpoint note exists,
- findings distinguish structural gaps from content/provider gaps,
- next recommended slice is justified by results.

## Recommended order

1. compiled artifact contract v1
2. compiled artifact persistence + readback v1
3. selected-evidence policy v1
4. explain/debug contract v1
5. eval corpus v1
6. bounded benchmark/quality pass

## Why this order

- The next biggest missing system boundary is the knowledge layer, not another provider.
- `selected_evidence` is already present, so it can be improved after the compiled artifact has a place to land.
- Eval/benchmarking becomes more useful once the output surfaces are closer to the intended v2 shape.

## Non-goals for this closure map

Do not widen this map into:
- full evidence packing parity with v1,
- background worker architecture,
- broad provider fan-out,
- memory system integration,
- large UI delivery work.

## Practical verdict

If these six slices are closed cleanly, v2 should count as a real, bounded, independently defensible system rather than an architecture proving branch.
