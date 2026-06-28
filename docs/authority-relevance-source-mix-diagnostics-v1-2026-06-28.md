# SourceTrace v2 authority-relevance source-mix diagnostics v1 — 2026-06-28

## Goal

After the retrieval query handoff repair, diagnose why some live queries still land commentary-heavy or vendor-heavy selected evidence instead of stronger institutional sources.

This slice stays diagnostic-only.
No selector-policy change is bundled into it.

## Scope

Used the same post-handoff live query class and inspected the current search/retrieval surface itself.
Focus:
- whether institutional sources are missing entirely from provider results,
- or present but losing due to result ordering / truncation / acceptance,
- or structurally underrepresented for some topic classes.

## Architectural observations

Current search layer is intentionally thin:
- `SearxNGSearchGateway` passes a plain query to SearxNG
- it returns the first `count` rows with almost no source-type metadata
- there is no explicit institutional/official source classification in the search adapter
- there is no upstream source-mix steering beyond the query text itself
- the default SearxNG-backed path only keeps the top few results returned by the provider

That means source mix is mostly decided by:
1. raw query wording,
2. upstream search-engine ranking,
3. shallow top-N truncation,
4. only later by bounded selector logic.

## Live source-mix findings

### 1) Breach notification
This is the strongest case after the handoff repair.

Observed top results included multiple institutional sources very high in the raw provider output, including:
- FTC
- ICO
- EDPB

Interpretation:
- for this topic, the provider surface already contains strong institutional candidates near the top
- the current system does reasonably well here once query drift is fixed
- this case does **not** point to selector failure

### 2) Legal hold steps
This case improved sharply after the handoff repair, but still leaned vendor/practical.

Observed raw top results showed a mixed surface:
- ranks 1–2: vendor/practical guides (Venio, DISCO)
- rank 3: institutional PDF guidance
- rank 6: National Archives guidance

Interpretation:
- institutional sources are **present** in the provider output
- but they are not consistently leading the result stack
- shallow top-N behavior makes the final candidate pool sensitive to provider ranking and query wording
- this looks more like a retrieval/source-ordering problem than a downstream selector problem

### 3) Broader pattern from the rerun set
Across the rerun queries, the remaining weak cases now look like one of two shapes:
- **institutional sources exist, but are outranked by practical/vendor/commentary pages**, or
- **query wording is broad enough that mixed commentary sources compete too well against official/institutional pages**

The key shift versus earlier diagnostics is important:
- before the handoff repair, retrieval was fundamentally using the wrong query input
- after the repair, the remaining weakness is much narrower and more honest: source ordering / source mix under a plain query

## Main conclusion

The current live weakness is best described as **source-mix bias under plain retrieval**, not selector drift.

For at least some topics:
- the provider already has institutional candidates,
- but the system does not yet steer strongly enough toward them before top-N truncation and later selection.

## Practical diagnosis

The next bounded repair probably belongs in one of these upstream places:
- query generation/source wording that better biases official/institutional results,
- search adapter/source typing metadata for institutional vs commentary/vendor surfaces,
- or candidate acceptance/order shaping before downstream selected-evidence policy runs.

What should **not** happen next:
- adding more downstream authority/relevance selector heuristics before this upstream source-mix issue is addressed more directly.

## Recommended next bounded slice

`authority-relevance-source-mix-shaping-v1`

Goal:
- keep scope upstream and narrow
- improve the probability that official/institutional candidates survive into the bounded candidate pool for queries whose wording implies that preference
- avoid touching downstream selector policy in the same slice
