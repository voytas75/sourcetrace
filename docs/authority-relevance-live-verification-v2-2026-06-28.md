# SourceTrace v2 authority-relevance live verification v2 — 2026-06-28

## Goal

Re-run the earlier live authority/relevance verification after repairing the retrieval query handoff contract.

This slice remains evaluation-only.
No selector-policy change is bundled into it.

## Method

Used the current v2 operator/runtime path with the repaired query handoff (`authority-relevance-query-handoff-contract-v1`), live Azure + SearxNG, and persisted execution readback.

Queries used:
1. `remote work reporting obligations Poland employer official guidance`
2. `break glass account guidance conditional access official best practice`
3. `data breach notification checklist authority official guidance`
4. `legal hold steps records retention official guidance`

For each query, the check looked at:
- whether `evidence_query` exactly matched the bounded seed query
- selected evidence titles/URLs/providers
- bounded judgment bands on selected items
- whether overall outcome quality improved versus the earlier live pass

## Main result

The handoff repair materially improved live behavior.

The biggest previous defect is gone:
- `evidence_query` now matched the original bounded seed query in all four cases
- retrieval no longer drifted into assistant-style prose

This did not make every result perfect, but it clearly improved the live baseline enough to confirm that the handoff bug was a real upstream cause, not a side issue.

## Case notes

### 1) Remote work reporting
Selected:
- British Polish Chamber of Commerce remote-work guide
- Dudkowiak & Putyra remote-work guide

Assessment:
- improved versus the earlier pass
- still commentary/legal-adjacent rather than strongly official
- but now clearly on-topic and much more specific
- judgment improved materially (`topic_match high`, `specificity high` on top item)

### 2) Identity / break-glass
Selected:
- Microsoft Learn emergency access accounts
- AdminDroid break-glass best practices

Assessment:
- clearly improved and broadly acceptable
- now includes a strong official Microsoft Learn source plus one practical commentary source
- this is close to the intended authority/relevance shape

### 3) Breach notification
Selected:
- FTC data breach response guide
- ICO personal data breaches guide

Assessment:
- strongly improved and acceptable
- both sources are institutional/official enough for the bounded query intent
- this is the best outcome of the rerun set

### 4) Legal hold steps
Selected:
- Venio legal hold best-practices guide
- Everlaw litigation-holds guide

Assessment:
- dramatically improved versus the previous hard failure
- no longer off-topic
- still vendor/practical rather than clearly official/public-institutional
- acceptable as a practical pair, but weaker on institutional authority than the strongest cases above

## Main conclusion

The retrieval query handoff repair was the right fix.

It meaningfully improved live authority/relevance outcomes, and it removed the most clearly broken upstream behavior.

However, the rerun also shows that the next weakness is now narrower:
- not freeform query drift,
- but source mix and authority profile of retrieved candidates for some topics.

In other words:
- before the repair, live retrieval was structurally unstable
- after the repair, live retrieval is much more coherent
- the remaining gap is more about how to bias candidate sourcing toward stronger official/institutional guidance when the query intent implies that preference

## Practical verdict

Do **not** change downstream selector policy first.

The sharper next bounded slice, if we keep pushing this track, is likely upstream retrieval/source-shaping work such as:
- authority-aware retrieval biasing,
- official/institutional source preference in query generation or candidate acceptance,
- or narrow diagnostics on why some topics still land commentary-heavy candidate pools despite correct query handoff.

## Recommended next bounded slice

`authority-relevance-source-mix-diagnostics-v1`

Goal:
- inspect why some corrected live queries still land mainly commentary/vendor sources instead of stronger institutional sources
- stay diagnostic first before adding new heuristics
