# Deep Research authority-first reranking follow-up — 2026-06-21

Status: completed bounded slice
Date: 2026-06-21
Scope: first authority-first retrieval/reranking pass for procedural-admin queries.

## 1. Goal

Strengthen procedural/admin query handling by introducing explicit authority signals rather than only adding more domain bans.

---

## 2. Changes made

### A. Authority signal heuristic
Added `_authority_signal_score()` for procedural/admin queries.

Current positive signals include:
- `learn.microsoft.com`
- Microsoft Learn phrasing in title/snippet/url
- ConfigMgr/MECM documentation path indicators such as `/intune/configmgr/` or `/mem/configmgr/`
- product-documentation style phrases like `Create configuration baselines` and `Compliance Settings`

Current negative signals include:
- blog/community/video/forum markers

### B. Relevance scoring integration
Integrated authority signal scoring into `_general_relevance_score()` so procedural/admin sources with stronger authority cues get a real scoring boost.

### C. Procedural source ranking integration
Integrated authority signals into `_source_rank_for_query()` so strong documentation-like sources get rank improvement beyond plain source-type sorting.

### D. Tests
Added focused test coverage proving that Microsoft Learn scores above a community blog for the SCCM baseline query class.

---

## 3. Verification

### Tests
- focused gate: `tests/unit/application/test_application_research.py` → passed

### Quick SCCM rerun
Observed runtime result for:
- `How do I create configuration baselines in SCCM?`

Observed outcome:
- `search_providers = ['searxng']`
- result still did **not** capture official Microsoft documentation in the persisted evidence set,
- top URLs remained dominated by community/blog-style material,
- evaluator still produced:
  - `source_quality_verdict = weak`
  - `relevance_verdict = weak`
  - `truthfulness_verdict = mixed`
  - `should_revise_report = true`

This means the new authority-aware reranking logic is directionally correct, but it is **not sufficient on its own** to solve the SCCM class weakness in the live runtime.

---

## 4. Strongest conclusion

The bottleneck is now clearer.

This is no longer primarily a local ranking-order problem inside already-accepted findings.
It is a broader retrieval/evidence-selection problem:
- the live search result set itself can still be weak,
- strong official documentation may not be arriving early enough,
- or the final evidence set is still being built from partial/community material despite the new ranking preferences.

In other words:
- authority-first reranking helped the policy layer,
- but did not yet materially change the runtime outcome for the hardest procedural query.

---

## 5. Recommendation

Do not keep stacking small heuristic tweaks onto the same layer.

The next meaningful slice should move one layer earlier or one layer stronger, for example:
1. explicit query rewriting / expansion for procedural-admin queries toward official-doc intent,
2. authority-first source filtering before extraction/synthesis,
3. or domain-prioritized retrieval for known documentation ecosystems.

The current evaluator and benchmark baseline are already good enough to measure that next step honestly.

---

## 6. Verdict

This slice was useful, but not sufficient.

It successfully narrowed the problem:
- the remaining SCCM weakness is not just cosmetic ranking inside the final report,
- it likely needs stronger retrieval shaping or authority-aware filtering before the later synthesis stages.
