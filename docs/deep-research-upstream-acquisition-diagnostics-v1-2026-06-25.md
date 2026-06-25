# Deep Research upstream acquisition diagnostics v1 — 2026-06-25

Status: complete
Scope: hard diagnostics for current institutional and scientific live-query failures after routing, preservation, and weighting fixes.
Owner: Wiedzmin

## 1. Decision / SSOT

This document is the SSOT for the current bounded upstream-acquisition diagnostics slice.
It supersedes chat summaries for this slice.

## 2. Why this slice now

Recent bounded fixes landed and tested green:
- query-class-specific upstream routing v1
- official/scientific candidate preservation v1
- institutional/scientific source-weighting v1

But live behavior remained weak:
- institutional/NIK query still surfaced media-led results instead of official material
- scientific/remote-work query still failed with zero usable results

That meant the main remaining bottleneck was likely upstream of final ranking.

## 3. Goal

Determine, with hard evidence, whether the remaining failure sits in:
- query classification,
- query generation/refinement,
- raw search acquisition,
- or post-search acceptance/gating.

## 4. Evidence inspected

Artifacts and event streams inspected:
- `data/research/events/rj-c03af5789970.json`
- `data/research/events/rj-d5ed6f8f61c5.json`
- `data/research/jobs/rj-c03af5789970.json`
- `data/research/jobs/rj-d5ed6f8f61c5.json`
- live status/result payloads for the same jobs

Reference context:
- `docs/deep-research-remote-work-weak-source-upstream-diagnostics-v1-plan-2026-06-24.md`

## 5. Institutional query diagnosis (NIK / Szpital Południowy)

Query:
- `Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?`
- job: `rj-c03af5789970`

Observed planning/classification:
- `planning_analysis.query_class = procedural_admin`
- `execution_plan.strategy = procedural_research`

This is already suspicious: the query is institutional/investigative, not Microsoft-style operator procedure.

### Round 1 search queries emitted
Original round-1 query set:
1. `Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie, najlepiej na podstawie oficjalnych materiałów pokontrolnych i komunikatów.`
2. `site:learn.microsoft.com Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie, najlepiej na podstawie oficjalnych materiałów pokontrolnych i komunikatów.`
3. `Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie, najlepiej na podstawie oficjalnych materiałów pokontrolnych i komunikatów. Microsoft Learn`
4. `Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie, najlepiej na podstawie oficjalnych materiałów pokontrolnych i komunikatów. official documentation`

Providers attempted:
- `procedural_admin_unified_search`
- `searxng`

Round-1 outcome:
- `raw_hits = 6`
- `accepted = 0`
- `low_relevance = 6`

Retry query set:
1. `NIK Szpital Południowy Warszawa ustalenia`
2. `raport NIK Szpital Południowy Warszawa`
3. `kontrola NIK Szpital Południowy Warszawa wyniki`

Retry outcome:
- `raw_hits = 7`
- `accepted = 2`
- `low_relevance = 5`

Post-filter outcome:
- `Normalized 2 new source(s); kept 1 after authority filtering.`
- kept source URL: `https://www.money.pl/finanse/gwozdz-do-trumny-nik-ujawni-raport-ws-warszawskiego-szpitala-7300245413345312a.html`

Round 2 emitted queries:
1. `site:learn.microsoft.com Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie, najlepiej na podstawie oficjalnych materiałów pokontrolnych i komunikatów.`
2. `Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie, najlepiej na podstawie oficjalnych materiałów pokontrolnych i komunikatów. Microsoft Learn official documentation`
3. `Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie, najlepiej na podstawie oficjalnych materiałów pokontrolnych i komunikatów. Configuration Manager documentation`

Round-2 outcome:
- `raw_hits = 11`
- `accepted = 0`
- `low_relevance = 11`

### Verdict for institutional query
Primary blocker:
- **wrong query-class classification / wrong search-shaping family**

