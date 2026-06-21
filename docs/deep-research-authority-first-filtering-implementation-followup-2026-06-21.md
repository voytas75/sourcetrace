# Deep Research authority-first filtering implementation follow-up — 2026-06-21

Status: completed bounded slice
Date: 2026-06-21
Scope: implementation of pre-extraction authority-first filtering for procedural-admin Deep Research queries.

## 1. Goal

Introduce a stronger gate between:
- deduped search hits
- and extracted findings

so that procedural-admin answers are influenced primarily by authoritative documentation before extraction/synthesis begins.

---

## 2. What was implemented

### A. Pre-extraction authority filter
Added a bounded pre-extraction filter in `research_runtime.py`:
- `_filter_hits_for_extraction(...)`
- `PreExtractionFilterOutcome`

This layer now evaluates procedural-admin search hits before extraction and decides what survives into the extraction stage.

Current v1 policy:
- strongly keeps:
  - official docs
  - high-authority docs-like hits
- drops:
  - forum
  - video
  - snippet repo sources
  - low-value procedural noise
- keeps a limited best-secondary fallback when strong docs are sparse

### B. Telemetry
Extended `ResearchStats` with filter-level visibility:
- `pre_extraction_sources_seen`
- `pre_extraction_sources_kept`
- `pre_extraction_sources_dropped`
- `authority_policy_applied`
- `authority_filter_fallback_used`
- `dropped_source_types`

### C. Runtime integration
The runtime now applies the filter before:
- `self.extract(...)`

This means procedural-admin extracted findings are now built from the filtered hit set, not the raw deduped hit set.

### D. Evaluator awareness
The evaluator now includes filter-aware procedural notes such as:
- `Authority-first filtering was applied before extraction.`
- fallback explanation when secondary sources had to be admitted.

---

## 3. Tests

Added/updated focused unit tests verifying:
- official docs survive while forum/video/snippet sources are dropped,
- fallback works when only secondary sources exist,
- procedural query generator + authority shaping still behaves correctly.

Focused gate after change:
- `19 passed`

Full repo gate after change:
- `403 passed`

---

## 4. Quick SCCM rerun result

Observed runtime result for:
- `How do I create configuration baselines in SCCM?`

### Improvements
- `search_providers = ['searxng']`
- top URLs are now dominated by Microsoft Learn / official Microsoft sources
- the first five visible URLs were all Microsoft documentation before the first community blog appeared
- evaluator now reports:
  - `source_quality_verdict = mixed`
  - `relevance_verdict = strong`
  - `truthfulness_verdict = strong`
  - `should_revise_report = false`

### Representative top URLs
- `learn.microsoft.com/.../create-configuration-baselines`
- `learn.microsoft.com/.../deploy-configuration-baselines`
- `learn.microsoft.com/.../about-configuration-baselines-and-configuration-items`
- `learn.microsoft.com/.../new-cmbaseline`
- `learn.microsoft.com/.../get-started-with-compliance-settings`

### Remaining imperfection
- one community blog still remained in the wider kept set,
- evaluator still rates source quality as `mixed`, not `strong`.

So the slice improved the evidence path substantially, but did not yet make the class completely authority-pure.

---

## 5. Verdict

This slice succeeded.

It delivered the main intended effect:
- official procedural docs now dominate the extracted evidence path,
- weak sources are filtered earlier,
- the procedural SCCM case is materially cleaner than before,
- repo health remains green.

The remaining weakness is now smaller and much more specific than before.

---

## 6. Recommendation

Do not widen scope immediately.

If this line of work continues later, the next likely micro-slice is:
- one stricter pass on what counts as acceptable secondary procedural support,
- or a cap that prevents community sources from entering the kept set when enough official docs already survived.

But the major upgrade itself is now in place and working.
