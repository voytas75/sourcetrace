# SourceTrace v2 authority-relevance live retrieval diagnostics v1 — 2026-06-28

## Goal

Localize where the live authority/relevance path breaks before changing downstream selection policy.

This slice stays diagnostic-only.
No policy change is bundled into it.

## Scope

Checked the same live query class that previously produced weak authority/relevance outcomes.
Focused on whether the failure appears first in:
- planning,
- query refinement,
- retrieval query construction,
- or downstream evidence selection.

## Key finding

The sharpest current live defect is in **retrieval query construction**.

The retrieval stage is currently using a large assistant-style freeform text blob as `evidence_query`, not a bounded search query derived from the original user intent.

That means retrieval is often searching for text like:
- "This is a solid summary..."
- "If you want, I can help in one of these ways..."
- "Here are the official guidance sources to finish that section..."

instead of searching for the original intent directly.

This is a much stronger diagnosis than the earlier generic observation that retrieval looked weak.
The live path is structurally unstable because the search input drifts into answer-like prose before retrieval.

## Evidence from live checks

### Case: remote work reporting
- seed query: `remote work reporting obligations Poland employer official guidance`
- retrieval query prefix: `It looks like you already have the core answer pretty well summarized...`
- `evidence_query_equals_seed`: `false`
- planning degraded: `true`
- top selected result: remote-work anecdotal/community-style result

### Case: identity / break-glass
- seed query: `break glass account guidance conditional access official best practice`
- retrieval query prefix: `Yes — that summary is aligned with Microsoft’s official guidance...`
- `evidence_query_equals_seed`: `false`
- planning degraded: `false`
- top selected result: `Manage emergency access accounts in Microsoft Entra ID`

Interpretation:
- this one happened to land better,
- but the mechanism is still unstable because retrieval is using expanded prose rather than a bounded query object/string.

### Case: breach notification
- seed query: `data breach notification checklist authority official guidance`
- retrieval query prefix: `This is a solid checklist and it closely matches the way regulators frame breach response...`
- `evidence_query_equals_seed`: `false`
- planning degraded: `true`
- top selected result: broad GDPR PDF/explainer-type material

### Case: legal hold steps
- seed query: `legal hold steps records retention official guidance`
- retrieval query prefix: `Here are the official guidance sources to finish that section...`
- `evidence_query_equals_seed`: `false`
- planning degraded: `true`
- top selected result: a NARA-related PDF in one run, but previous live runs also drifted badly off-topic

Interpretation:
- even when the retrieved result looks better, the current mechanism is still doing the wrong thing architecturally.
- it is succeeding inconsistently, not correctly.

## Main conclusion

The next change should **not** be authority/relevance selector tuning.

The primary upstream repair target is:
- keep retrieval on a bounded query string derived from user intent,
- rather than letting planning/query-refinement freeform answer prose become the retrieval input.

## Practical diagnosis

Today the minimal flow effectively does this:
1. planning writes freeform output
2. query refinement writes freeform output
3. retrieval searches using the current accumulated text

That is the wrong contract for stable retrieval.

What the system likely needs instead is a bounded handoff such as:
- explicit retrieval query field/string,
- or structured query-refinement output that isolates search intent from answer prose.

## Recommended next bounded slice

`authority-relevance-query-handoff-contract-v1`

Goal:
- keep scope strictly on the planning/query-refinement -> retrieval handoff
- introduce a bounded retrieval-query contract or field
- do not change downstream authority/relevance selection in the same slice

## Why this is the right next move

Because the live failures are now explained well enough that improving downstream selection first would treat symptoms, not cause.
