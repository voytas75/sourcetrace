# SourceTrace v2 deployment readiness gap review v1 — 2026-06-28

## Goal

Re-rank the remaining non-storage production gaps after the recent retrieval, regression, trust-contract, and storage-posture slices, then choose the next highest-value bounded slice.

## What is materially stronger now

The following lines are no longer the sharpest production gaps:

### Storage / persistence honesty
Recent slices materially improved this line:
- persistence partial-state audit
- trailing JSONL corruption tolerance
- JSONL durability posture decision

Verdict:
- good enough for the current bounded operator/development posture
- not the next best place to spend effort

### Operator truth surface
Recent slice materially improved this line:
- operator trust contract (`usable / weak / needs_review / degraded`)

Verdict:
- still simple, but good enough for the current stage
- not the sharpest remaining gap

### Source typing / institutional survival basics
Recent slices materially improved this line:
- source typing v1-v3
- institutional evidence precision
- institutional retrieval window + evaluation

Verdict:
- no longer the immediate bottleneck
- keep without further heuristic drift

## Remaining meaningful non-storage gaps

### 1. Retrieval quality remains the biggest live bottleneck
Why it is still #1:
- even after the retrieval-window improvement, live behavior is still not fully stable across hard cases
- the quality line now has a baseline and better operator honesty, but retrieval remains the main place where answer usefulness is won or lost
- the remaining question is no longer "should official material survive at all?" but rather whether retrieval output is consistently good enough across representative cases

This is still the highest-value production gap.

### 2. Regression discipline now exists, but it is still small
Why it is still important:
- `quality-regression-pack-v1` is a good start
- but it is still a narrow pack, not yet a broader confidence layer
- future retrieval/selection changes can still outrun the current regression surface

This is important, but still secondary to live retrieval quality itself.

### 3. Trust contract is present, but not yet deeply tied to evidence quality semantics
Why it still matters:
- operators now get a clean top-line status
- but the trust block is still intentionally shallow
- there is still no richer quality-policy layer connecting trust more directly to evidence-strength patterns or eval outcomes

This matters, but not before the next retrieval-quality step.

### 4. PDF quality remains unfinished but is not the immediate blocker
Why it is lower:
- seam + consumer path + typed carry-forward already exist
- user explicitly paused PDF expansion earlier
- PDF quality matters, but it is not the current main production bottleneck

## Re-ranked priority order

### Highest priority now
1. broader retrieval quality validation and stabilization

### Next tier
2. regression pack expansion / confidence hardening
3. deeper trust-quality alignment

### Lower for now
4. PDF quality gate completion

## Best next bounded slice

`retrieval-quality-evaluation-pack-v1`

## Why this is the best next move

It is the best next slice because it:
- stays away from deterministic heuristics
- uses the newly added regression discipline instead of bypassing it
- directly targets the still-sharpest production bottleneck: whether retrieval quality is stable enough across a broader representative pack
- creates a better basis for deciding whether the next move should be retrieval refinement, regression-pack expansion, or trust-policy deepening

## Intended scope of the next slice

Run and summarize a broader retrieval-quality evaluation pack across representative live queries, then record:
- where the current retrieval path is already good enough
- where it is still unstable
- whether the next bounded move should be:
  - retrieval refinement,
  - regression-pack expansion,
  - or trust-quality alignment

## Practical verdict

After the recent closure work, the next highest-value production-readiness gap is **still retrieval quality**, but now it should be approached through a broader evaluation pack rather than another local heuristic repair.
