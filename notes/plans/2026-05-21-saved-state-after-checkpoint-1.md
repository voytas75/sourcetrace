# Sourcetrace — saved work state after Checkpoint 1 closure

Saved: 2026-05-22
Repo: `/home/voytas/projects/sourcetrace`
Branch: `main`
Resume checkpoint commit: `6c06126`
Current closeout commit: `a8327bb`

## What is now closed
- Phase 1 / Checkpoint 1 for A1/A2/A3 is closed at documentation level.
- Observation notes updated:
  - `docs/plans/2026-05-21-observation-a1-reuters-south-africa-risks.md`
  - `docs/plans/2026-05-21-observation-a2-bbc-us-inflation-energy-shock.md`
  - `docs/plans/2026-05-21-observation-a3-bbc-us-jobs-april.md`
- Checkpoint summary created:
  - `docs/plans/2026-05-21-checkpoint-1-phase1-a123.md`

## Confirmed product state
- A2/A3 live extraction blocker was caused by structured payload normalization drift in `src/sourcetrace/llm/litellm_client.py`.
- Bounded adapter fix was added to normalize alias payload shapes (`claim_text`, `claim`, `exact_text`, `source_id`, `citation`, etc.).
- After the fix, campaign-shaped A2/A3 reruns returned `ready` and persisted claims.
- Post-checkpoint bounded quality slices now landed in `src/sourcetrace/application/extraction_runtime.py`:
  - A1 grounding tightening for uniquely paraphrased claims,
  - A2 carry-through duplicate tightening for `however,`,
  - A2.2 carry-through duplicate tightening for `although`,
  - A3 source-faithfulness guard for percentage-value drift.
- Current full test baseline: `275 passed` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q`.

## Current bounded verdict
- Runtime blocker for Phase 1 factual bucket is closed.
- Current dominant issues are now quality issues, not extraction failure:
  - grounding traceability,
  - claim compactness outside the already-fixed carry-through cases,
  - source-faithful normalization for non-trivial analytical rewrites.
- Readiness remains bounded to `controlled test-use`.
- Do not upgrade the product claim to trusted analytical readiness.

## Best next slice when resuming
1. Re-check live A1 grounding traceability after the bounded grounding fix and identify what still falls back to weak spans.
2. Tighten extraction/normalization to reduce oversized or lightly paraphrased analytical claims that are not already covered by the `however,` / `although` carry-through rules.
3. Then proceed with Phase 2 campaign docs:
   - C1
   - C2

## Files most relevant on resume
- `docs/plans/2026-05-21-checkpoint-1-phase1-a123.md`
- `docs/plans/2026-05-21-saved-state-after-checkpoint-1.md`
- `docs/plans/2026-05-21-real-data-ops-plan-v1.md`
- `src/sourcetrace/llm/litellm_client.py`
- `src/sourcetrace/application/extraction_runtime.py`
- `tests/unit/application/test_application_extraction_runtime.py`
- `tests/unit/application/test_application_extraction.py`

## Working tree note
- Working tree was clean immediately after the A3 commit and docs closeout commit.
- On resume, first check `git status --short --branch`, then confirm the current baseline with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` before picking the next bounded slice.
