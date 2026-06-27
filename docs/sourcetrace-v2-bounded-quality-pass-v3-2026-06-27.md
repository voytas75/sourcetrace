# SourceTrace v2 bounded quality pass v3 — 2026-06-27

## Scope

Run one short quality pass over the richer `eval_corpus_v3` plus the existing bounded v2 confidence surfaces.

Verification run:
- `tests/unit/v2/test_eval_corpus_v3.py`
- `tests/unit/v2/test_eval_corpus_v2.py`
- `tests/unit/v2/test_selected_evidence_policy.py`

Result:
- **PASS** (`4 passed` for the v3 gate; supporting v2/policy checks also passed)

## What this pass now proves better than v2

Compared with the previous quality pass, this one gives a slightly more realistic signal on:
- remote-work / policy topic shape
- IT-admin / identity-hardening topic shape
- official-vs-duplicate-domain competition
- thin-news-vs-richer-source competition

That means the current bounded policy stack is now holding across:
- minimal-content guard
- explain/debug surface
- domain-diversity preference
- a somewhat more realistic topical fixture layer

## Sharpest remaining weakness

The bottleneck still looks like **corpus realism**, but now in a narrower sense:
- not merely “add more cases” in the abstract,
- but add cases that stress **authority vs relevance tradeoffs** and **official-vs-commentary preference** more directly.

The current bounded policy is coherent.
What it still lacks is evidence that the chosen policy behaves well on harder authority/relevance collisions.

## Practical verdict

The next best slice should not be another generic heuristic just because we can add one.
The smarter move is to add a few sharply targeted corpus cases that force a decision between:
- official but broader pages,
- non-official but more directly on-topic pages,
- duplicate-domain official pages,
- thin commentary vs richer institutional guidance.

## Recommended next bounded slice

Prefer:
1. `eval corpus v4` focused on authority-vs-relevance collisions, then
2. only if that new corpus justifies it, a small evidence-policy change.
