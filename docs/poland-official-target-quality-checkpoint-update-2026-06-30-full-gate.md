# SourceTrace v2 Poland official target-quality checkpoint update — 2026-06-30 full gate

## Verdict

The bounded Poland target-quality sequence is now fully checkpointed.

After:
- `exact-subject-target-quality-refinement-v1`
- `official-pair-hygiene-v1`
- and the small eval-fixture alignment pass,

repo-side validation is clean again.

## Final validation result

Full v2 unit gate:
- `./.venv/bin/pytest -q tests/unit/v2`
- result: `121 passed, 3 xfailed in 2.22s`

Targeted eval triage gate:
- `./.venv/bin/pytest -q tests/unit/v2/test_authority_relevance_outcome_eval_v2.py tests/unit/v2/test_eval_corpus_v3.py -vv`
- result after fixture alignment: `2 passed`

## What was confirmed

1. **Exact-subject official top-1 improved**
- the Poland labour-law / official-source phrasing now surfaces a stronger official gov.pl winner in live runs
- the earlier broad-adjacent institutional drift was materially reduced

2. **Official pair hygiene improved**
- selected evidence no longer ejects a stronger second official candidate only to satisfy blind diversity pressure
- the exception remains narrow and bounded

3. **Eval posture is aligned with the new bounded behavior**
- the remaining full-suite failures were not random regressions
- they were stale eval expectations that still encoded the older diversity-favoring behavior
- fixtures were updated instead of rolling back the better policy behavior

## Current trustworthy restart summary

For this Poland family thread, the current honest state is:
- official-source survival is healthier
- exact-subject official ranking is healthier
- selected pair hygiene is healthier
- live verification passed
- full v2 repo-side gate is green again

The main remaining open issue is still:
- residual breadth inside otherwise healthy official result sets

Not the old problems:
- not obvious publication-like drift
- not obvious non-official contamination of the selected pair
- not obvious failure of official candidate survival in the calibrated Poland family

## Restart pointers

Use these docs together:
- `docs/poland-institutional-retrieval-diagnostics-v1-2026-06-30.md`
- `docs/exact-subject-target-quality-refinement-v1-2026-06-30.md`
- `docs/poland-official-target-quality-checkpoint-2026-06-30.md`
- `docs/poland-official-target-quality-checkpoint-update-2026-06-30-full-gate.md`

## Practical next move

Do not reopen this slice unless new live evidence shows a fresh exact-subject miss.

If resuming Poland quality work later, the next bounded move should only be a new precision slice if:
- a live run shows residual breadth that materially harms operator trust, or
- a new official-source family shows the same exact-subject weakness.
