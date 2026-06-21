# Deep Research evaluator-aware benchmark baseline follow-up — 2026-06-21

Status: completed bounded slice
Date: 2026-06-21
Scope: first canonical 3-query benchmark rerun after evaluator integration, using evaluator-aware benchmark reporting.

## 1. What was done

Executed the canonical 3-query benchmark pack against the current SourceTrace runtime and generated a fresh evaluator-aware markdown report.

Artifacts:
- raw benchmark payload: `/tmp/sourcetrace_research_benchmark_current_results.json`
- generated report: `docs/deep-research-benchmark-baseline-2026-06-21-evaluator-aware.md`

Queries run:
1. `analiza ostatniego tygodnia ETHUSDC`
2. `How do I create configuration baselines in SCCM?`
3. `deep research architecture`

---

## 2. Baseline results

### ETHUSDC
- score: `12/12`
- verdict: strong current evaluator-aware pass
- note: still asks for an exact OHLCV check, but the result was otherwise clean and well-structured.

### SCCM baseline query
- score: `7/12`
- verdict: still the weakest current class
- note: evaluator correctly flags that no official procedural documentation made it into the evidence set and that the answer still leans too much on community-style material.

### Deep research architecture
- score: `10/12`
- verdict: good enough, but still source-mix noisy
- note: evaluator correctly marks blog/secondary-source contamination without collapsing the whole answer.

---

## 3. Strongest conclusion

The benchmark is now materially more useful because it no longer relies only on manual interpretation of raw outputs.

The current decision signal is sharp:
- market-symbol path looks healthy,
- broad-concept path is acceptable,
- procedural/admin path is still the main weak class.

---

## 4. Recommendation

Do not broaden scope again.

If the next slice is still about Deep Research quality rather than platform ergonomics, the best remaining target is:
- stronger authority-first retrieval/reranking for procedural/admin queries,
- ideally with more explicit authority signals rather than more ad hoc source bans.

The evaluator and benchmark harness are now good enough to measure that next step clearly.
