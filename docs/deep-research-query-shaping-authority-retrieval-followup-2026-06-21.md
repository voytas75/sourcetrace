# Deep Research query shaping + authority-first retrieval follow-up — 2026-06-21

Status: completed bounded slice
Date: 2026-06-21
Scope: improve procedural-admin query handling by moving authority intent earlier into search query generation.

## 1. Goal

Address the remaining SCCM / procedural-admin weakness at an earlier stage than final reranking.

The hypothesis was:
- if official-doc intent is injected into the query generation layer,
- retrieval quality should improve enough that later ranking/evaluation stages finally see better evidence.

---

## 2. Changes made

### A. Procedural query variants
Added `_procedural_query_variants()` to generate authority-seeking search forms such as:
- `site:learn.microsoft.com ...`
- `... Microsoft Learn`
- `... official documentation`
- more specific ConfigMgr/MECM baseline phrases when the query indicates SCCM/baseline intent.

### B. Query generator integration
Updated `StubQueryGenerator` so procedural-admin queries now use those authority-seeking variants in round 1 and keep official-doc-oriented forms in round 2.

This moves the retrieval posture from:
- generic procedural query wording

to:
- explicit official-doc intent embedded in the search layer.

### C. Tests
Added focused tests verifying that:
- procedural query generation now includes `site:learn.microsoft.com`,
- procedural variants include official-doc wording,
- the existing authority signal behavior still holds.

---

## 3. Verification

### Tests
- focused gate: `tests/unit/application/test_application_research.py` → passed (`17 passed`)

### Quick SCCM rerun
Observed runtime result for:
- `How do I create configuration baselines in SCCM?`

Observed improvements:
- `search_providers = ['searxng']`
- official Microsoft documentation now entered the persisted evidence set,
- top URLs now include multiple `learn.microsoft.com` pages,
- evaluator shifted to:
  - `source_quality_verdict = mixed`
  - `relevance_verdict = strong`
  - `truthfulness_verdict = strong`
  - `should_revise_report = false`

Representative top URLs now included:
- `learn.microsoft.com/.../create-configuration-baselines`
- `learn.microsoft.com/.../deploy-configuration-baselines`
- `learn.microsoft.com/.../about-configuration-baselines-and-configuration-items`
- `learn.microsoft.com/.../new-cmbaseline`

A community blog still appeared in the top set, so the class is not perfectly clean yet, but the result quality clearly improved.

---

## 4. Verdict

This slice succeeded.

The strongest evidence is that the problem really did start too early for reranking alone to fix.
Once query shaping carried authority intent directly into retrieval, the procedural/admin result improved materially.

So the current understanding is now sharper:
- authority-aware reranking alone was insufficient,
- query shaping + authority-first retrieval moved the result class into a much healthier state.

---

## 5. Remaining weakness

The SCCM/procedural class is improved, but not yet perfectly authority-pure.

What remains:
- community material can still enter the wider result set,
- source-quality is `mixed`, not `strong`,
- stronger pre-extraction authority filtering may still be worthwhile later.

---

## 6. Recommendation

Do not widen scope too fast.

The next best move, if continuing this track, is now smaller and cleaner than before:
- authority-first filtering before extraction/synthesis,
- or a lighter domain-priority policy for known doc ecosystems,
- then rerun the procedural benchmark case.

But the major bottleneck has been materially reduced.
