# Deep Research compiled artifact evidence carry-forward v2 slice brief

Status: proposed implementation slice
Date: 2026-06-21
Scope: narrow projection fix focused specifically on missing/weak supporting evidence in compiled artifacts.

## 1. Slice verdict

This is now the narrowest real bottleneck.

After enrichment v1:
- source refs improved,
- follow-up carry-forward improved,
- but supporting evidence can still collapse to empty in sparse paths.

So the next slice should not be another broad enrichment pass.
It should specifically fix evidence carry-forward.

---

## 2. Problem statement

Compiled artifacts still sometimes lose evidence even when the upstream run has enough material to preserve something useful.

Observed symptom from the latest spot-check:
- `supporting_evidence = 0`
- lint still flags `missing_evidence`

This means current evidence projection is still too dependent on `raw_findings` / `sources` being populated in one specific way.

---

## 3. Objective

Make compiled artifacts reliably carry forward at least the best available evidence context from the run result.

Priority:
1. preserve real finding-derived evidence when available,
2. preserve source-derived evidence when findings are sparse,
3. avoid empty `supporting_evidence` unless the run is truly empty,
4. keep the behavior deterministic and cheap.

---

## 4. Non-goals

Do not do these in this slice:
- no LLM re-extraction,
- no UI work,
- no new lint logic,
- no cross-run merge,
- no full rewrite of result artifacts.

---

## 5. Likely root cause

Current projection logic only looks at:
- `result.raw_findings`
- then `result.sources`

But sparse runtime paths can still produce:
- thin or absent raw findings,
- thin sources,
- while the report text itself still contains usable evidence-like signal in `## Key findings` or `## Current answer`.

So v2 should add a final report-derived fallback.

---

## 6. Recommended implementation

Add one more fallback layer for `supporting_evidence`:

1. raw findings
2. result sources
3. report `## Key findings` lines
4. report `## Current answer` fallback snippet

For report-derived fallback refs:
- use synthetic local refs like `about:report/{job_id}#key-findings-1`
- preserve concise text summary
- make it explicit that this is report-derived evidence, not a raw external source

This is not perfect provenance, but it is better than empty evidence and still truthful if labeled clearly.

---

## 7. Rules

### A. Prefer external evidence when present
Real findings/sources stay first-class.
Report-derived fallback should only activate when those are absent.

### B. Keep report-derived fallback clearly synthetic
Do not pretend it is an external source.
Use an internal URL-like ref and explicit title labeling.

### C. Small cap
Keep evidence count tight: 3–5 max.

### D. Deterministic dedup
If report-derived fallback repeats current answer / key findings too closely, keep the better one only.

---

## 8. Tests to add

### A. Sparse result with no findings/sources but with key findings in report
Expected:
- `supporting_evidence` is non-empty
- refs use synthetic report-derived identifiers

### B. Sparse result with no key findings but with current answer
Expected:
- one fallback evidence ref from current answer

### C. Normal rich result
Expected:
- external evidence still wins over report-derived fallback

---

## 9. Verification steps

After implementation:
1. focused tests,
2. full gate,
3. runtime spot-check,
4. confirm `supporting_evidence > 0` in previously thin path,
5. inspect lint delta.

---

## 10. Success criteria

Minimum success:
- compiled artifact no longer loses all supporting evidence in sparse but non-empty paths,
- lint `missing_evidence` drops where appropriate,
- full gate remains green.

Preferred success:
- evidence carry-forward remains truthful while avoiding hollow artifacts.

---

## 11. Final recommendation

Proceed now.

This is a small, highly local slice with a clear target and a measurable payoff.
