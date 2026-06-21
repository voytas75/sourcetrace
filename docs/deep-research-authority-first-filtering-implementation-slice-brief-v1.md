# Deep Research authority-first filtering implementation slice brief v1

Status: proposed implementation slice
Date: 2026-06-21
Scope: bounded implementation brief for authority-first filtering before extraction/synthesis for procedural-admin Deep Research queries.

## 1. Slice verdict

This is the next sensible Deep Research quality slice after:
- query shaping + authority-first retrieval,
- evaluator v1,
- evaluator-aware benchmark baseline.

The target is narrow and justified:
- one query class: `procedural_admin`,
- one new control point: pre-extraction authority filtering,
- one measurable goal: cleaner evidence sets and stronger procedural-source quality.

---

## 2. Problem statement

Current state after the latest procedural query improvements:
- official docs can now enter the evidence set,
- evaluator output for SCCM improved materially,
- but community/blog-style material can still leak into the broader result set,
- and those weaker sources can still influence extraction and later synthesis.

So the remaining issue is no longer primarily query generation or final reranking.
It is the lack of a stronger gate between:
- `deduped search hits`
- and `extracted findings`

---

## 3. Objective

Add a pre-extraction filtering layer that prefers official/authoritative procedural documentation before findings are extracted.

Desired outcome for SCCM-like procedural queries:
- official docs dominate extracted findings,
- weak community sources are dropped or demoted before extraction,
- fallback keeps coverage when no strong docs exist,
- evaluator output improves from `mixed` toward `strong` source quality.

---

## 4. Non-goals

Do not do these in this slice:
- no auto-rewrite,
- no new search backend,
- no evaluator redesign,
- no ML reranker,
- no generalized policy engine for every query class,
- no wide UI changes.

This is a bounded procedural-admin quality slice, not a platform rewrite.

---

## 5. Proposed code changes

## A. Add a pre-extraction authority filter helper

Add a helper in `src/sourcetrace/application/research_runtime.py`, for example:
- `_filter_hits_for_extraction(...)`
- or `_apply_pre_extraction_policy(...)`

Input:
- `query`
- `hits`

Output:
- filtered tuple of `SearchHit`
- optional telemetry summary describing:
  - seen count,
  - kept count,
  - dropped count,
  - dropped source classes,
  - whether fallback path was used.

---

## B. Add explicit filter policy for `procedural_admin`

Suggested internal logic:

### Step 1 — score each hit on separate axes
For each hit calculate:
- relevance score
- authority score
- weak-source risk
- source type

### Step 2 — initial keep/drop bands
For procedural queries:
- strongly keep:
  - `official_docs`
  - docs-like vendor documentation
  - PowerShell/module docs tied to the same product ecosystem
- conditionally keep:
  - good secondary guides if they support/extend official docs
- drop or hard-demote:
  - forum
  - video
  - snippet_repo
  - thin blog results
  - listing/archive/tag pages
  - obviously off-domain, keyword-matching noise

### Step 3 — fallback safety rail
If strong sources after filtering fall below a minimum threshold,
allow the best secondary procedural sources back in.

This prevents empty evidence sets when official docs are sparse.

---

## C. Insert the filter before extraction

Current rough flow:
- query generation
- search
- dedupe
- extract
- synthesize

Target flow:
- query generation
- search
- dedupe
- **pre-extraction authority filter**
- extract
- synthesize

In practice, this means filtering `new_hits` before:
- `findings = self.extract(tuple(new_hits))`

and before those hits are allowed to meaningfully shape the evidence set.

---

## D. Add telemetry

Extend result stats or result metadata with filter visibility.

Suggested fields:
- `pre_extraction_sources_seen`
- `pre_extraction_sources_kept`
- `pre_extraction_sources_dropped`
- `authority_policy_applied`
- `authority_filter_fallback_used`
- optionally `dropped_source_types`

If `ResearchStats` is too narrow, attach a compact filter summary near evaluation/result metadata instead.

The key requirement is observability.

---

## E. Evaluator awareness

Teach the evaluator to interpret the new filter metadata when available.

Examples:
- if fallback had to re-allow weak sources, evaluator should understand why source quality stayed mixed,
- if the filter applied cleanly and weak sources were largely removed, evaluator can rate source quality more confidently.

This can be done lightly in v1 — just enough to avoid blind scoring.

---

## 6. Suggested functions / seams

Possible additions in `research_runtime.py`:
- `_filter_hits_for_extraction(query: str, hits: tuple[SearchHit, ...]) -> tuple[SearchHit, ...]`
- `_should_keep_for_procedural_extraction(query: str, hit: SearchHit) -> bool`
- `_best_secondary_procedural_hits(...)`
- `_filter_summary(...)`

Keep this procedural-admin-specific in v1. Do not over-abstract yet.

---

## 7. Tests to add

### A. Unit tests for filtering policy

1. **official + blog + forum + video**
- official docs survive
- forum/video are dropped
- blog is dropped or kept only as fallback depending on the mix

2. **official + secondary vendor doc**
- official remains primary
- secondary vendor doc can survive as support

3. **only weak sources available**
- fallback safety rail prevents empty evidence set
- best secondary source survives

4. **off-topic noisy source**
- dropped before extraction even if it has keyword overlap

### B. Runtime-oriented test

A focused fake-runtime test should verify that extracted findings for a procedural query are formed from filtered hits, not the raw unfiltered set.

---

## 8. Verification steps

After implementation:
1. run focused unit tests,
2. run full repo gate,
3. rerun quick SCCM procedural query,
4. inspect evaluator output,
5. optionally rerun the procedural row of the benchmark baseline.

---

## 9. Success criteria

Minimum success:
- official documentation survives and dominates the extracted procedural evidence,
- forum/video/snippet noise no longer meaningfully reaches extracted findings,
- fallback works when official docs are absent,
- telemetry shows what the filter did,
- full test gate remains green.

Preferred success on SCCM query:
- `source_quality_verdict = strong` or clearly cleaner `mixed`,
- `relevance_verdict = strong`,
- `truthfulness_verdict = strong`,
- `should_revise_report = false`,
- top extracted findings are clearly authority-first.

---

## 10. Rollback

If the slice harms coverage or causes over-filtering:
- remove the pre-extraction filter hook,
- keep query shaping and authority-first retrieval,
- leave evaluator/benchmark changes intact.

That rollback is low-risk because the new layer is a single bounded insertion point.

---

## 11. Recommended execution order

1. add filter helper,
2. wire filter before extraction,
3. add telemetry,
4. add focused tests,
5. run full gate,
6. rerun SCCM case,
7. write follow-up note with measured effect.

---

## 12. Final recommendation

Proceed with this slice as the next implementation step when Deep Research optimization resumes.

Reason:
- it follows the evidence,
- it attacks the remaining bottleneck at the right layer,
- and it is still bounded enough to verify honestly.
