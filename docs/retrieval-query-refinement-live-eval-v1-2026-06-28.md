# SourceTrace v2 retrieval-query-refinement live eval v1 — 2026-06-28

## Goal

Run a small live pack against the updated dynamic query-refinement handoff and check whether candidate-pool quality improves materially on the remaining hard cases.

This slice is evaluation only.
It does not add new retrieval heuristics or change selector/trust policy.

## Runtime used

Bounded live operator path:
- `python -m sourcetrace_v2.operator.run_minimal_flow ...`
- Azure live LLM runtime
- local SearxNG at `http://127.0.0.1:18080`

## Live pack

Queries checked:
- `legal hold steps records retention official guidance`
- `remote work reporting obligations Poland employer official guidance`
- `cross border data transfer official guidance`
- `official tax filing deadline guidance for small business`

Artifacts saved under:
- `tmp/live-eval-v1/*.json`

## Results

### 1. Legal hold

Retrieval query:
- `legal hold steps records retention official guidance site:gov OR site:.edu OR site:archives.gov OR site:justice.gov`

Selected shape:
- `[PDF] Legal Hold Guidance - King County`
- `Records Management Regulations and Guidance | National Archives`

Verdict:
- clear improvement
- this is no longer the earlier vendor/vendor trap
- the query-refinement seam is now capable of surfacing public/institutional material in this hard case

Caution:
- trust still marked `needs_review`
- current reason includes `jurisdiction_mixed_selected_institutional_pair`, which is structurally honest but may now be a bit coarse for some cross-authority public-law pairs

### 2. Remote work Poland

Retrieval query:
- `Poland remote work employer reporting obligations official guidance site:gov.pl OR site:pip.gov.pl OR site:zus.pl`

Selected shape:
- `[PDF] remote work and telework in Polish public administration - CEJSH`
- `The rights and obligations of employers | Biznes.gov.pl`

Verdict:
- partial improvement
- this is better than the earlier advisory/commercial drift
- a real official/public source now survives into the selected pair
- but the top hit is still not a clean exact-subject official winner

Interpretation:
- dynamic query refinement helps here, but not enough to call the case stable or solved

### 3. Cross-border data transfer

Retrieval query:
- `cross-border data transfer official guidance site:gov OR site:europa.eu OR site:ico.org.uk OR site:edpb.europa.eu`

Selected shape:
- `Clarifying the legal requirement for cross-border sharing of health data ...`
- `International data transfers | Data protection guide for small business`

Verdict:
- mixed outcome
- the query is meaningfully more official-intent than before
- selected evidence is still not fully clean and trust remains `needs_review`\n- this remains a hard ambiguity/jurisdiction-quality case

### 4. Tax guidance

Retrieval query:
- `official IRS tax filing deadline guidance small business site:irs.gov OR site:gov.uk OR site:canada.ca OR site:ato.gov.au`

Selected shape:
- `Publication 334 (2025), Tax Guide for Small Business - IRS`
- `Small Business Filing and Recordkeeping Requirements -`

Verdict:
- strong improvement
- this no longer lands the earlier jurisdiction-mixed institutional pair
- trust is now `usable`

## Overall verdict

The updated dynamic query-refinement handoff is a **real live improvement**.

What improved materially:
- tax guidance
- legal hold
- remote-work Poland (partially)

What remains not fully clean:
- remote-work Poland still lacks a clear exact-subject official winner at the top
- cross-border data transfer still lands an imperfect mixed-quality institutional shape

## Practical interpretation

This result changes the next decision.

The next best move is **not** to go back to generic deterministic retrieval heuristics.
The dynamic query-refinement seam is doing useful work and should remain the preferred path for intent shaping.

But the eval also shows that dynamic query building alone is not enough for every hard case.
The remaining weakness now looks narrower:
- exact-subject survival among already-more-official candidate pools
- especially where official/public-law sources compete with broad or adjacent institutional material

## Recommended next bounded slice

`retrieval-survival-after-query-refinement-v1`

Goal:
- inspect whether a small bounded survival adjustment is still needed after the improved query-refinement path,
- but only for candidate-pool promotion within already official-intent retrieval results,
- and only if it can be justified from these live outcomes without falling back into query-specific deterministic heuristics.
