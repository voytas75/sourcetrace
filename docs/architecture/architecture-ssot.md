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

## Working hypotheses
- Postgres plus pgvector is a sufficient MVP persistence baseline.
- Hybrid retrieval is a better default than pure vector retrieval.
- Graph capabilities should be deferred until later iterations unless new evidence changes that decision.
- API-first model usage is likely the fastest path to quality in MVP.
- Typed provenance relations may become valuable after MVP once basic claim grounding works.

## Do weryfikacji
- Whether MVP should be API-first, local-first, or dual-mode.
- Which PDF/web parser stack should be the default.
- Whether source reliability scoring should be rule-based or model-assisted in iteration 1.
- Which source families beyond URL/PDF/RSS should enter MVP.
- What the lightest acceptable contradiction/entailment validation path is for iteration 1.

## Core domain objects
### Case
A bounded investigation context with objective, questions, scope, and status.

### Document
A raw source artifact with metadata, content hash, provenance, and ingestion status.

### Chunk
An addressable document fragment used for retrieval, evidence linking, and downstream extraction.

### Entity
A detected named object or identifier grounded in one or more chunks.

### Claim
A structured statement extracted from evidence and linked to supporting or contradictory chunks.

### Review
A human decision attached to a claim, entity, or report.

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
- validation of schema and evidence links
- contradiction-aware claim validation at a basic level
- analyst review
- markdown/html/json reporting

### Out of scope for MVP
- full graph intelligence
- autonomous multi-agent orchestration
- broad social/web crawling at scale
- advanced entity resolution
- multimodal heavy pipeline as a default

## Quality rules
1. No claim without evidence links.
2. No report without explicit certainty bands.
3. No pipeline run without auditable model/prompt metadata.
4. Raw evidence and interpretation must remain separate.
5. The analyst must be able to inspect the source path behind each report statement.
6. Contradictory evidence must be preserved and surfaced, not silently merged away.
7. Unverified claims should be gated from stronger report sections.

## Repository document roles
- `docs/architecture/architecture-ssot.md`: canonical product and architecture baseline.
- `docs/research/research-ledger.md`: rolling evidence from reviewed external sources.
- `docs/plans/execution-blueprint-v0.md`: provisional implementation-facing plan, still pre-build.

## Current recommended next step
Continue structured research and use each cycle to either strengthen or revise:
- MVP storage assumptions,
- retrieval strategy,
- extraction contract design,
- contradiction handling,
- analyst review workflow,
- reporting contract.
