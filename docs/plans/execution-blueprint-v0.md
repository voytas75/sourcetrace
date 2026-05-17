# SourceTrace Execution Blueprint v0

Status: provisional
Mode: research-first, no implementation yet
Purpose: describe the intended module boundaries, build order, open questions, and decision gates before implementation begins.

> This is not an implementation-ready plan. It is a living bridge between research and later execution.

## Goal
Prepare SourceTrace to move from research into a bounded MVP build without locking in architecture too early.

## Build principle
Prefer a small number of strong, auditable primitives over broad early feature coverage.

## Confirmed now
- SourceTrace should remain case-driven and evidence-first.
- MVP should preserve raw sources and structured claim evidence links.
- Modular separation is desirable, but the codebase should stay lightweight until implementation is approved.
- Research updates should patch this blueprint before any implementation-ready plan is frozen.
- Contradiction-aware validation is important enough to shape the design before implementation starts.
- Analyst review is a core workflow surface, not a reporting afterthought.
- Progressive disclosure is the right default for analyst review UX.
- Source reliability / information credibility should be implemented as advisory triage, not as a substitute for claim validation.
- Basic evidence ranking belongs in the MVP plan because it reduces analyst reading load.
- MVP analyst review should follow a layered path: review queue, case overview, claim workspace, evidence detail.
- Human review state should be stored separately from system verdicts.
- Domain contract coverage is in place for cases, documents, chunks, retrieval, claim verification flow, and case-level report output.
- Application contract coverage is in place for case intake, document preparation, claim extraction, claim verification, human review, report assembly, and credibility assessment.

## Working hypotheses
- Iteration 1 can fit inside a single Python backend plus a minimal web UI.
- Package boundaries should follow domain and workflow concerns, not framework defaults.
- A future graph layer should fit into the same domain model rather than reshape it.
- MVP can begin with simple provenance links, while leaving room for typed provenance relations later.
- MVP contradiction validation can likely be implemented as a 3-step flow: claim decomposition, evidence attribution/ranking, aggregated verdict.
- MVP source reliability / information credibility scoring can start with explicit criteria and bands rather than opaque scalar trust scores.
- MVP review queue can use explicit item states such as `new`, `triaged`, `in_review`, `on_hold`, `resolved`, `escalated`.

## Do weryfikacji
- final tech stack choices for parser, LLM provider mode, and retrieval/reranking details
- whether review UX should be server-rendered first or API + separate frontend
- what minimum source set defines MVP readiness
- which exact entailment/NLI path is sufficient for the first usable build
- which review interactions belong in MVP versus iteration 2

---

## Planned module map

### 1. Domain layer
Purpose: stable business objects and contracts.

Planned concerns:
- cases
- documents
- chunks
- entities
- claims
- reviews
- reports
- run metadata
- claim-evidence relations
- credibility assessments

Expected package path:
- `src/sourcetrace/domain/`

### 2. Application layer
Purpose: orchestrate use cases without owning storage or UI.

Planned concerns:
- create case
- ingest source into case
- chunk and enrich document
- extract entities and claims
- validate claims
- assemble report
- review workflow actions
- credibility assessment workflow

Expected package path:
- `src/sourcetrace/application/`

### 3. Pipeline layer
Purpose: operational processing steps and adapters around extraction/retrieval flows.

Planned concerns:
- ingestion pipeline
- chunking pipeline
- extraction pipeline
- validation pipeline
- retrieval strategies
- evidence ranking
- reporting assembly
- source reliability / information credibility enrichment

Expected package path:
- `src/sourcetrace/pipeline/`

### 4. Storage layer
Purpose: isolate persistence and search implementation details.

Planned concerns:
- case/document/claim repositories
- raw artifact storage
- vector and full-text search adapters
- run logging persistence
- provenance link persistence
- credibility metadata persistence

Expected package path:
- `src/sourcetrace/storage/`

### 5. Web/API layer
Purpose: delivery interface for analyst workflows and machine access.

Planned concerns:
- API routes
- HTML views or minimal frontend handlers
- claim review screens
- report export endpoints
- review queue / triage views
- health/status endpoints later

Expected package path:
- `src/sourcetrace/web/`

### 6. Shared/config layer
Purpose: settings, types, utility glue kept intentionally narrow.

Expected package path:
- `src/sourcetrace/config/`
- `src/sourcetrace/shared/`

---

## Planned top-level repository structure

### Product code
- `src/sourcetrace/`
  - `domain/`
  - `application/`
  - `pipeline/`
  - `storage/`
  - `web/`
  - `config/`
  - `shared/`

### Tests
- `tests/unit/`
- `tests/integration/`
- `tests/fixtures/`

### Scripts
- `scripts/`
  - dev/bootstrap helpers later
  - data import/export helpers later

### Docs
- `docs/architecture/`
- `docs/research/`
- `docs/plans/`

### Working notes
- `notes/`

### Data areas
- `data/raw/`
- `data/processed/`
- `data/reports/`

---

## Pre-implementation build order

### Phase A — research consolidation
Entry condition:
- continue source review cycles
- revise SSOT and this blueprint

Outputs:
- refined domain model
- narrowed MVP source set
- narrowed retrieval and parser assumptions
- narrowed contradiction-handling assumptions
- provisional source reliability / information credibility rubric
- narrowed analyst review assumptions

### Phase B — implementation readiness decision
Entry condition:
- major architecture questions reduced to manageable `do weryfikacji`

Outputs:
- implementation-ready plan
- first bounded slice definition
- candidate stack freeze for iteration 1
- explicit MVP review workflow

### Phase C — bounded MVP implementation
Not started yet.
Will begin only after a dedicated implementation plan is written and approved.

---

## Decision gates before implementation

### Gate 1: product scope freeze
Questions:
- Which source types are mandatory in iteration 1?
- What exact analyst workflow is supported end-to-end?
- What review actions are required before reporting?
- What minimum source reliability / information credibility rubric must be stored from day 1?

### Gate 2: storage and retrieval freeze
Questions:
- Is Postgres + pgvector still sufficient after further research?
- Do we need reranking in iteration 1 or can it wait?
- Is hybrid retrieval mandatory for the first usable cut?
- How explicit should evidence ranking be in analyst-facing results?

### Gate 3: extraction and validation contract freeze
Questions:
- What JSON schemas define entities, claims, and validations?
- What minimum support checks are required before a claim becomes report-eligible?
- How are supportive versus contradictory versus insufficient links represented?
- Which exact entailment/NLI component will power the first verifier?

### Gate 4: delivery surface freeze
Questions:
- Minimal web UI first, or API-first with very thin views?
- What report formats are mandatory in iteration 1?
- What claim-review affordances are required in the first analyst UI?
- Which progressive-disclosure layers are mandatory in MVP?

---

## Research-to-plan update rule
When a new source materially changes assumptions about:
- data model,
- retrieval,
- validation,
- analyst review,
- reporting,
- credibility scoring,

then patch:
1. `docs/research/research-ledger.md`
2. `docs/architecture/architecture-ssot.md` if product truth changed
3. `docs/plans/execution-blueprint-v0.md` if module or build-order assumptions changed

---

## Current recommended next research slice
1. parser stack and ingestion defaults
2. retrieval/reranking depth for iteration 1
3. execution-side seam design for `application -> pipeline/storage` (`6.x` plan before concrete adapters)

## Later at execution start
When implementation is explicitly approved, create a new implementation-ready plan that includes:
- exact files to create/modify
- bounded task slices
- verification commands
- initial test strategy
- first implementation milestone
