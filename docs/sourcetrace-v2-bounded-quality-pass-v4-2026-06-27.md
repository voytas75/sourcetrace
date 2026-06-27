# SourceTrace v2 bounded quality pass v4 — 2026-06-27

## Scope

Run one short quality pass over the new collision-focused `eval_corpus_v4` and supporting policy/corpus checks.

Verification run:
- `tests/unit/v2/test_eval_corpus_v4.py`
- `tests/unit/v2/test_eval_corpus_v3.py`
- `tests/unit/v2/test_eval_corpus_v2.py`
- `tests/unit/v2/test_selected_evidence_policy.py`

## Result

Current bounded quality pass v4 status: **PASS**

## What this pass proves

The current bounded policy stack remains coherent across:
- minimal-content guard
- explain/debug surface
- domain-diversity preference
- more realistic topical cases
- explicit authority-vs-relevance and official-vs-commentary collision fixtures

This is enough to say the current v2 selection policy is no longer obviously under-validated for its intended bounded scope.

## Sharpest remaining gap

The remaining gap is now narrower and more strategic:
- not “does the current bounded policy basically work?”
- but “what authority/relevance policy do we actually want beyond this bounded baseline?”

In other words, the next move should probably not be another tiny policy tweak made from discomfort.
The system now has enough bounded evidence to support a deliberate choice between:
- stopping here and calling the current policy good enough for v2, or
- starting a new, explicitly more ambitious evidence-policy track.

## Practical verdict

For the current bounded v2 closure track, the evidence-selection layer now looks **good enough**.
The next useful work is likely one of:
1. declare evidence-policy baseline frozen for v2 and switch to broader closure/packaging work, or
2. open a new explicitly-post-baseline track for richer authority/relevance judgment.

## Recommendation

Recommendation: **do not add `selected-evidence policy v3` by default**.
Treat the current stack as the bounded baseline unless a new requirement or a sharper corpus says otherwise.
