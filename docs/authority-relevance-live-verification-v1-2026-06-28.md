# SourceTrace v2 authority-relevance live verification v1 — 2026-06-28

## Goal

Run a small live verification pass on real queries and check whether the current authority/relevance posture still produces acceptable selected-evidence outcomes on the real provider mix.

This slice is evaluation-only.
No policy change is bundled into it.

## Method

Used the current v2 operator/runtime path with live Azure + SearxNG and persisted compiled readback.

Queries used:
1. `remote work reporting obligations Poland employer official guidance`
2. `break glass account guidance conditional access official best practice`
3. `data breach notification checklist authority official guidance`
4. `legal hold steps records retention official guidance`

For each query, the check looked at:
- compiled selected-evidence titles/URLs/providers
- bounded judgment bands on selected items
- whether the pair looked like an acceptable authority/relevance outcome

## Observed outcomes

### 1) Remote work reporting
Selected:
- BPCC employment-law guide
- Dudkowiak employment-contract page

Assessment:
- not acceptable for the intended query
- both results are commentary/legal-adjacent; no clear official or exact reporting guidance surfaced
- judgment bands were already weak (`authority low/none`, `topic_match low`, `answer_fit low`)

### 2) Identity / break-glass accounts
Selected:
- MSEndpointMgr conditional access article
- AdminDroid conditional access impacts article

Assessment:
- not acceptable for the intended query
- both results are commentary/vendor-adjacent blog content; no strong official break-glass guidance surfaced
- the problem is upstream candidate quality, not only downstream selection

### 3) Data breach notification
Selected:
- GDPR.eu explainer
- European Commission data protection explainer

Assessment:
- weak / borderline but still not good enough for the exact query
- one source is broad commentary, the other is broad official explanation, but neither is a concrete notification checklist/procedure source
- again, query/candidate quality is too broad before selection

### 4) Legal hold steps / records retention
Selected:
- LinkedIn post about Copilot Studio instructions
- Anthropic constitution page

Assessment:
- clearly unacceptable
- this is a hard failure at retrieval/query-generation level
- selected outputs are off-topic enough that downstream authority/relevance judgment cannot rescue the run

## Main conclusion

The current bounded authority/relevance selection surface should **not** be the first thing changed from this live pass.

The sharper live problem is upstream:
- query shaping
- retrieval candidate quality
- candidate-topic relevance before evidence judgment/selection

In other words:
- fixture-level authority/relevance posture looked coherent
- real live verification exposed that the candidate pool can still be too broad, too commentary-heavy, or outright off-topic
- changing the downstream selection policy now would risk compensating for the wrong layer

## Practical verdict

This slice does **not** justify immediate authority/relevance heuristic expansion.
It does justify a new bounded upstream-quality slice focused on:
- live query shaping quality
- retrieval candidate relevance
- authority-aware candidate generation before selection

## Recommended next bounded slice

`authority-relevance-live-retrieval-diagnostics-v1`

Goal:
- stay in evaluation/diagnostic mode first
- inspect why these live queries produced weak or off-topic candidate sets
- localize whether the main issue is planning, query refinement, retrieval source mix, or candidate acceptance

Do not jump straight to policy changes from this live pass.
