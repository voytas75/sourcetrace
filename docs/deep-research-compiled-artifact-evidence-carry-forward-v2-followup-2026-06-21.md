# Deep Research compiled artifact evidence carry-forward v2 follow-up — 2026-06-21

Status: implemented
Scope: narrow evidence fallback upgrade for compiled artifact projection.

## What shipped

Implemented `compiled artifact evidence carry-forward v2`.

### Main change
`_project_supporting_evidence(...)` now has an additional report-derived fallback chain:
1. raw findings
2. result sources
3. report `## Key findings`
4. report `## Current answer`

Report-derived fallback refs use explicit synthetic internal refs such as:
- `about:report/{job_id}#key-findings-1`
- `about:report/{job_id}#current-answer`

That keeps the fallback truthful instead of pretending to be an external source.

## Verification

### Full repo gate
- `408 passed`

### Focused test added
Confirmed that report-only fallback produces non-empty supporting evidence in a sparse result shape.

### Runtime spot-check
Executed a real in-memory research run again.

Observed spot-check output:
- `artifact_id = cra-rj-550afb25cb69`
- `supporting_evidence = 0`
- `lint_status = weak`
- `risk_flags = ('missing_evidence', 'weak_source_quality', 'needs_revision')`

## Interpretation

The v2 fallback works for the narrow sparse-result shape covered by tests, but the runtime spot-check still stayed empty.
That means the remaining issue is now narrower and more concrete:

- the actual runtime result shape in this path is not exposing usable `Key findings` / `Current answer` text to the projection in the way this fallback expects,
- or the report body being passed into compiled projection differs from the synthetic test shape enough that the fallback still does not trigger.

So this slice was still useful: it proved one fallback layer, but it did not yet fix the real runtime path.

## Verdict

This was a valid narrowing slice, not the final fix.

We now know:
- the problem is no longer conceptual,
- it is in the exact runtime report/result shape reaching compiled projection.

## Recommended next slice

`compiled artifact projection diagnostics v1`

Reason:
- we now need one tight instrumentation/debug slice,
- specifically to inspect the exact runtime `result.result`, `raw_report`, `raw_findings`, and `sources` shape at compile time for the failing path,
- then patch the projection against that actual structure instead of guessing another fallback.
