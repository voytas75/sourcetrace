# Deep Research remote-work weak-source upstream diagnostics v1 — 2026-06-24

Status: in progress
Scope: diagnose why the representative remote-work / mental-health `general` query still retains weak source shapes despite recent relevance, retention, promotion, and classifier refinements.
Owner: Wiedzmin

## 1. Decision / SSOT

This document is the SSOT for the current bounded diagnostics slice.
Update it inline as work proceeds.
Do not treat chat summaries as authoritative once this file exists.

## 2. Why this slice now

Recent bounded work improved one conceptual/general path, but the representative remote-work query still ends with:
- `core=0`
- supporting-only weak source shapes
- lint `weak` with `thin_evidence_base`

That suggests the remaining bottleneck sits upstream of the latest classifier/promotion improvements.

## 3. Goal

Determine whether the current remote-work weak-source outcome is primarily caused by:
- weak query generation,
- weak search result selection,
- weak authority-aware retention for this topic,
- or simply poor source availability in the current backend/provider mix.

Also provide a short feasibility readout for the next plan.

## 4. Planned work items

### A. Re-read the remote-work live artifact chain
- [x] Re-read the latest representative remote-work result artifact.
- [x] Re-check search/retention stats already persisted there.
- [x] Record the observed upstream shape plainly.

Observed upstream shape from `rj-5364ece6e656`:
- `queries = 4`, `rounds = 2`, but only `urls = 3`
- `pre_extraction_sources_seen = 3`
- `pre_extraction_sources_kept = 2`
- `authority_filter_fallback_used = true`
- kept sources were weakly specific:
  - ABSL general workplace-mental-health page
  - ZPP webinar/report summary page
- final evidence remained:
  - `core = 0`
  - `supporting = 2`
  - lint `weak` / `thin_evidence_base`

Plain reading:
- the system did not surface a rich candidate pool and did not find a strong authoritative bucket for this topic.
- the final weakness is visible before packing: the candidate pool itself is already thin and off-target.

### B. Compare against generation/selection assumptions
- [x] Inspect the current query-expansion shape for direct-answer/general runs.
- [x] Inspect whether the retained sources suggest search-generation mismatch, selection mismatch, or provider poverty.
- [x] Record the most likely bottleneck.

Current general direct-answer expansion (round 2):
- `<objective> report study`
- `<objective> analysis findings`
- `<objective> workplace health research`

Most likely bottleneck:
- primarily **query-generation mismatch**, with possible secondary provider poverty.

Reasoning:
- the remote-work query is specific: it needs post-2023, remote/hybrid work, and mental-health outcomes.
- current round-2 expansions are too generic and partially drift from the actual question:
  - `workplace health research` broadens away from remote work,
  - `report study` and `analysis findings` are vague and not obviously biased toward post-2023 peer-reviewed or longitudinal sources,
- resulting evidence confirms the drift:
  - ABSL page is about mental health at work in general,
  - ZPP page is a webinar/report summary,
  - neither is a strong direct answer to the requested post-2023 remote-work mental-health question.
- because only 3 URLs surfaced at all, provider/search-backend poverty may also contribute,
- but the first bounded seam with the highest leverage is still query shaping, because the current expansions are visibly under-specified for this topic.

### C. Feasibility readout
- [x] State whether the next bounded fix looks high / medium / low feasibility.
- [x] Name the smallest justified next seam.
- [x] Keep this slice diagnostic only.

Feasibility rating:
- **medium-high** for one bounded query-shaping improvement slice.

Why not low:
- the mismatch is concrete,
- the seam is local (`StubQueryGenerator` general direct-answer branch),
- and the current prompts are clearly generic enough that a better topic-specific expansion is plausible.

Why not high:
- the backend/provider may still be sparse for some Polish-language or mixed-language remote-work queries,
- so better query shaping may improve but not fully solve the topic.

Smallest justified next seam:
- `general direct-answer query shaping for research-seeking health/social topic v1`
- specifically: make round-2 expansion less generic and more aligned with the actual requested evidence shape (for example post-2023, remote/hybrid, mental-health outcomes, study/longitudinal/survey cues).

## 5. Likely scope

- `src/sourcetrace/application/research_runtime.py`
- `data/research/results/rj-5364ece6e656.json`
- related docs/SSOT from the live verification chain

## 6. Out of scope

Not in this slice:
- immediate code changes,
- broad backend/provider replacement,
- benchmark pack expansion,
- lint redesign.

## 7. Completion condition

This slice is complete when the most likely upstream bottleneck is explicit and the next bounded plan has a feasibility rating.

## 8. Completion note

Pending.
