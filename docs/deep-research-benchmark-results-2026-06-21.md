# Deep Research benchmark results — 2026-06-21

Status: completed bounded benchmark run
Date: 2026-06-21
Runtime: local launcher with `SOURCETRACE_SEARXNG_BASE_URL=http://127.0.0.1:18080`
Scope: first black-box benchmark pass using the public Deep Research API.

## 1. Run verdict

The Deep Research API surface is sufficient for real black-box benchmarking.

The system completed all three benchmark runs through the public API, produced persisted result artifacts, and returned consistently structured reports.

However, this run exposed two meaningful quality problems:
1. **telemetry truthfulness is currently wrong** — `search_providers` reported `stub-search` even though the runtime was configured for `searxng`,
2. **source-quality ranking is still weak on procedural/admin queries** — the SCCM baseline query returned a usable answer, but the result set was polluted by YouTube, blogs, Reddit, and other weak sources instead of clearly preferring Microsoft Learn / official documentation.

So the current state is:
- lifecycle/API: good,
- report structure: good,
- uncertainty discipline: decent,
- source-quality routing: mixed,
- telemetry/debug truthfulness: currently not acceptable.

---

## 2. Benchmark setup

Launcher path used:
- local launcher mode
- repo virtualenv active
- shell env sourced from `~/.bashrc`
- `SOURCETRACE_SEARXNG_BASE_URL=http://127.0.0.1:18080`

Observed runtime confirmation:
- `/api/runtime` reported:
  - `research = enabled`
  - `research_search_backend = searxng`
  - `research_search_configured = true`

Queries run:
1. `analiza ostatniego tygodnia ETHUSDC`
2. `How do I create configuration baselines in SCCM?`
3. `deep research architecture`

Scoring rubric:
- `0` = failed / misleading
- `1` = mixed / partial
- `2` = good enough for current slice

Dimensions:
- lifecycle/api correctness
- source relevance
- source quality
- synthesis truthfulness
- output shape consistency
- telemetry truthfulness

Maximum score per query: `12`

---

## 3. Results table

| Query | API | Relevance | Quality | Truthfulness | Shape | Telemetry | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| `analiza ostatniego tygodnia ETHUSDC` | 2 | 1 | 1 | 2 | 2 | 0 | 8 |
| `How do I create configuration baselines in SCCM?` | 2 | 1 | 0 | 1 | 2 | 0 | 6 |
| `deep research architecture` | 2 | 1 | 1 | 1 | 2 | 0 | 7 |

Interpretation:
- `8/12` = acceptable but needs one bounded tuning slice
- `6/12` = weak enough to justify targeted quality work
- `7/12` = acceptable but still mixed

---

## 4. Per-query notes

### Query 1 — `analiza ostatniego tygodnia ETHUSDC`

Observed positives:
- exact-pair sources were present,
- final report used the expected structure,
- uncertainty was explicit and appropriately restrained,
- the answer did not bluff a precise weekly conclusion without enough evidence.

Observed issues:
- evidence mixed **Binance Spot** with **Bitget Perpetual**, so the comparison was directionally suggestive but not clean,
- result quality still leaned on market pages that are only partially comparable,
- telemetry still incorrectly reported `stub-search`.

Verdict:
- decent behavior,
- still needs pair-specific source normalization / ranking polish,
- not urgent enough to require Odysseus yet.

### Query 2 — `How do I create configuration baselines in SCCM?`

Observed positives:
- final answer was operationally plausible,
- report shape was good,
- the answer did not completely drift away from the task.

Observed issues:
- source ranking was weak,
- top findings included **YouTube**, **blog posts**, **Reddit**, and other low-authority sources,
- Microsoft Learn / official ConfigMgr docs were not clearly preferred,
- the answer therefore rests on weaker evidence than it should for a procedural enterprise query.

Verdict:
- this is the clearest current failure,
- the next bounded quality slice should treat this query class as a first-class target.

### Query 3 — `deep research architecture`

Observed positives:
- the synthesized answer described a reasonable planner → retrieval/tool use → evidence/state → synthesis pattern,
- the output shape was consistent,
- the answer stayed mostly within the likely evidence envelope.

Observed issues:
- source mix was noisy and blog-heavy,
- the query is semantically broad and allowed drift into generic “agent architecture” material,
- telemetry again falsely reported `stub-search`.

Verdict:
- conceptually decent,
- still too permissive in source acceptance/ranking for a benchmark intended to support tuning decisions.

---

## 5. Strongest conclusion from this run

The next best slice is **not** “go inspect Odysseus broadly”.

The next best slice is:

## telemetry + procedural-source-quality hardening

Specifically:
1. fix `result.stats.search_providers` so it reflects the actual search path used,
2. strengthen source preference / rejection for **procedural enterprise queries**, especially toward official docs,
3. keep market-symbol tuning as a secondary follow-up, not the first move.

---

## 6. Should we inspect Odysseus now?

### Recommendation: not yet

This benchmark already named the failing dimensions clearly enough:
- telemetry truthfulness,
- procedural-source-quality ranking.

Those can be improved directly inside SourceTrace first.

### When Odysseus becomes worth opening

Only if, after one bounded local tuning slice:
- SourceTrace still fails to prioritize official docs for procedural/admin queries, or
- SourceTrace still shows better query shaping/ranking gaps on exact-symbol market queries.

Then Odysseus should be consulted only for that precise behavior:
- source acceptance/rejection heuristics,
- query shaping,
- rank preference rules,
- synthesis discipline.

Not for general archeology.

---

## 7. Notes on benchmark harness quality

This run also revealed a small operator footgun in result interpretation:
- the useful payload currently lives under `result.raw_findings` and `result.raw_report`,
- `findings` and `report_markdown` were empty in this run path.
\nThat is not necessarily a product bug, but it is worth documenting or normalizing because it makes external benchmark reading more awkward than needed.

---

## 8. Recommended next action

Implement one bounded slice with this DoD:
- `search_providers` reports the actual backend used,
- official-doc preference is measurably improved for SCCM/procedural queries,
- rerun this same 3-query benchmark pack,
- only then decide whether Odysseus comparison is still needed.
