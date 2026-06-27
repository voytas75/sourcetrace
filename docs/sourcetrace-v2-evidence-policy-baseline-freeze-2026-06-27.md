# SourceTrace v2 evidence-policy baseline freeze — 2026-06-27

## Decision

Freeze the current v2 evidence-selection policy as the bounded baseline.

This means:
- do **not** add `selected-evidence policy v3` by default,
- treat the current selection stack as good enough for the bounded v2 line,
- require either a new requirement or sharper corpus evidence before reopening the policy.

## Frozen baseline

The frozen baseline currently includes:
- minimal-content guard,
- compact explain/debug surface,
- domain-diversity preference,
- validation against eval corpora v1–v4,
- bounded quality passes v1–v4.

## Why freeze now

Recent quality passes and corpus expansions narrowed the remaining uncertainty.
The current evidence does **not** show that another small heuristic tweak is the best next move.

The sharper conclusion is:
- the current bounded policy is coherent,
- the remaining uncertainty is strategic rather than obviously tactical,
- more policy tweaks without a new trigger would be guessier than useful.

## Reopen conditions

Reopen the evidence-selection policy only if at least one of these is true:
1. a new eval corpus case exposes a clear selection failure,
2. a new product/runtime requirement demands a stronger authority/relevance judgment,
3. a separate post-baseline authority/relevance policy track is explicitly opened.

## Practical implication

For the current v2 closure track:
- treat evidence-selection as baseline-frozen,
- move effort to closure/packaging/posture work or to new evidence-driven requirements,
- avoid heuristic drift.
