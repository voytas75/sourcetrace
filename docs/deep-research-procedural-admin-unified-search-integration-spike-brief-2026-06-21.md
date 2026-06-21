# Deep Research procedural_admin unified-search integration spike brief

Status: proposed spike
Date: 2026-06-21
Scope: bounded experiment to test Unified Search as an upstream acquisition path for `procedural_admin` queries.

## 1. Why this spike

Current diagnosis says:
- downstream procedural/admin handling is mostly working,
- the weakest layer is upstream search recall / acquisition,
- Unified Search shows promising recall for Microsoft Learn when constrained appropriately.

So the next sensible step is not a full search-stack rewrite.
It is a small integration spike.

---

## 2. Objective

Answer one concrete question:

> If `procedural_admin` queries use a controlled Unified Search path, does the procedural benchmark row improve materially versus the current path?

---

## 3. Constraints

- no global search-default switch,
- no broad integration for every query class,
- no deep refactor of the search subsystem,
- keep the change narrow and removable.

---

## 4. Recommended spike shape

For `procedural_admin` only:
- allow a Unified Search-backed adapter/path,
- prefer a controlled source mix rather than noisy all-sources default,
- keep current downstream authority-first filtering/evidence packing/evaluator intact.

### Suggested source posture
Start with a controlled source set that performed best in the comparison run.
Initial candidate:
- `google`

If needed later:
- `google` plus one additional provider,
- but do not begin with noisy wide-source blending.

---

## 5. Success criteria

The spike is successful if the SCCM procedural benchmark row shows at least one of these without regressing truthfulness:
- official docs present in the evidence set,
- improved `source_quality`,
- improved `relevance`,
- `should_revise_report = false`.

---

## 6. Evaluation method

Run one controlled procedural rerun:
- query: `How do I create configuration baselines in SCCM?`
- current path vs unified-search procedural path

Compare:
- top findings URLs,
- evaluator verdicts,
- recommended next check,
- whether official docs are present.

---

## 7. Decision rule

- If Unified Search materially improves the procedural row: keep the integration path as an optional or query-class-specific route.
- If it only improves recall but stays too noisy: keep it only with tighter source control.
- If it does not improve the row materially: do not integrate now.

---

## 8. Expected best outcome

Likely best outcome:
- worth integrating for `procedural_admin`,
- but only with source control / biasing,
- not as a global replacement for the current search path.
