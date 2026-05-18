# SourceTrace Architecture SSOT

Status: draft v0
Scope: canonical product and architecture baseline for the SourceTrace repository

## Purpose
SourceTrace is an application project for building an evidence-centric OSINT + LLM system. This document is the current SSOT for product intent, quality rules, core domain objects, and MVP boundaries.

## Product goal
Build a system that helps an analyst gather sources, preserve raw evidence, extract traceable claims, review them, and generate reports with explicit confidence bands.

## Core product stance
- LLM is an operator on evidence, not the source of truth.
- Raw source preservation is mandatory.
- Every claim must be traceable to one or more concrete evidence chunks.
- Human review remains part of the core workflow.
- Research, planning, and implementation live in one repo, but product truth must stay in canonical docs.

## Confirmed now
- The system should be case-driven, not just document-driven.
- The quality model should be evidence-first and claim-centric.
- MVP should prefer a small number of strong primitives over early graph complexity.
- Required confidence bands in outputs: `potwierdzone`, `prawdopodobne`, `do weryfikacji`.
- The repository should support iterative research → SSOT update → blueprint update → later implementation.
- Contradictory evidence matters and should not be collapsed into a generic low-confidence bucket.
- Claim-focused analyst review is part of the product, not a temporary workaround.
- Workflow logs are not enough; the system needs semantic claim-to-evidence provenance.
- A useful validation triad for MVP is emerging: `support`, `contradict`, `insufficient evidence`.
- Source credibility is a separate signal from claim support and should not override semantic verification.
- Analyst review should use progressive disclosure: overview first, then drill-down evidence and rationale.
- Evidence should be ranked for analyst consumption so sufficient context appears early.
- MVP analyst workflow should follow a layered review path: `review queue -> case overview -> claim workspace -> evidence detail`.
- OSINT-style credibility naming should separate `source_reliability` from `information_credibility`.
- Human review state must remain separate from system verdicts.
- Domain contract layer is now present for cases, documents, chunks, retrieval, claims, review decisions, report entries, and case reports.
- Application contract layer is now present for case intake, document preparation, claim extraction, claim verification, human review, report assembly, and credibility assessment.
- A bounded LLM integration layer is now present under `src/sourcetrace/llm/` with SourceTrace-owned models, config, normalized errors, structured-generation seams, and a first claim-extraction gateway.
- The application layer now includes an LLM-backed claim extraction runtime seam for mapping structured extraction payloads into application claim outcomes.

## Working hypotheses
- Postgres plus pgvector is a sufficient MVP persistence baseline.
- Hybrid retrieval is a better default than pure vector retrieval.
- Graph capabilities should be deferred until later iterations unless new evidence changes that decision.
- API-first model usage is likely the fastest path to quality in MVP.
- Typed provenance relations may become valuable after MVP once basic claim grounding works.
- MVP source reliability / information credibility scoring should start as rule-based provisional bands with analyst override.
- A lightweight contradiction/entailment path for MVP can follow: claim decomposition → evidence matching/ranking → support/contradict/insufficient verdict.
- MVP review workflow can use explicit queue/item states without requiring a heavy workflow engine.

## Do weryfikacji
- Whether MVP should be API-first, local-first, or dual-mode.
- Which PDF/web parser stack should be the default.
- Which exact entailment/NLI component is light enough and good enough for iteration 1.
- What minimum credibility rubric and stored fields should be mandatory from day 1.
- Which source families beyond URL/PDF/RSS should enter MVP.
- Which review interactions are MVP-critical versus iteration-2 nice-to-have.

## Core domain objects
### Case
A bounded investigation context with objective, questions, scope, and status.

### Document
A raw source artifact with metadata, content hash, provenance, ingestion status, and provisional source reliability / information credibility metadata.

### Chunk
An addressable document fragment used for retrieval, evidence linking, and downstream extraction.

### Entity
A detected named object or identifier grounded in one or more chunks.

