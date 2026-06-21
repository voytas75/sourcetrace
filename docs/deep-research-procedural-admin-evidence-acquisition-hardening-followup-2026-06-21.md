# Deep Research procedural/admin evidence acquisition hardening follow-up — 2026-06-21

Status: diagnostic slice completed
Date: 2026-06-21
Scope: determine whether the remaining `procedural_admin` weakness is downstream evidence handling or upstream search-surface quality.

## What was checked

Ran a narrow procedural/admin runtime check with a realistic mixed hit set containing:
- Microsoft Learn `create configuration baselines`
- Microsoft Learn `deploy configuration baselines`
- one community SCCM tutorial
- one Reddit discussion

The current procedural/admin pipeline was exercised without changing retrieval/filtering heuristics first.

## Observed result

Top URLs in the resulting evidence set:
1. `https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines`
2. `https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/deploy-configuration-baselines`
3. `https://www.anoopcnair.com/sccm-configuration-baselines-guide/`

Evaluator outcome:
- `source_quality = mixed`
- `relevance = strong`
- `truthfulness = strong`
- `should_revise_report = false`

Evaluator reasons:
- `Official documentation is present in the evidence set.`
- `Community or weak procedural sources are still mixed into the result set.`
- `Authority-first filtering was applied before extraction.`
- `Fallback admitted secondary sources because too few strong procedural sources survived filtering.`

## Main conclusion

This is the important result:

The downstream procedural/admin pipeline is **not fundamentally failing** when official Microsoft Learn hits are actually present in the search surface.

It behaves as expected:
- official docs survive,
- evidence set becomes materially healthier,
- evaluator improves from `weak` to `mixed` / `strong` dimensions,
- report revision is no longer required.

## What this means

The remaining benchmark weakness is narrower than it first looked.

The main bottleneck is now more likely:
- upstream search-surface quality / recall in the synthetic benchmark path,
- not the already-implemented authority-first filtering and evidence handling.

In other words:
- if the search surface contains official docs, the current pipeline mostly does the right thing,
- if the search surface does not contain them, the downstream logic cannot invent them.

## Decision

Do **not** patch procedural/admin filtering logic again right now.

The better next move is one of these:
1. improve the benchmark/runtime search surface used for procedural/admin checks,
2. add a more realistic procedural benchmark harness that includes official-doc-capable search results,
3. only revisit downstream policy if a realistic official-doc-capable run still drops them.

## Verdict

This was a useful narrowing slice.

It shows that the current `procedural_admin` weakness is now mostly an **upstream acquisition/recall problem**, not a downstream evidence-pipeline design flaw.
