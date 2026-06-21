# Deep Research compiled research artifact implementation follow-up — 2026-06-21

Status: implemented
Scope: first compiled research artifact layer added on top of Deep Research result artifacts.

## What shipped

Implemented `compiled research artifact v1` as an additive layer above completed research runs.

### Added domain objects
- `CompiledResearchArtifact`
- `CompiledResearchClaim`
- `CompiledResearchEvidenceRef`

### Added persistence seam
- `CompiledResearchArtifactRepository`
- wired into `ResearchPersistence.compiled`

### Added storage implementations
- `InMemoryCompiledResearchArtifactRepository`
- `FileBackedCompiledResearchArtifactRepository`
- separate filesystem namespace under `data/research/compiled/`

### Added runtime transformation
- `_compile_research_artifact(result: ResearchResultArtifact) -> CompiledResearchArtifact`
- auto-compilation wired on completed successful result persistence paths

### Added retrieval path
- `GET /api/research/compiled/{artifact_id}`
- `GET /api/research/compiled?owner_id=...`

## Current artifact posture

Compiled artifacts currently carry:
- `artifact_id`
- `source_job_id`
- `owner_id`
- `query`
- `query_class`
- `title`
- `summary`
- `current_answer`
- `key_claims`
- `supporting_evidence`
- `open_questions`
- `next_checks`
- `source_refs`
- `evaluation_snapshot`
- `created_at`

This is intentionally small and additive.

## Verification

### Full repo gate
- `405 passed`

### Runtime spot-check
Executed a real in-memory research run and confirmed compiled artifact persistence.

Observed spot-check output:
- `job_id = rj-7c662f1a6c88`
- `artifact_id = cra-rj-7c662f1a6c88`
- `title = how to deploy configuration baselines in sccm`
- `query_class = procedural_admin`
- `has_eval = True`

## Notes

This slice deliberately does **not** yet do:
- cross-run merge/dedup
- artifact health/lint
- rich compiled-artifact UI
- branch/follow-up proposal generation

Those now have a real substrate to build on.

## Verdict

This was the right next slice after evidence packing.

The system now has a first real bridge from:
- ephemeral run result

to:
- reusable compiled research artifact

That is the minimum durable knowledge layer needed before artifact lint / health and follow-up branch logic can make sense.

## Recommended next slice

`artifact lint / health v1`

Reason:
- compiled artifacts now exist,
- evaluator snapshots are preserved with them,
- and the next useful step is to check artifact completeness, brittleness, stale uncertainty, and weak evidence packing outcomes in a structured way.
