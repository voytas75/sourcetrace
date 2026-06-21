# Deep Research runtime spot-check harness hardening follow-up — 2026-06-21

Status: implemented
Scope: prevent misleading runtime spot-check results caused by underspecified synthetic research synthesis output.

## What shipped

Implemented a small hardening layer in `local_launcher` for research runtime spot-check paths.

### Main change
Added a wrapper:
- `_research_synthesis_with_markdown_fallback(...)`

Behavior:
- if the research synthesis output already looks like a proper Deep Research markdown result, keep it,
- if it returns an underspecified body such as `"ok"`, replace it with a minimal markdown-shaped fallback containing:
  - `## Current answer`
  - `## Key findings`
  - `## Uncertainty`
  - `## Next checks`

This keeps runtime spot-checks aligned with the actual contract expected by compiled artifact projection and lint layers.

## Why this matters

Without this hardening, a synthetic spot-check could accidentally test a degenerate output shape and then falsely implicate the compiled artifact layer.

This happened in the earlier diagnostic pass:
- `result.result = "ok"`
- no sections
- no findings
- no sources

That was not a representative Deep Research synthesis result.

## Verification

### Focused launcher tests
- added coverage for runtime build path with underspecified `research_synthesis`
- focused launcher tests passed

### Full repo gate
- `409 passed`

## Verdict

This was the right cleanup slice.

It does not change product behavior for proper synthesis output.
It only hardens synthetic/runtime verification paths so the checks stay meaningful.

## Practical outcome

Future runtime spot-checks are less likely to produce false negatives against:
- compiled artifact projection
- artifact lint / health
- evidence carry-forward logic

That reduces diagnostic noise and keeps benchmark/runtime signals more trustworthy.
