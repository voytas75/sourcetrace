# Deep Research procedural_admin unified-search integration v1 brief

Status: implementation brief
Date: 2026-06-21
Scope: controlled Unified Search integration for `procedural_admin` queries with safe fallback to the current search path.

## 1. Objective

Promote the successful Unified Search spike into a bounded v1 integration for `procedural_admin` queries.

The goal is not a global replacement.
The goal is to improve official-doc recall for procedural/admin queries while preserving a safe fallback path.

---

## 2. Policy

For `procedural_admin` only:
1. try Unified Search first,
2. if the returned hit set is too weak, fall back to the current search path,
3. keep downstream authority-first filtering, extraction, evaluator, and artifact flow unchanged.

---

## 3. Fallback triggers

Fallback to the current path if Unified Search returns:
- no hits,
- or no official-doc-like hits,
- or a top slice that fails a minimal quality threshold.

### Initial threshold
Conservative v1 rule:
- if no hit in the top 5 looks like `official_docs` / strong authority, use fallback.

That keeps the decision simple and cheap.

---

## 4. Source posture

Do not use noisy unrestricted Unified Search defaults for this query class.

v1 should stay controlled and biased.
Initial posture:
- prefer a controlled Unified Search source set suitable for procedural queries,
- preserve reversibility.

---

## 5. Success criteria

For the procedural SCCM row, v1 is successful if it reliably improves at least these outcomes without regressions:
- official docs present in evidence set,
- `source_quality` improves to at least `mixed`,
- `relevance` stays `strong`,
- `should_revise_report = false`.\n
---

## 6. Rollback

Low-risk rollback:
- disable Unified Search path for `procedural_admin`,
- keep the previous current search path untouched.

Because the integration is query-class-specific and fallback-backed, rollback is trivial.
