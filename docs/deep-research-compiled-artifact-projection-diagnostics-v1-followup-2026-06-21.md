# Deep Research compiled artifact projection diagnostics v1 follow-up — 2026-06-21

Status: completed diagnostic slice
Scope: identify the exact runtime input shape reaching compiled artifact projection in the previously failing spot-check path.

## What we found

The failing spot-check path was not actually exercising a markdown-shaped research result.

Observed runtime projection input snapshot:
- `result.result = "ok"`
- `raw_report = "ok"`
- `raw_findings_count = 0`
- `sources_count = 0`
- extracted `Current answer = ""`
- extracted `Key findings = ()`
- extracted `Next checks = ()`

This means the projection layer had almost nothing to work with.

## Conclusion

The persistent `missing_evidence` result in that specific spot-check path was **not** evidence that compiled projection heuristics were fundamentally broken.
It was mainly a harness artifact:
- the synthetic completion function used for the runtime spot-check returned only `"ok"`,
- so the compiled artifact projection received a structurally empty report.

That made the spot-check too weak to represent real compiled-artifact quality.

## Verification after fixing the harness shape

Ran the same runtime spot-check with a markdown-shaped synthesis response containing:
- `## Current answer`
- `## Key findings`
- `## Uncertainty`
- `## Next checks`

Observed result:
- `artifact_id = cra-rj-834b02d26dbf`
- `supporting_evidence = 3`
- `source_refs = 3`
- `next_checks = 2`
- `lint_status = weak`
- `risk_flags = ('weak_source_quality', 'needs_revision')`

## Interpretation

This is the key result:
- `missing_evidence` disappeared
- `missing_sources` disappeared
- follow-up structure is present
- remaining weakness is now evaluator-driven, not projection-collapse-driven

That is much healthier.

## Verdict

The diagnostics slice paid off.
It showed that the earlier red signal mixed two things:
1. real evaluator caution
2. a misleadingly thin runtime spot-check harness

After correcting the harness shape, the compiled artifact layer behaves much closer to expectations.

## Recommended next step

No immediate new projection heuristic slice is required.

The next sensible move is either:
- return to benchmark-driven Deep Research quality work,
- or tighten the runtime spot-check harness/docs so future checks use markdown-shaped synthesis by default.