### Claim
A structured statement extracted from evidence and linked to supporting, contradictory, or insufficient evidence outcomes.

### Review
A human decision attached to a claim, entity, or report, including rationale and optional override notes.

### Report
A synthesized investigation output assembled from reviewed or classified claims.

## MVP boundaries
### In scope
- cases
- URL/PDF/RSS/manual text ingestion
- raw evidence storage
- chunking and embeddings
- entity extraction
- claim extraction
- relevance scoring at a basic level
- evidence ranking at a basic level for analyst review
- validation of schema and evidence links
- contradiction-aware claim validation at a basic level
- provisional source credibility scoring with analyst override
- analyst review
- markdown/html/json reporting

### Out of scope for MVP
- full graph intelligence
- autonomous multi-agent orchestration
- broad social/web crawling at scale
- advanced entity resolution
- multimodal heavy pipeline as a default
- highly granular typed provenance taxonomies
- fully learned black-box credibility scoring as the main trust signal

## Quality rules
1. No claim without evidence links.
2. No report without explicit certainty bands.
3. No pipeline run without auditable model/prompt metadata.
4. Raw evidence and interpretation must remain separate.
5. The analyst must be able to inspect the source path behind each report statement.
6. Contradictory evidence must be preserved and surfaced, not silently merged away.
7. Unverified claims should be gated from stronger report sections.
8. Citation presence alone does not count as support.
9. Source credibility scores are advisory and cannot replace claim-level evidence checks.
10. Review UI should minimize cognitive overload by default and reveal deeper detail on demand.

## Repository document roles
- `docs/architecture/architecture-ssot.md`: canonical product and architecture baseline.
- `docs/research/research-ledger.md`: rolling evidence from reviewed external sources.
- `docs/plans/execution-blueprint-v0.md`: provisional implementation-facing plan, still pre-build.

## Current recommended next step
The initial contract-first baseline is now extended through lower-level seams, a minimal in-memory runtime path, and a minimal analyst-facing delivery surface.

Confirmed now:
- `domain` contracts are in place
- `application` request/outcome contracts are in place
- `application` execution seams are in place for case intake, document preparation, claim extraction, verification, human review, report assembly, and credibility assessment
- lower-level retrieval and persistence seams are in place in `pipeline.interfaces` and `storage.interfaces`
- a first in-memory runtime path is in place for persistence, lexical retrieval, and verification orchestration
- a minimal analyst delivery surface is in place in `web/` with a pure-stdlib WSGI/API, a case HTML view, and report JSON/Markdown output
- that delivery surface now exposes evidence summary fields, explicit missing/invalid status payloads, and a thin-path end-to-end test pack over the in-memory flow
- local verification after the 10.x rollout: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `123 passed`
- local verification after the bounded LLM.x layer + extraction integration rollout: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `157 passed`

Recommended target stack for the next architectural phase:
- Python backend with FastAPI + Pydantic v2 + SQLAlchemy/Alembic
- PostgreSQL + pgvector for primary persistence and vector search
- hybrid retrieval rather than lexical-only retrieval
- Redis-backed background work (RQ preferred for simplicity)
- server-rendered analyst UI with Jinja2 + HTMX
- a dedicated LLM integration layer behind SourceTrace-owned gateways
- LiteLLM as the preferred provider abstraction for LLM communication
- LLM usage focused on extraction, normalization, and drafting; final verification remains grounded in retrieval evidence, NLI/rules, and human review

Next recommended step:
- sync repo-facing docs to the bounded LLM.x baseline so the current architecture truthfully includes the new `llm/` layer and extraction runtime seam
- only then decide whether the next slice is deeper runtime orchestration, storage-backed extraction persistence, or web/API integration for the LLM-backed path
- keep LiteLLM hidden behind the local boundary and avoid leaking provider details upward while broadening integration
- do not jump into broad platformization before those boundaries stay explicit in both code and docs
