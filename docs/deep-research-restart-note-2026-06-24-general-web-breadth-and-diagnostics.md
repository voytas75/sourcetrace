# Deep Research restart note — 2026-06-24 — general web breadth and diagnostics

## Where we are
The bounded follow-up after Deep Research artifact-chain hardening is now closed on `main`.

Latest shipped commit:
- `a2cc73b` — `feat(research): improve general web evidence breadth and diagnostics`

This follow-up stayed intentionally internet-only for broad/general research questions.
No local-project grounding bias was added.

## What was shipped
- replaced fragile `unknown` handling with `ResearchQueryClass.GENERAL`
- kept legacy persisted `query_class="unknown"` payloads readable
- improved multi-round web query shaping for `general` / `direct_answer`
- broadened later-round web search candidate breadth
- fixed cumulative evidence packing across rounds
- added search narrowing diagnostics in runtime progress events
- tuned `general` relevance lightly for context-rich non-procedural hits
- raised `general` supporting evidence capacity to `3`
- preserved honest evidence posture:
  - `general` findings stay in `supporting`
  - no artificial promotion into `core`

## Verified live outcome
Representative broad/general query:
- `Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku`

Representative final smoke:
- job id: `rj-c5372ebcfc80`
- `urls = 3`
- `raw_findings_count = 3`
- `supporting_count = 3`
- `core_count = 0`

Representative narrowing diagnostics:
- round 1: `raw_hits=10, accepted=1, low_relevance=9`
- round 2: `raw_hits=17, accepted=2, duplicate=1, low_relevance=14`

Interpretation:
- candidate breadth is no longer the only bottleneck
- the main remaining narrowing pressure for this class of query is still `low_relevance`
- current state is materially better than the pre-fix baseline (`urls=1`, `supporting_count=1`)

## Canonical docs from this slice
- `docs/deep-research-general-web-relevance-and-supporting-breadth-closure-note-2026-06-24.md`
- `docs/deep-research-restart-note-2026-06-24-general-web-breadth-and-diagnostics.md` (this file)

## If resuming later
Ask for a 3-line status first:
1. where we are
2. what remains open
3. best next small slice

## Best next small slice
Only if new evidence justifies more work:
- another very narrow `general` relevance tuning pass driven by warning diagnostics
- do **not** jump into a broad rewrite
- do **not** add local-project grounding to this internet-only path unless requirements explicitly change

## Current posture
This micro-epic should be treated as complete unless new live evidence shows a regression or a clear quality gap worth another bounded pass.
