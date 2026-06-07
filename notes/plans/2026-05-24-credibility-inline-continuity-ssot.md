# Plan SSOT — credibility inline-content continuity across input paths

Status: slice 1 completed, continuity fix live-verified
Parent context: `docs/plans/2026-05-24-structured-credibility-fields-plan.md`
Related evidence:
- manual live runs from 2026-05-24 across BBC-like manual note, Reuters, and World Bank examples
- `docs/plans/2026-05-24-live-credibility-rerun-b3.md`
- `docs/plans/2026-05-24-credibility-debug-pipeline-capture.md`
- `docs/plans/2026-05-24-credibility-inline-continuity-checkpoint.md`
Related stable docs:
- `docs/plans/2026-05-24-cross-bucket-closeout.md`
- `docs/plans/2026-05-24-credibility-policy-closeout.md`
- `docs/plans/2026-05-26-source-trace-research-to-backlog-plan.md`

## Why this slice now
Manual live verification stopped pointing first to bad source scoring.

Across multiple source classes, the repeated operator-visible gap was narrower and more actionable:
- `source_reliability` behaved broadly sensibly,
- `information_credibility` became more useful when the credibility path saw real excerpt text,
- but dev-seeded inline documents were degrading into metadata-only credibility drafts with messages like:
  - `No prepared source text was provided`
  - `No source text provided`
  - `No prepared source text to assess`

The same or very similar inline text, when attached through the case/document flow, yielded richer excerpt-aware credibility output.

That made the real decision not “improve scoring” in general, but whether to unify the credibility input continuity contract across input paths.

## Real decision
This was primarily an **input continuity / delivery-to-credibility seam** slice.

The goal was:
- make credibility assessment reuse available inline document text when prepared chunks are missing,
- so equivalent inline content does not produce materially different credibility drafts depending only on how the document entered the system.

This is still not a broad scoring or prompt-quality project.

## Confirmed evidence
### Confirmed before fix
From earlier live manual runs:
- health and launcher were green,
- POST/GET credibility seam persisted assessments correctly,
- structured credibility output (`summary`, `strengths`, `concerns`, `verification_checks`, typed bands, factor arrays) surfaced correctly,
- Reuters-like and World Bank-like sources could get `source_reliability: high`,
- case/document flow produced richer excerpt-aware `information_credibility` assessments than equivalent dev-seeded flows,
- dev-seeded flows repeatedly emitted metadata-only concerns about missing prepared/source text even when inline `text` had been seeded.

### Confirmed during this slice
The bounded route-level fix plus live capture established:
- explicit `POST /api/documents/{id}/prepare` creates stored chunks with expected `raw_text`,
- `POST /api/documents/{id}/credibility` can consume those chunks and produce excerpt-aware `high / medium` credibility output,
- after adding route-level auto-prepare for credibility, a fresh live dev-seeded World Bank rerun without explicit `prepare` also produced:
  - stored chunks visible via `GET /api/documents/{id}/chunks`,
  - `source_reliability: high`,
  - `information_credibility: medium`,
  - no missing-source-text fallback.

### Reclassified conclusion
The active continuity bug was in the credibility route path, not in:
- chunk persistence,
- `_prepared_text_excerpt(...)`,
- or the core credibility runtime parser.

## What changed
### Production change
Bounded continuity fix in:
- `src/sourcetrace/web/api.py`

Behavior change:
- before `POST /api/documents/{id}/credibility` delegates to assessment,
- if the document has no prepared chunks but does have `inline_content`,
- the route now auto-calls `prepare_document(...)` with that inline content,
- matching the already-established continuity pattern used by extraction.

### Test change
Strengthened web regression in:
- `tests/unit/web/test_full_api_routes.py`

Final regression contract:
- a dev-seeded inline document assessed directly through `POST /credibility`
- should behave equivalently to the same document after explicit `POST /prepare`
- at the owned seam:
  - prompt contains excerpt text,
  - prompt does not contain the missing-source-text fallback,
  - output `summary`, `source_reliability`, and `information_credibility` match the explicit-prepare path.

## Verification
### Focused tests
Confirmed:
- `PYTHONPATH=src pytest -q tests/unit/web/test_full_api_routes.py -k auto_prepare_matches_explicit_prepare`
  - `1 passed`
- `PYTHONPATH=src pytest -q tests/unit/web/test_full_api_routes.py -k credibility`
  - `4 passed, 31 deselected`
- earlier wider credibility scope remained green after the initial route fix:
  - `PYTHONPATH=src pytest -q tests/unit/application/test_application_credibility.py tests/unit/web/test_full_api_routes.py -k credibility`
  - `22 passed, 31 deselected`

### Live verification
Confirmed live on the local launcher:
1. explicit prepare path
   - Reuters dev-seeded document:
     - `prepare_chunk_count: 1`
     - stored chunk `raw_text` present
     - credibility: `source_reliability: high`, `information_credibility: medium`
   - World Bank dev-seeded document:
     - `prepare_chunk_count: 1`
     - stored chunk `raw_text` present
     - credibility: `source_reliability: high`, `information_credibility: medium`
2. implicit auto-prepare path
   - fresh World Bank dev-seeded document with no explicit `prepare`
   - direct `POST /api/documents/{id}/credibility` produced:
     - stored chunk visible afterwards via `GET /api/documents/{id}/chunks`
     - `source_reliability: high`
     - `information_credibility: medium`
     - excerpt-aware summary/concerns
     - no missing-source-text fallback

## Scope outcome
### Done in this slice
- identified the real seam,
- froze it with a bounded RED,
- shipped the smallest continuity GREEN,
- verified with focused tests,
- verified live with explicit and implicit prepare flows.

## Success criteria status
### Achieved
- dev-seeded inline documents no longer default to missing-source-text fallback in the verified live rerun,
- dev-seeded credibility output became excerpt-aware on representative strong-source cases,
- POST/GET credibility seam remained green,
- no scoring heuristic broadening was needed.

## Decision-ready exit conditions
### Close this SSOT slice as materially done
Because:
- the first real continuity seam was fixed,
- dev-seeded and case/document flows are now materially closer on equivalent inline inputs,
- live revalidation no longer shows metadata-only fallback by default for the verified strong-source dev-seeded reruns.

## Closure rule
Do not reopen this continuity slice by default.

Reopen only if one of these happens:
1. a fresh live path again falls back to missing-source-text behavior for a dev-seeded inline document,
2. explicit `prepare` and direct `POST /credibility` diverge again on equivalent inline input,
3. a new operator-facing case shows that continuity remains broken after the verified fix.
