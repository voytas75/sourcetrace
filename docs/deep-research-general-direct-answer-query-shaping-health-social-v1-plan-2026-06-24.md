# Deep Research general direct-answer query shaping for research-seeking health/social topics v1 — 2026-06-24

Status: in progress
Scope: one bounded refinement to general direct-answer round-2 query shaping for research-seeking health/social topics such as remote work and mental health.
Owner: Wiedzmin

## 1. Decision / SSOT

This document is the SSOT for the current bounded slice.
Update it inline as work proceeds.
Do not treat chat summaries as authoritative once this file exists.

## 2. Why this slice now

Remote-work upstream diagnostics established that the current direct-answer general expansion is too generic for at least one representative research-seeking topic.
Current round-2 expansion:
- `<objective> report study`
- `<objective> analysis findings`
- `<objective> workplace health research`

For the remote-work / mental-health query, this appears to drift away from the intended evidence shape and contributes to a weak candidate pool.

## 3. Goal

Make one bounded improvement so that round-2 expansion for research-seeking health/social questions is more aligned with the requested evidence shape.

## 4. Guardrails

This slice must not:
- redesign the whole query generator,
- add many topic-specific branches,
- break market/procedural/news behavior,
- assume the backend can always supply ideal sources.

## 5. Planned work items

### A. Choose one bounded query-shaping rule
- [x] Re-read the current `StubQueryGenerator` general direct-answer branch.
- [x] Pick one narrow refinement rule for health/social research-seeking topics.
- [x] Record the rule here before code edits.

Chosen bounded rule:
- for `DIRECT_ANSWER` objectives that look like health/social research-seeking questions (for this slice: `mental health`, `wellbeing`, or `dobrostan`, combined with `remote`, `hybrid`, or `praca zdalna`), replace the current generic round-2 trio with a more evidence-shaped trio:
  - `<objective> longitudinal study after 2023`
  - `<objective> survey report after 2023`
  - `<objective> remote hybrid work mental health study`

Reason:
- this stays inside one local branch of `StubQueryGenerator`,
- it directly addresses the diagnosed drift,
- it does not redesign the whole planner,
- and it pushes toward study/survey/longitudinal evidence instead of vague workplace-health pages.

### B. Apply one bounded change
- [x] Implement exactly one local query-shaping refinement.
- [x] Keep the behavior narrow and easy to reason about.
- [x] Avoid heuristic sprawl.

Applied change:
- in the `DIRECT_ANSWER` round-2 branch, added one narrow health/social research-seeking override triggered by:
  - mental-health / wellbeing cues (`mental health`, `zdrowie psychiczne`, `wellbeing`, `dobrostan`)
  - plus remote/hybrid cues (`remote`, `hybrid`, `praca zdalna`, `zdaln`)
- when triggered, round-2 expansion becomes:
  - `<objective> longitudinal study after 2023`
  - `<objective> survey report after 2023`
  - `<objective> remote hybrid work mental health study`

Why this remains bounded:
- one local override in `StubQueryGenerator`,
- no planner redesign,
- no additional runtime/packing/classifier changes.

### C. Focused validation
- [x] Add/update only the smallest focused regression coverage needed.
- [x] Run the smallest meaningful focused gate.
- [x] Record the result inline.

Coverage updates:
- kept the generic direct-answer expansion test, but moved it to a non-health/non-remote objective
- added `test_stub_query_generator_uses_research_shaped_expansion_for_remote_mental_health_query`

Validation note:
- the first two test attempts failed for legitimate trigger-shape reasons:
  - the initial trigger matched English `mental health` but not Polish `zdrowie psychiczne`,
  - then it matched exact `praca zdalna` but not the inflected form `pracy zdalnej`.
- both were corrected by tightening the override toward robust but still narrow token matching.

Focused gate:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ./.venv/bin/pytest -q tests/unit/application/test_application_research.py`
- result: `53 passed in 0.16s`

### D. Feasibility / next-step readout
- [x] State the current feasibility state of the plan after this slice.
- [x] Record whether a follow-up live verification is justified.

Current feasibility state:
- **still medium-high, slightly improved**.

Why:
- the next live check now targets a clearly diagnosed local mismatch with a concrete, tested fix,
- the seam stayed narrow and did not create collateral failures,
- but backend/provider sparsity may still cap the upside.

Next-step verdict:
- a follow-up live verification is justified now.
- no additional query-shaping tweaks should be stacked before that verification.

## 6. Likely scope

- `src/sourcetrace/application/research_runtime.py`
- `tests/unit/application/test_application_research.py`

## 7. Out of scope

Not in this slice:
- search backend replacement,
- packer changes,
- classifier changes,
- lint redesign.

## 8. Completion condition

This slice is complete when one bounded query-shaping refinement is implemented, tested, and the plan feasibility/state is updated.

## 9. Completion note

Current slice status: complete.

What changed:
- the general direct-answer generator now uses more evidence-shaped round-2 queries for remote/hybrid mental-health style questions.

What remains to verify:
- whether this produces a richer candidate pool for the remote-work representative query,
- whether `pre_extraction_sources_seen` / `urls` improve,
- and whether stronger source shapes start to survive into the retained evidence set.

Recommended next action:
- run one bounded live verification pass for the remote-work query before any further changes.

---

## 10. Follow-up live verification for the remote-work query

Status: complete.

Observed run after the query-shaping override:
- job_id: `rj-a85d9910468c`
- terminal state: `done/full`
- stats:
  - `queries = 4`
  - `rounds = 2`
  - `urls = 3`
- evidence shape:
  - `core = 0`
  - `supporting = 2`
  - `background = 0`
- supporting titles:
  - `Praca zdalna po pandemii – Raport podsumowujący webinarium #14 ... - ZPP`
  - `Wpływ pracy zdalnej na zdrowie jest niekorzystny`
- lint:
  - `weak`
  - `thin_evidence_base`

Interpretation:
- the query-shaping override did **not** materially improve this representative remote-work run.
- candidate-pool breadth did not improve (`urls` remained at 3),
- evidence quality did not improve,
- and the retained source set remains weak and partially generic/publicistic.

What this suggests:
- the current limitation is now less likely to be solvable by another small local query-shaping tweak alone.
- the next likely bottleneck is provider/back-end coverage quality for this topic, or a need for a different search strategy than the current bounded general direct-answer flow.

Updated feasibility state:
- the broader plan remains **partially feasible**, but the specific local query-shaping path for this remote-work topic has dropped from `medium-high` to **medium-low** expected leverage.
- reason: the bounded fix was valid and tested, but live evidence did not move.

Recommended next step:
- stop local heuristic tuning on this remote-work path for now.
- if continuing later, use a different hypothesis class (for example provider mix / search-strategy change / targeted bilingual or academic-source expansion), not another nearby wording tweak.