Why:
- the query is being forced into `procedural_admin`
- that injects Microsoft Learn / Configuration Manager procedural expansions into a Polish institutional audit query
- the emitted query sets prove the shaping family is wrong before ranking even begins

Secondary blocker:
- even after retry, only 2 hits are accepted and authority filtering still keeps a media page instead of an official one
- so there is also a weaker secondary issue in acceptance/filtering, but it is not the first problem to solve

Strong conclusion:
- this is **not** mainly a ranking problem anymore
- it is first a **misclassification / wrong query-family generation** problem

## 6. Scientific query diagnosis (remote work / mental health)

Query:
- `Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku`
- job: `rj-d5ed6f8f61c5`

Observed planning/classification:
- `planning_analysis.query_class = broad_concept`
- `execution_plan.strategy = broad_research`

This classification is directionally correct.

### Round 1 search queries emitted
Original query set:
1. `Zbadać wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku`

Outcome:
- `raw_hits = 3`
- `accepted = 0`
- `low_relevance = 3`

Retry query set:
1. `wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023`
2. `praca zdalna zdrowie psychiczne pracowników badania 2024`
3. `remote work mental health employees 2024 study`
4. `praca zdalna dobrostan psychiczny pracowników forum doświadczenia 2024`

Retry outcome:
- `raw_hits = 12`
- `accepted = 0`
- `low_relevance = 12`

Final outcome:
- hard error: `Search is unavailable: neither the original query nor the LLM-refined web queries returned usable results.`

### Verdict for scientific query
Primary blocker:
- **upstream acquisition + overly strict acceptance gating**

Why:
- classification is broadly correct
- retry queries are imperfect but at least partly sensible (`badania 2024`, English `study` variant)
- however the live backend returns 12 raw hits and all 12 are rejected as low relevance

Implication:
- either the provider mix is not surfacing scholarly/health sources for this topic,
- or the current relevance acceptance logic is too strict for this source shape,
- or both

Secondary issue:
- one retry query is actively low quality:
  - `praca zdalna dobrostan psychiczny pracowników forum doświadczenia 2024`
- that injects anecdotal/forum intent into a query whose constraints explicitly asked for systematic reviews, meta-analyses, and representative studies

Strong conclusion:
- this path does **not** primarily fail in final ranking
- it fails because no usable candidate set survives acquisition + acceptance

## 7. Cross-case synthesis

### Institutional case
Main failure seam:
- query misclassification into `procedural_admin`

### Scientific case
Main failure seam:
- weak upstream acquisition and/or overly strict acceptance, despite broadly correct class

### What is no longer the main blocker
After the recent slices, the main blocker is no longer:
- procedural-adapter hijack
- candidate preservation policy alone
- final local weighting alone

## 8. Best next bounded slices

### Next slice A — institutional
`institutional query-class correction v1`

Bounded goal:
- stop classifying institutional audit/report questions like the NIK query as `procedural_admin`
- route them into a general/institutional evidence-seeking query family instead of Microsoft procedural expansions

Minimal DoD:
- the NIK query no longer emits `site:learn.microsoft.com`, `Microsoft Learn`, or `Configuration Manager documentation`
- live rerun shows institutional/offical-oriented query variants instead

### Next slice B — scientific
`scientific acquisition + acceptance diagnostics/fix v1`

Bounded goal:
- inspect why 12 raw retry hits all became `low_relevance`
- identify whether the failure is provider poverty, relevance heuristics, or both

Minimal DoD:
- capture representative raw returned domains/URLs for the remote-work retry set
- determine whether scholarly/health sources are absent upstream or being rejected downstream

## 9. Recommendation

Do the institutional classification fix first.

Reason:
- it is the sharpest and most obviously wrong behavior
- the emitted query text proves the current branch is incorrect
- it is likely local and bounded

Then do the scientific acquisition/acceptance pass.

## 10. Completion note

This diagnostics slice is complete.
The strongest verified finding is:
- **institutional failure = wrong class / wrong query family**
- **scientific failure = no usable candidate set survives acquisition + relevance acceptance**
