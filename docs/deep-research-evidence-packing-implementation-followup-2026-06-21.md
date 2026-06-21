# Deep Research evidence packing implementation follow-up — 2026-06-21

Status: completed bounded slice
Date: 2026-06-21
Scope: implementation of evidence packing before synthesis for SourceTrace Deep Research.

## 1. Goal

Introduce a dedicated evidence-packing layer so synthesis no longer operates on a flat, undifferentiated finding set.

Target behavior:
- `core` evidence should drive the answer,
- `supporting` evidence should qualify or reinforce it,
- `background` evidence should stay available without dominating the final synthesis.

---

## 2. What was implemented

### A. Packed evidence model
Added lightweight evidence-packing support in `research_runtime.py`:
- `PackedEvidence`
- `_pack_evidence_for_synthesis(...)`

The packer currently assigns findings into:
- `core`
- `supporting`
- `background`

### B. Query-class-aware packing
Added initial heuristic packing behavior by query class.

Most important v1 case:
- `procedural_admin`
  - official Microsoft/vendor procedural docs are promoted into `core`,
  - useful secondary docs remain `supporting`,
  - broader or weaker context falls to `background`.

### C. Synthesis integration
The synthesizer now uses packed evidence instead of treating all findings as equally answer-driving.

Practical effects:
- report summary uses the packed answer-driving set,
- key findings prefer `core + supporting`,
- background context is acknowledged separately instead of silently driving the answer.

### D. Telemetry
Extended `ResearchStats` with evidence-packing counts:
- `packed_core_count`
- `packed_supporting_count`
- `packed_background_count`

---

## 3. Tests

Added focused unit coverage for:
- procedural evidence packing preferring official docs as `core`,
- existing authority-first and evaluator behavior remaining intact.

Focused gate after change:
- `20 passed`

Full repo gate after change:
- `404 passed`

---

## 4. Quick procedural rerun result

Reran the SCCM benchmark-style procedural query:
- `How do I create configuration baselines in SCCM?`

Observed result:
- `search_providers = ['searxng']`
- top URLs were dominated by official Microsoft documentation,
- the report became cleaner, more procedural, and more directly grounded in Microsoft documentation,
- evaluator shifted to:
  - `source_quality_verdict = strong`
  - `relevance_verdict = strong`
  - `truthfulness_verdict = strong`
  - `should_revise_report = false`
  - `recommended_next_check = No immediate corrective check required.`

### Representative top URLs
- `learn.microsoft.com/.../create-configuration-baselines`
- `learn.microsoft.com/.../deploy-configuration-baselines`
- `learn.microsoft.com/.../new-cmbaseline`
- `learn.microsoft.com/.../about-configuration-baselines-and-configuration-items`
- `learn.microsoft.com/.../get-started-with-compliance-settings`

A secondary community guide still appeared later in the set, but did not dominate the answer-driving path.

---

## 5. Verdict

This slice succeeded.

Evidence packing produced the intended effect:
- the synthesis path is cleaner,
- official docs now clearly drive the procedural answer,
- evaluator output improved from previously `mixed` source quality to `strong`,
- the procedural SCCM case now looks materially healthier end-to-end.

This is the strongest confirmation so far of the Karpathy-aligned direction:
- retrieval quality matters,
- but **context discipline before synthesis** matters just as much.

---

## 6. Recommendation

The next strategic slice is now more justified than before:
- `compiled research artifact v1`

Reason:
- evidence flow is now clean enough that preserving it as a reusable artifact is much less likely to fossilize noise.
