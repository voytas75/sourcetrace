# Deep Research compiled artifact enrichment implementation follow-up — 2026-06-21

Status: implemented
Scope: first improvement pass for `result -> compiled artifact` projection quality.

## What shipped

Implemented `compiled artifact enrichment v1` as a bounded upgrade of the projection layer.

### Added projection helpers
- `_project_supporting_evidence(...)`
- `_project_source_refs(...)`
- `_project_claims(...)`
- `_project_followup(...)`
- `_unique_text_items(...)`

### Updated compiled artifact projection
`_compile_research_artifact(...)` now uses the helper layer instead of a shallow direct copy.

Improved areas:
- stronger source-ref carry-forward
- stronger follow-up carry-forward
- deterministic claim selection/dedup
- deterministic source/evidence dedup
- fallback source projection when the upstream run is sparse

## Verification

### Full repo gate
- `407 passed`

### Runtime spot-check
Executed a real in-memory research run and inspected the enriched compiled artifact + lint.

Observed spot-check output:
- `artifact_id = cra-rj-09f12cad17d8`
- `source_refs = 1`
- `supporting_evidence = 0`
- `next_checks = 1`
- `lint_status = weak`
- `risk_flags = ('missing_evidence', 'weak_source_quality', 'needs_revision')`

## Interpretation

This slice improved the compiled layer, but did not magically turn the artifact healthy.
That is good.

What improved:
- source refs no longer collapse to empty in the sparse spot-check path,
- next-check carry-forward is preserved,
- compiled artifacts are less hollow than before.

What remains weak:
- supporting evidence is still too thin in this runtime spot-check path,
- evaluator-driven weakness still correctly propagates,
- so lint remains meaningfully red rather than falsely green.

## Verdict

This was still the right slice.

The result is not “fixed,” but it is more truthful and less lossy.
We reduced projection loss without faking quality.

## Recommended next slice

`compiled artifact evidence carry-forward v2`

Reason:
- the remaining main weakness is now narrower,
- evidence projection is still too thin in sparse/partial paths,
- and that is a more precise next target than another broad enrichment pass.
