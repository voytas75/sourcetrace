# Sourcetrace — saved work state after Checkpoint 1 closure

Saved: 2026-05-21
Repo: `/home/voytas/projects/sourcetrace`
Branch: `main`
Commit at campaign note start: `cbd29e6`

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
- Full test baseline after the fix: `268 passed` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q`.

## Current bounded verdict
- Runtime blocker for Phase 1 factual bucket is closed.
- Current dominant issues are now quality issues, not extraction failure:
  - grounding traceability,
  - claim compactness,
  - source-faithful normalization.
- Readiness remains bounded to `controlled test-use`.
- Do not upgrade the product claim to trusted analytical readiness.

## Best next slice when resuming
1. Grounding traceability for paraphrased-but-unique claims, especially the remaining A1 weakness.
2. Tighten extraction/normalization to reduce oversized or lightly paraphrased claims in A2/A3-style factual articles.
3. Then proceed with Phase 2 campaign docs:
   - C1
   - C2

## Files most relevant on resume
- `docs/plans/2026-05-21-checkpoint-1-phase1-a123.md`
- `docs/plans/2026-05-21-real-data-ops-plan-v1.md`
- `src/sourcetrace/llm/litellm_client.py`
- `src/sourcetrace/application/extraction_runtime.py`
- `tests/unit/llm/test_litellm_client.py`

## Working tree note
The repo still has additional local changes beyond the Checkpoint 1 docs. Before the next coding slice, check `git status --short` and separate:
- campaign/docs ledger files,
- extraction/grounding code changes,
- unrelated README / blueprint edits.
