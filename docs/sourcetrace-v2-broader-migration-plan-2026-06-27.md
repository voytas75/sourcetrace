# SourceTrace v2 broader migration plan (2026-06-27)

## Verdict
A broader SourceTrace v2 migration now makes sense **as a bounded staged plan**, not as a full parity rewrite mandate.

The right next move is not "migrate everything from v1".
The right next move is to sequence the migration so that each slice proves the v2 spine is buying lower extension cost, better execution truth, and cleaner operator surfaces.

## Current posture
What v2 already proved:
- independent package spine
- runtime config layer
- native logging layer
- typed execution receipts + rollups
- run persistence marker truth
- persisted readback envelope
- minimal HTTP/readback semantics

What v2 has **not** yet proved:
- real search/retrieval input
- one meaningful Deep Research workflow with live evidence input
- richer result artifact/operator output
- independent operator surface beyond minimal JSON path
- job lifecycle beyond the current minimal path
- broader parity for documents/cases/verification/credibility

## Planning rule
Do not migrate feature-by-feature from the edge of the old UI.
Do not treat v1 parity as the default goal.

Instead:
1. prove one more real capability on the v2 spine,
2. verify that inspectability and extension cost stay good,
3. only then widen the surface.

## Recommended bounded slices

### Slice 1 — Real search adapter + retrieval input path
**Goal**
Move v2 from stubbed proof to one real external evidence-input seam.

**Scope**
- add one concrete search adapter under `adapters/search/`
- add one bounded retrieval input contract
- capture provenance/receipt truth for retrieved evidence candidates
- keep provider plurality out of scope

**DoD**
- v2 can execute one bounded run with real search input
- execution truth shows where evidence candidates came from
- result/readback projection exposes the retrieved-source provenance clearly
- tests cover adapter seam and the end-to-end bounded path

**Why this is next**
This is the smallest slice that moves v2 from architecture proof toward real usefulness.

---

### Slice 2 — One meaningful Deep Research workflow on v2
**Goal**
Port one real workflow, not the whole v1 `research_runtime.py`.

**Scope**
- planning
- query refinement
- retrieval/search input
- evidence judge
- synthesis
- bounded result artifact

**Out of scope**
- full Deep Research parity
- background/runtime sophistication
- broad UI
- PDF richness

**DoD**
- one meaningful research workflow runs end-to-end on the v2 spine
- stage boundaries remain explicit and receipts stay truthful
- adding or modifying one stage remains bounded

---

### Slice 3 — Compiled artifact / operator projection parity-lite
**Goal**
Give v2 a more operator-useful output surface than thin result/readback alone.

**Scope**
- one compiled artifact projection
- compact diagnostics/supporting metadata
- explicit links back to execution truth

**Out of scope**
- full v1 compiled artifact sophistication
- broad export family

**DoD**
- operator can inspect one coherent artifact containing result + provenance + execution truth
- projection stays layered over typed artifacts/receipts rather than ad hoc runtime state

---

### Slice 4 — Web/API surface for one operator path
**Goal**
Expose one genuinely useful operator path directly from v2.

**Scope**
- one run endpoint
- one status/readback endpoint
- optional one minimal HTML/operator view only if it materially improves inspection

**Out of scope**
- full `web/api.py` parity
- cases/documents surface
- broad delivery/UI work

**DoD**
- a v2 workflow can be run and inspected without leaning on the old delivery path
- transport semantics stay thin and projection-driven

---

### Slice 5 — Background/job lifecycle parity-lite
**Goal**
Add the smallest healthy job lifecycle only if earlier slices prove it is worth carrying forward.

**Scope**
- queued / running / done / error
- one bounded async/queue seam
- minimal persistence/status projection

**Out of scope**
- advanced scheduler behavior
- broad orchestration engine work
- multi-backend queue abstraction

**DoD**
- v2 can support a basic job lifecycle beyond inline execution
- execution truth remains stable across async boundaries

---

### Slice 6 — Decide the next migration branch
**Goal**
Choose whether v2 should widen further into research product surface or analyst workflow surface.

**Decision branch**
Choose based on evidence from slices 1–5:
- `research-first`: continue on Deep Research product/runtime/operator surface
- `analyst-workflow-first`: move into documents / cases / verification / credibility
- `research-core only`: stop broad migration and keep v2 as a narrower stronger core

**DoD**
- the next branch is chosen from observed value and extension cost, not from parity pressure alone

## Guardrails
- Do not widen to many providers early.
- Do not migrate the old monolithic orchestration shape into v2.
- Do not make v2 core depend on v1 runtime modules.
- Do not bring in cases/documents/verification just because they exist in v1.
- Do not add broad UI before one genuinely useful operator path exists.
- Prefer one real capability proof over many skeletal module additions.

## Recommended next slice
**Slice 1 — Real search adapter + retrieval input path**

Reason:
- it is the smallest move that tests whether v2 can carry real evidence input,
- it improves usefulness without forcing full Deep Research parity,
- it gives better information for deciding the pace of broader migration.

## Bottom line
The broader v2 plan should be:

`real search/retrieval -> one real research workflow -> operator artifact projection -> one independent operator surface -> minimal job lifecycle -> explicit branch decision`

That is a healthier migration path than trying to force immediate parity with the whole v1 surface.
