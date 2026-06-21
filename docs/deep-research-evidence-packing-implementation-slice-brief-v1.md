# Deep Research evidence packing implementation slice brief v1

Status: proposed implementation slice
Date: 2026-06-21
Scope: bounded implementation brief for adding evidence packing before synthesis in SourceTrace Deep Research.

## 1. Slice verdict

This is the best next tactical slice in the Karpathy-aligned Deep Research roadmap.

Reason:
- retrieval and authority filtering have already improved materially,
- evaluator and benchmark infrastructure already exist,
- the biggest remaining short-term bottleneck is not finding evidence, but **packing the right evidence into synthesis**.

So this slice targets context discipline rather than more retrieval tuning.

---

## 2. Problem statement

Current Deep Research behavior is improved, but still too flat between:
- extracted findings,
- and final synthesis.

The system currently lacks a dedicated layer that intentionally distinguishes:
- evidence that should drive the answer,
- evidence that should support or qualify the answer,
- evidence that is background-only and should not dominate synthesis.

Without this, even a better retrieval stack can still produce noisy or diluted reports.

---

## 3. Objective

Add a bounded **evidence packing** layer before synthesis.

The packed evidence should classify extracted findings into at least:
- `core`
- `supporting`
- `background`

The synthesis step should then operate on this packed structure rather than a flat tuple of findings.

Desired outcome:
- stronger answer focus,
- lower synthesis noise,
- better uncertainty phrasing,
- cleaner use of authoritative evidence,
- improved evaluator outcomes without widening retrieval scope.

---

## 4. Non-goals

Do not do these in this slice:
- no compiled artifact system yet,
- no artifact lint layer yet,
- no auto-rewrite,
- no new search backend,
- no major UI redesign,
- no generalized policy engine for every research class.

This slice is about **packing evidence better before synthesis**.

---

## 5. Proposed design

## A. Introduce packed evidence model

Add a small internal model, for example in `research_runtime.py` or an adjacent module.

Suggested shape:
- `PackedEvidence`
- `PackedEvidenceItem`

Possible fields:
- role: `core | supporting | background`
- finding reference / finding content
- score / rationale
- source type
- authority signal summary

Keep it lightweight in v1.
No need for heavy domain-model proliferation yet.

---

## B. Add evidence packer function

Suggested seam:
- `_pack_evidence_for_synthesis(query: str, findings: tuple[ExtractedFinding, ...]) -> PackedEvidence`

Responsibilities:
1. score findings for synthesis usefulness,
2. identify top answer-driving evidence,
3. keep some supporting qualifiers,
4. demote broader or redundant context into background,
5. preserve enough diversity to avoid brittle overfitting.

---

## C. Use query-class-aware packing rules

The packer should use existing query classification where helpful.

### For `procedural_admin`
- core:
  - official docs,
  - strong procedural vendor docs,
  - direct how-to / baseline / deployment guidance
- supporting:
  - secondary docs clarifying steps or edge cases
- background:
  - generic explainers,
  - broad product overviews,
  - low-authority context that should not drive the answer

### For `market_symbol`
- core:
  - exact-symbol market data or directly relevant chart/data pages
- supporting:
  - corroborating analytics
- background:
  - broader market commentary

### For `broad_concept`
- core:
  - strongest explanatory/architectural findings
- supporting:
  - additional perspectives
- background:
  - wider thematic context that should not dominate the answer

Keep the first implementation narrow and heuristic.

---

## D. Change synthesis input contract

Current shape is effectively:
- `query + findings -> report`

Target shape:
- `query + packed_evidence -> report`

The synthesis step should receive or reconstruct a structured view such as:
- core findings list,
- supporting findings list,
- background findings list,
- compact summary of why those were selected.

Even if the synthesizer still renders from text, the text should be built from packed roles, not a flat dump.

---

## E. Telemetry / result visibility

Add minimal evidence-packing visibility to result metadata or stats.

Suggested fields:
- `packed_core_count`
- `packed_supporting_count`
- `packed_background_count`
- optionally `packing_policy_applied`

If `ResearchStats` is already crowded, attach a compact packing summary near evaluation/result metadata instead.

Observability matters because this slice should be benchmarkable.

---

## F. Evaluator awareness

Evaluator should later be able to use evidence-packing info when available.

Initial v1 recommendation:
- evaluator may note whether authoritative evidence actually drove the packed `core` set,
- evaluator may downgrade source quality if weak evidence leaks into `core`.

Do this lightly in the same slice only if it stays small.
Otherwise, defer to follow-up.

---

## 6. Suggested functions / seams

Possible additions:
- `_pack_evidence_for_synthesis(...)`
- `_evidence_role_for_finding(...)`
- `_core_evidence_limit_for_query_class(...)`
- `_supporting_evidence_limit_for_query_class(...)`
- `_render_packed_evidence_for_synthesis(...)`

Keep v1 simple.
Prefer a few explicit helpers over abstract frameworks.

---

## 7. Tests to add

## A. Unit tests for packing roles

1. **procedural query with official + blog + generic product overview**
- official guidance lands in `core`
- useful secondary guide lands in `supporting`
- generic overview lands in `background`

2. **market-symbol query with exact pair + broad crypto analysis**
- exact pair data lands in `core`
- broad market commentary stays `background`

3. **broad concept query**
- strongest explanatory findings become `core`
- redundant or looser context becomes `supporting/background`

## B. Runtime-oriented test

A focused test should verify that synthesis input is built from packed evidence roles rather than directly from the flat finding tuple.

## C. Optional evaluator test

If evaluator awareness is included:
- weak evidence inside `core` should be reflected in verdict logic.

---

## 8. Verification steps

After implementation:
1. run focused unit tests,
2. run full repo gate,
3. rerun at least one procedural query,
4. inspect packed evidence metadata,
5. compare report cleanliness before/after,
6. optionally rerun the canonical benchmark pack.

---

## 9. Success criteria

Minimum success:
- synthesis is no longer fed a flat undifferentiated evidence list,
- packed roles exist and are used,
- authoritative evidence appears in `core` for procedural queries,
- generic/noisy evidence is demoted to `supporting` or `background`,
- full gate remains green.

Preferred success:
- procedural report quality improves in focus and clarity,
- evaluator sees cleaner source-quality posture,
- benchmark notes show reduced synthesis drift.

---

## 10. Rollback

If the slice causes over-compression or brittle reports:
- remove the packed-evidence hook,
- keep retrieval, filtering, evaluator, and benchmark improvements,
- fall back to existing synthesis path.

Rollback is low-risk if evidence packing is inserted as a single bounded layer.

---

## 11. Recommended execution order

1. add packed evidence model/helper,
2. classify findings into roles,
3. wire packed structure into synthesis,
4. add telemetry,
5. add focused tests,
6. run full gate,
7. rerun procedural case,
8. write follow-up with measured impact.

---

## 12. Final recommendation

Proceed with this as the next implementation slice when Deep Research workflow updates resume.

Reason:
- it addresses the clearest remaining tactical gap,
- it aligns tightly with the Karpathy-style context-discipline principle,
- and it is the right precursor to later compiled artifacts.
