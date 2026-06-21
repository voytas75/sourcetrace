# Deep Research procedural ranking polish — 2026-06-21

Status: completed bounded slice
Date: 2026-06-21
Scope: one additional procedural-query ranking pass after telemetry + source-quality hardening.

## 1. Goal

Push remaining weak community-style procedural sources further down when stronger official/documentation sources exist.

Targeted residual noise classes:
- Stack Overflow,
- GitHub gists / snippet repos,
- loose community pages,
- forum-style references.

---

## 2. Changes made

### A. Weak-source detection
Extended procedural weak-source detection to treat these as weak evidence classes for procedural/admin queries:
- `stackoverflow.com`
- `gist.github.com`
- forum/Q&A style paths

### B. Source typing and ranking
Added/refined source typing so that:
- Stack Overflow is treated as `forum`,
- GitHub Gists are treated as `snippet_repo`,
- procedural-query ranking demotes these classes more aggressively.

### C. Top findings selection
For procedural queries, top-findings selection now blocks these source classes unless stronger material is absent:
- `forum`
- `video`
- `snippet_repo`

### D. Tests
Focused tests now verify that procedural-query relevance/ranking rejects or excludes:
- Reddit,
- Stack Overflow,
- GitHub Gists,
- YouTube
when better official documentation exists.

---

## 3. Verification

### Automated tests
- focused gate: `tests/unit/application/test_application_research.py` → passed
- full repo gate: `397 passed`

### Quick SCCM rerun
Observed runtime result for:
- `How do I create configuration baselines in SCCM?`

Observed:
- `search_providers = ['searxng']`
- Microsoft Learn still appears in top findings,
- a community blog still appeared first in raw findings,
- Stack Overflow / gist-style sources were pushed out of the visible top slice,
- the answer remained operationally plausible and leaned mainly on the stronger procedural model.

---

## 4. Verdict

This pass improved the procedural-query floor, but it did **not fully solve ranking purity**.

What improved:
- weaker community/Q&A/snippet sources are now treated more harshly,
- the visible top result set is cleaner than before,
- the repo remains green.

What remains imperfect:
- a non-official community blog can still outrank Microsoft Learn in raw findings,
- some irrelevant-but-keyword-matching sources can still leak into the wider raw finding set.

So the current state is:
- better,
- cleaner,
- still not fully authoritative-first.

---

## 5. Recommendation

Do **not** keep polishing this in many tiny heuristic passes right now.

The return is already diminishing.

The next best move is now to shift to the planned:

## post-result evaluator v1

Why:
- the retrieval/ranking floor is now meaningfully better than before,
- telemetry is truthful,
- evaluator work can now add structured diagnostic visibility without merely masking obviously broken upstream behavior.

If a future ranking pass is needed later, it should likely use a more explicit authority signal or query-class-aware rescoring rather than more ad hoc domain bans.
