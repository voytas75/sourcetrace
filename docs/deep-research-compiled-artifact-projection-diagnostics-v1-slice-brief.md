# Deep Research compiled artifact projection diagnostics v1 slice brief

Status: proposed diagnostic slice
Date: 2026-06-21
Scope: inspect the exact runtime shape reaching compiled artifact projection in the failing sparse path.

## 1. Slice verdict

This is now the correct next step.

We have already done enough heuristic guessing.
The next move should be direct observation.

---

## 2. Problem statement

Evidence fallback logic works in focused tests, but still does not trigger in the real runtime spot-check path.

That means the issue is probably in the actual runtime data shape reaching `_compile_research_artifact(...)`.

Likely candidates:
- `result.result` shape differs from the synthetic test assumption,
- `raw_report` vs `result` matters,
- `raw_findings` / `sources` are emptier or shaped differently than expected,
- report section extraction is not hitting the actual generated markdown.

---

## 3. Objective

Inspect the real runtime projection inputs for the failing path and answer one concrete question:

> What exact data shape reaches compiled artifact projection when `supporting_evidence` still ends up empty?

---

## 4. Non-goals

- no broad redesign
- no speculative heuristics first
- no new knowledge-layer abstractions

This is a short diagnostic slice.

---

## 5. Recommended implementation

Add a minimal internal diagnostic helper that emits a compact projection input snapshot, for example:
- `job_id`
- whether `raw_findings` exists and count
- whether `sources` exists and count
- small excerpt of `result.result`
- small excerpt of `raw_report`
- extracted `Current answer`
- extracted `Key findings`
- extracted `Next checks`

This can stay internal and test/runtime-only.

---

## 6. Verification

After adding the diagnostic helper:
1. run the sparse runtime spot-check,
2. capture the projection input snapshot,
3. identify the mismatch,
4. if fix is obvious and small, patch immediately in the same flow.

---

## 7. Success criteria

Minimum success:
- we stop guessing,
- we know the exact failing runtime shape,
- the next fix is based on observation, not assumption.

Preferred success:
- the diagnostic immediately reveals a tiny patch and we can apply it right away.

---

## 8. Final recommendation

Proceed now.

This is the shortest path to the real fix.
