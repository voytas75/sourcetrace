# Deep Research artifact lint / health implementation follow-up — 2026-06-21

Status: implemented
Scope: first deterministic lint / health layer for compiled research artifacts.

## What shipped

Implemented `artifact lint / health v1` as a separate diagnostic layer over compiled research artifacts.

### Added domain model
- `CompiledResearchArtifactLintStatus`
- `CompiledResearchArtifactLint`

### Added persistence seam
- `CompiledResearchArtifactLintRepository`
- wired into `ResearchPersistence.compiled_lint`

### Added storage implementations
- `InMemoryCompiledResearchArtifactLintRepository`
- `FileBackedCompiledResearchArtifactLintRepository`
- separate filesystem namespace:
  - `data/research/compiled-lint/`

### Added deterministic lint function
- `_lint_compiled_research_artifact(artifact: CompiledResearchArtifact) -> CompiledResearchArtifactLint`

### Current lint checks
- structural completeness
- evidence presence / weakness
- source ref presence
- evaluator snapshot presence
- evaluator weakness / revise signals
- open questions without next checks

### Added automatic lint persistence
When a compiled artifact is produced, a lint artifact is now generated and persisted automatically.

### Added retrieval path
- `GET /api/research/compiled/{artifact_id}/lint`

## Verification

### Full repo gate
- `406 passed`

### Runtime spot-check
Executed a real in-memory research run and confirmed lint persistence.

Observed spot-check output:
- `artifact_id = cra-rj-c628fd0d60f0`
- `lint_id = crl-cra-rj-c628fd0d60f0`
- `status = weak`
- `risk_flags = ('missing_evidence', 'missing_sources', 'weak_source_quality', 'needs_revision')`
- `next_action = revise_artifact`

## Interpretation

The spot-check output is actually useful.
It shows the new lint layer is not decorative: it is willing to call out that the current compiled artifact projection is still thinner than the underlying runtime quality work deserves.

That means the system now has an explicit pressure signal for the next layer of work.

## Verdict

This was the correct slice after compiled artifacts.

The Deep Research stack now has:
1. run result
2. evaluator
3. compiled artifact
4. artifact health/lint

That is a credible minimal knowledge-work chain.

## Recommended next slice

`compiled artifact enrichment v1`

Reason:
- the new lint surfaced a real weakness,
- current compiled artifact projection is still too thin on evidence/source carry-forward,
- and the next useful move is not more lint sophistication,
- it is improving the artifact projection so healthy artifacts can actually become healthy.
