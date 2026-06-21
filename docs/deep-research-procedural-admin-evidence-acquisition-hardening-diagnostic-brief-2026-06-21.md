# Deep Research procedural/admin evidence acquisition hardening — diagnostic brief

Status: diagnostic brief
Date: 2026-06-21
Scope: narrow diagnosis of why official procedural documentation still fails to land in the evidence set for `procedural_admin` queries.

## 1. Problem statement

The current weakest benchmark class is still `procedural_admin`.

Most recent signal:
- benchmark rerun improved the SCCM procedural row from `7/12` to `9/12`,
- but `source_quality` remains `0`,
- evaluator still says: `No official procedural documentation was found in the evidence set.`

That means the remaining bottleneck is not artifact scaffolding or reporting.
It is still evidence acquisition.

---

## 2. Observed pipeline posture

The current pipeline already has the right high-level moves:
- procedural query shaping,
- authority signals favoring `learn.microsoft.com`,
- pre-extraction filtering for `procedural_admin`,
- evidence packing that prefers official docs when they exist.

So the likely failure is narrower:
- official-doc candidates are not being surfaced by the current search path,
- or they are being surfaced too sparsely,
- or the provider-backed synthetic benchmark path is too weak to expose them.

---

## 3. Key diagnostic conclusion

The current benchmark rerun used a synthetic provider-backed `web_search` fallback path.
In that path, the search adapter returned only a generic provider hit per query.

That means:
- the rerun correctly showed that `procedural_admin` is still the weakest class,
- but it did **not** yet prove that the current procedural evidence pipeline fails under a realistic official-doc-capable search surface.

So the immediate next step should be:
- test the procedural row against a search surface that actually contains official Microsoft Learn candidates,
- and only then change retrieval/filtering logic if official docs still fail to survive.

---

## 4. Recommended next slice

Use a bounded procedural/admin acquisition check with a realistic hit set.

Two good options:
1. targeted unit/integration-style runtime check with Microsoft Learn + secondary hits mixed together,
2. live runtime procedural rerun through a search backend that can actually return official docs.

### Recommendation
Start with option 1 first, because it isolates the pipeline cleanly and cheaply.

---

## 5. Decision

Do **not** patch retrieval/filtering again yet.

First verify whether the current pipeline already succeeds when official procedural hits are actually available in the input search set.

If it does, the real remaining issue is search-surface quality, not downstream evidence handling.
If it does not, patch the exact drop point.

---

## 6. Practical next move

Run one narrow procedural/admin runtime check with a mixed hit set containing:
- 2–3 Microsoft Learn SCCM baseline pages,
- 1–2 community/blog/forum pages,
- optional generic docs page.

Then inspect:
- kept hits after pre-extraction filter,
- extracted findings,
- top findings,
- evaluator verdict.

That will tell us whether the bottleneck is:
- upstream search recall,
- filter policy,
- extraction,
- or synthesis/evaluator path.
