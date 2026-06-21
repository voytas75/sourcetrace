# Deep Research hardening follow-up — 2026-06-21

Status: completed bounded slice
Date: 2026-06-21
Scope: telemetry truthfulness + procedural-source-quality hardening follow-up after the first benchmark pass.

## 1. Slice goal

Address the two clearest failures from the first benchmark run:
1. incorrect `search_providers` telemetry,
2. weak source preference for procedural/admin queries.

---

## 2. Changes made

### A. Telemetry truthfulness
Adjusted research runtime telemetry so `result.stats.search_providers` reflects the actual configured/active search adapter rather than defaulting to `stub-search` when `settings.search_provider` is unset.

Implemented behavior:
- direct SearxNG adapter now reports `searxng`,
- provider-backed search reports `web_search`,
- chained adapters report their active provider names,
- fallback remains `stub-search` only when no better signal exists.

### B. Procedural-source-quality hardening
Strengthened procedural-query heuristics so weak community/video/forum sources are treated more conservatively.

Changes include:
- stronger weak-source detection for:
  - YouTube,
  - Reddit,
  - blog-like domains,
  - broader community/blog platforms,
- explicit `forum` source type,
- lower ranking for forum/blog/video sources on procedural queries,
- top findings selection now blocks `forum` and `video` source types for procedural queries unless better material is absent.

### C. Tests
Added/strengthened focused tests to verify:
- Reddit-like procedural hits are rejected as relevant evidence,
- top findings for procedural queries prefer official docs over blog/video/forum alternatives.

Full repo gate remained green after the change.

---

## 3. Verification

### Automated tests
- focused gate: `tests/unit/application/test_application_research.py` → passed
- full repo gate: `397 passed`

### Benchmark rerun summary
Reran the same three benchmark queries through the public Deep Research API.

Observed improvements:

#### Query 1 — `analiza ostatniego tygodnia ETHUSDC`
- `search_providers` now reports `['searxng']`
- top sources became cleaner and more comparable:
  - TradingView chart
  - TradingView technicals
  - Binance ETH/USDC
  - Bybit ETH/USDC
- the answer became more disciplined around spot-market comparability and avoided the earlier spot/perpetual mix.

#### Query 2 — `How do I create configuration baselines in SCCM?`
- `search_providers` now reports `['searxng']`
- Microsoft Learn now appears in the top results immediately
- a community blog still appears high, so the query class is improved but not fully clean yet
- the final answer is stronger because it now leans on a more credible procedural footing.

#### Query 3 — `deep research architecture`
- `search_providers` now reports `['searxng']`
- broad-concept query still returns a mixed blog/research/article source set, which is expectedly noisier than procedural queries
- this slice did not aim to solve broad-concept source curation completely.

---

## 4. Verdict

This slice succeeded.

### Fixed
- telemetry truthfulness for search backend reporting,
- the worst procedural-query source-quality weakness from the first benchmark pass.

### Improved but not fully finished
- procedural/admin source ranking is better, but still not strict enough to consistently force official docs + strong secondary docs above all community material,
- broad conceptual queries still need separate source-quality tuning if we want cleaner research-grade evidence mixes there.

---

## 5. Recommended next step

The next best step is **not** to jump to Odysseus yet.

Recommended order now:
1. optionally do one more bounded procedural-ranking pass to demote residual weak sources like Stack Overflow / generic gists when official docs exist,
2. then return to the planned **post-result evaluator** implementation,
3. keep broader concept-query source curation as a separate later slice.

If Odysseus is consulted later, it should be only for a still-failing named behavior, not for general comparison.
