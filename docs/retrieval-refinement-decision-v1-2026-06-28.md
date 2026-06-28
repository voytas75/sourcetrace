# SourceTrace v2 retrieval refinement decision v1 — 2026-06-28

## Goal

Use the stronger regression baseline plus the recent live retrieval evaluation evidence to decide which single retrieval refinement target should come next.

This slice is a decision slice, not an implementation slice.

## Candidate directions considered

### A. Case-specific retrieval tuning for Poland remote-work
Why it was considered:
- the Poland remote-work case remains unstable

Why it is **not** the next best move:
- it is the highest risk path back into local heuristics
- it would likely overfit one jurisdiction/query family before solving the more general retrieval weakness

### B. Case-specific retrieval tuning for legal-hold / records-retention
Why it was considered:
- legal-hold still falls back into vendor/vendor in some runs

Why it is **not** the next best move:
- it is narrower than the broader failure pattern
- it risks optimizing one domain before addressing the more general problem of candidate-pool composition and target quality

### C. Trust-contract deepening
Why it was considered:
- the recent evaluation pack showed trust status is still only loosely aligned with retrieval quality

Why it is **not** the next best move:
- trust semantics should follow stronger retrieval/evidence understanding, not substitute for it
- deepening trust policy before the next retrieval refinement would be premature

### D. Retrieval candidate quality / targeting refinement
Why it was considered:
- the remaining weak and ambiguous cases share a broader pattern:
  - advisory/commercial drift
  - unstable institutional survival in some domains
  - jurisdiction mixing when institutional hits exist but targeting is weak

Why this is the best next move:
- it is broader than a single weak case, but still more precise than a vague "improve retrieval"
- it fits the evidence from the new regression baseline
- it stays upstream and avoids selector surgery
- it can be evaluated cleanly against both the healthy anchor cases and the newly pinned weak/ambiguous cases

## Decision

The next highest-value retrieval refinement target should be:

## `retrieval-target-quality-refinement-v1`

## Intended focus

Improve the quality of which candidates survive into the bounded pool by targeting the broader problem of:
- advisory/commercial drift in official-intent queries
- weak jurisdiction/topic targeting when institutional candidates exist but are not the best answer shape

This should **not** be implemented as query-specific or country-specific rules.
It should stay general enough to help across:
- remote-work Poland
- cross-border data transfer
- jurisdiction-mixed tax guidance
- and similar future cases

## Why this beats the alternatives

It is the best next slice because it:
- addresses the sharpest remaining retrieval-side weakness visible across multiple cases
- avoids slipping into deterministic local heuristics
- does not require selector or trust-contract churn first
- has a stronger evaluation baseline than earlier slices had

## Guardrails for the next slice

The next implementation slice should:
- stay upstream in retrieval/candidate quality
- avoid query-family-specific overrides
- avoid selector-policy changes unless new evidence forces that conclusion
- be validated against both:
  - healthy anchor cases from regression pack v1
  - weak/ambiguous cases from regression pack v2

## Practical verdict

The right next move is no longer "find another weak query and patch it".
It is to make one bounded, general retrieval-target-quality refinement and judge it against the now-stronger shared baseline.
