# Deep Research general-web relevance and supporting breadth closure note — 2026-06-24

## Scope
This closure note records the bounded follow-up after the earlier Deep Research artifact-chain hardening slice.

Goal:
- improve internet-only behavior for broad/general Deep Research questions
- avoid local-project grounding bias
- replace fragile `unknown` classification with a safer `general` bucket
- preserve honest evidence posture: no artificial promotion into `core`
- make narrowing behavior inspectable before further tuning

## What changed

### 1. Query classification posture
- `ResearchQueryClass.UNKNOWN` was replaced by `ResearchQueryClass.GENERAL`.
- Broad non-procedural internet questions now resolve into `general` instead of falling into an unhelpful catch-all bucket.
- Legacy persisted payloads with `query_class="unknown"` are still readable and map to `general` on load.

### 2. Evidence packing posture for `general`
- `general` findings are treated as `supporting`, not auto-promoted into `core`.
- Final evidence packing now uses cumulative findings across rounds instead of only the last round.
- `supporting_limit` for `general` was raised from `2` to `3` once the upstream search/relevance path was producing three distinct findings in live smoke.

### 3. Internet-only search breadth
- The runtime now performs a slightly broader second-round web search for `general` / `direct_answer` style queries.
- Second-round query generation uses lightweight web-oriented variants instead of repeating the original query only.
- Later-round search adapters fetch a broader per-query candidate set than round one.

### 4. General relevance tuning
- `general` relevance filtering was tuned narrowly to admit context-rich non-procedural hits from safe source classes (`generic`, `docs`, `analysis`, `data`) even when literal keyword overlap is weaker.
- Procedural/admin posture was intentionally left stricter.

### 5. Search narrowing diagnostics
- Progress events now expose search narrowing summaries during runs.
- The runtime records warning-phase diagnostics such as:
  - raw hit count
  - accepted count
  - duplicate count
  - low-relevance count
  - domain-limit count
- This made it possible to verify that the main bottleneck for the tested general query was `low_relevance`, not provider breadth alone and not domain caps.

## Live findings from the bounded debug loop
The bounded diagnostics loop established the following progression for the tested broad/general query:

Query:
- `Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku`

Observed evolution:
- earlier state: `urls=1`, `supporting_count=1`
- after multi-round + diagnostics hardening: `urls=3`, `supporting_count=2`
- after raising `general` supporting capacity: `urls=3`, `supporting_count=3`

Representative live result after the final bounded slice:
- job id: `rj-c5372ebcfc80`
- `urls = 3`
- `raw_findings_count = 3`
- `supporting_count = 3`
- `core_count = 0`

Representative supporting set:
- `ABSL - Helping Hand: Jak zdrowie psychiczne wpływa na efektywność w miejscu pracy?`
- `Wpływ pracy zdalnej na zdrowie psychiczne pracowników`
- `Praca zdalna po pandemii – Raport podsumowujący webinarium ...`

Representative narrowing diagnostics from the same bounded investigation:
- round 1: `raw_hits=10, accepted=1, low_relevance=9`
- round 2: `raw_hits=17, accepted=2, duplicate=1, low_relevance=14`

## Interpretation
This follow-up changed the product behavior in a useful, bounded way:
- general internet questions are classified more honestly
- evidence is not cosmetically overstated
- supporting evidence survives across rounds
- the runtime now keeps up to three supporting findings for `general`
- narrowing is observable enough to support future tuning with evidence rather than guesswork

## What this slice did not do
- no local-project or repo grounding bias was added
- no recursive branching / branch execution engine was added
- no retry/self-loop reflection behavior was introduced
- no automatic promotion of thin evidence into `core`
- no broad procedural/admin loosening was introduced

## Current recommended posture
For broad/general internet-only questions, the current bounded runtime is now in a materially better state:
- classification: improved
- evidence packing: improved
- search breadth: improved
- narrowing observability: improved
- supporting evidence retention: improved

The next step, if future evidence justifies it, should be another narrowly scoped general relevance tuning pass based on observed warning diagnostics rather than a broad rewrite.
