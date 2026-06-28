# SourceTrace v2 institutional retrieval gap diagnostics v1 — 2026-06-28

## Goal

Inspect why strong public/institutional candidates are still weak or absent in the hardest institutional-intent cases before changing retrieval or selection behavior again.

Target cases:
- Poland remote-work reporting
- legal-hold / records-retention

## What was checked

1. Re-ran the two hard cases through the repo-owned v2 operator path and inspected persisted execution/readback candidate pools.
2. Inspected raw SearxNG results beyond the current v2 top-3 retrieval slice to see whether institutional sources were absent at the provider layer or being lost inside the bounded retrieval seam.

## Findings

### 1. Remote-work reporting is not a pure provider-miss

Observed current v2 candidate pool (`limit=3` after retrieval shaping):
- Deloitte
- Dudkowiak
- getsix

Observed raw SearxNG top 10 for the same query:
- BPCC
- Deloitte
- getsix
- easyeor
- Dudkowiak
- L&E Global
- CMS
- CELIA Alliance PDF
- **gov.pl — Ministry of Family, Labour and Social Policy / Remote work**
- PWE PDF

Interpretation:
- the provider is capable of returning a true public-institutional Poland source
- but the current v2 retrieval seam only keeps the first 3 raw rows before any broader survival logic can help
- therefore the sharper problem here is **top-N truncation too early in the retrieval seam**, not total absence of institutional evidence at the provider layer

### 2. Legal-hold / records-retention is also not a pure provider-miss

Observed current v2 candidate pool (`limit=3` after retrieval shaping):
- DISCO
- Venio
- First Legal / CLOC-hosted vendor practical material (depending on run ordering)

Observed raw SearxNG top 10 for the same query:
- Venio
- DISCO
- OpenText PDF (CLOC-hosted)
- Everlaw blog/guide
- **HHS litigation-hold policy**
- Everlaw guide
- **ABP legal hold policy PDF**
- First Legal
- **King County records-management legal-holds guidance PDF**
- Daymark

Interpretation:
- real institutional/public-law signals do exist in the provider output
- but they arrive below the current top-3 cutoff
- again, the sharper failure is **premature top-N truncation plus weak institutional survival before truncation**, not complete provider inability

## Main diagnosis

The current retrieval gap is primarily this:

> **v2 is collapsing provider output to a top-3 candidate pool too early, before institutional-intent survival pressure has enough room to rescue lower-ranked but stronger public/institutional candidates.**

That is a better diagnosis than either of these weaker stories:
- "the provider cannot find institutional material"
- "selector/judgment still needs more tuning"

## Why this matters

This changes the next move.
The next bounded slice should not be another selector or authority-scoring tweak.
It should inspect or adjust the retrieval seam where provider output is narrowed too aggressively.

## Practical verdict

The failure is upstream, but more specifically than before:
- not just "retrieval quality"
- **retrieval truncation / candidate-survival policy inside the current v2 seam**

## Recommended next bounded slice

`institutional-retrieval-window-v1`

Goal:
- widen the bounded retrieval window modestly for institutional-intent queries,
- then apply shaping/survival over that slightly larger pool,
- without turning the system into a broad heuristic sprawl or changing downstream selector policy first
