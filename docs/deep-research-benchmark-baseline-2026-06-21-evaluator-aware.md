# Deep Research benchmark report

Status: generated from benchmark result payloads

| Query | Class | API | Source | Relevance | Truth | Shape | Telemetry | Total | Revise |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `analiza ostatniego tygodnia ETHUSDC` | `market_symbol` | 2 | 2 | 2 | 2 | 2 | 2 | 12 | no |
| `How do I create configuration baselines in SCCM?` | `procedural_admin` | 2 | 0 | 0 | 1 | 2 | 2 | 7 | yes |
| `deep research architecture` | `broad_concept` | 2 | 1 | 1 | 2 | 2 | 2 | 10 | no |

## Per-query notes

### analiza ostatniego tygodnia ETHUSDC
- query_class: `market_symbol`
- providers: `['searxng']`
- findings_count: `5`
- recommended_next_check: Add one exact-market OHLCV check for the requested time window.
- report_preview: ## Current answer W ostatnim tygodniu ETHUSDC wygląda na wyraźnie słabszy: w dostarczonych punktach odniesienia cena spadła z ok. 1 795,89 do 1 735,29 na Binance i 1 726,89 na Bybit, czyli o ok. 3,3%–3,8% względem wcześniejszego poziomu referencyjnego. To…
- source: Top findings are mostly market or chart-oriented sources.
- next: Add one exact-market OHLCV check for the requested time window.

### How do I create configuration baselines in SCCM?
- query_class: `procedural_admin`
- providers: `['searxng']`
- findings_count: `3`
- recommended_next_check: Tighten source authority and rerun the same query for comparison.
- report_preview: ## Current answer In the Configuration Manager console, create a configuration baseline from **Assets and Compliance > Compliance Settings > Configuration Baselines** by selecting **Create Configuration Baseline**. In the wizard, give the baseline a name and…
- source: No official procedural documentation was found in the evidence set.
- relevance: Some findings still come from community, forum, video, or snippet-style sources.
- truth: The answer may lean on community material more than procedural authority warrants.

### deep research architecture
- query_class: `broad_concept`
- providers: `['searxng']`
- findings_count: `11`
- recommended_next_check: Tighten source authority and rerun the same query for comparison.
- report_preview: ## Current answer Deep research architecture is best understood as an orchestrated planner–executor system, not simple one-shot RAG. The strongest current evidence points to either a single strong agent with explicit planning and tool use or, more…
- source: The source mix includes blog-like or secondary commentary.
