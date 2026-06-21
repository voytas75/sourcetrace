# Karpathy gap analysis → SourceTrace Deep Research update plan v1

Status: proposed update plan
Date: 2026-06-21
Scope: workflow and logic update plan for SourceTrace Deep Research, using Karpathy-style LLM usage principles as a design lens.

## 1. Executive verdict

SourceTrace Deep Research is already strong in operator-facing mechanics:
- query shaping,
- authority-aware retrieval,
- pre-extraction filtering,
- evaluator v1,
- benchmark harness,
- modern `/research` UI.

But it is still weaker than the Karpathy-style ideal in three places that matter most:
1. **context discipline before synthesis**,
2. **durable compiled research artifacts**,
3. **follow-up / artifact-health logic beyond a single run**.

So the right update plan is **not** “make prompts smarter”.
It is:
- tighten evidence packing,
- promote runs into structured artifacts,
- then add lint / branch logic over those artifacts.

---

## 2. Karpathy principles used as design lens

This plan uses the following distilled principles:
- workflow-first, not prompt-first,
- tools are part of cognition,
- context is scarce and should be intentionally packed,
- knowledge should accumulate into reusable artifacts,
- good systems suggest the next useful question,
- architecture of work matters more than prompt cleverness.

These are not copied literally from one personal workflow implementation.
They are used here as system design heuristics.

---

## 3. Current SourceTrace state

## Already strong
- query-class-aware behavior has started to exist,
- procedural-admin retrieval is materially improved,
- authority-first logic now affects retrieval and pre-extraction filtering,
- evaluator gives structured post-result diagnostics,
- benchmark reporting is evaluator-aware,
- operator UI is strong enough for iterative testing.

## Still weak or incomplete
- synthesis still lacks a dedicated evidence-packing layer,
- research artifacts are persisted but still too run-centric,
- evaluator is not yet a research-artifact lint layer,
- follow-up questions are present only as light `next checks`,
- topic-level accumulation remains weak.

---

## 4. Gap map

## Gap A — evidence packing before synthesis

### Current state
SourceTrace now does better retrieval and filtering, but synthesis still does not explicitly distinguish:
- core evidence,
- supporting evidence,
- background-only context.

### Why this matters
This is the biggest practical Karpathy-aligned gap.
A system can retrieve good material and still synthesize poorly if its reasoning context is noisy or flattened.

### Design implication
Add a dedicated **evidence packing** layer before synthesis.

### Priority
**Highest**

---

## Gap B — compiled research artifact

### Current state
Research results are persisted as result artifacts, but they are still largely run-centric.

### Why this matters
Karpathy-style workflows accumulate knowledge rather than letting each run remain a one-off answer blob.

### Design implication
Promote finished runs into a more structured, reusable artifact form:
- topic note,
- dossier,
- evidence-backed claim structure,
- explicit open questions.

### Priority
**High**

---

## Gap C — artifact lint / health

### Current state
Evaluator v1 scores one result well enough, but does not yet function as an artifact health/lint layer.

### Why this matters
A research system becomes more valuable when it can inspect the health of accumulated knowledge:
- provenance gaps,
- contradictions,
- unverified claims,
- unresolved branches.

### Design implication
Add a later **artifact lint** layer after compiled artifacts exist.

### Priority
**Medium-high**, but only after compiled artifacts begin to exist.

---

## Gap D — follow-up branch logic

### Current state
There are `Next checks` and evaluator `missing_checks`, but no first-class branch proposal model.

### Why this matters
Karpathy-style systems are not just answer systems. They help carry the inquiry forward.

### Design implication
Introduce explicit outputs like:
- `open_questions`
- `high_value_followups`
- `branch_candidates`
- `evidence_gaps`

### Priority
**Medium**

---

## 5. Target workflow

Recommended target workflow evolution:

### Current rough flow
`query -> classify -> shape -> search -> authority filter -> extract -> synthesize -> evaluate`

### Planned upgraded flow
`query -> classify -> shape -> search -> authority filter -> extract -> evidence pack -> synthesize -> evaluate -> file compiled artifact -> lint artifact -> propose follow-up branches`

This is the correct long-term shape if SourceTrace Deep Research is to become more Karpathy-compatible.

---

## 6. Recommended slices and order

## Slice 1 — evidence packing before synthesis

### Goal
Increase context discipline and reduce synthesis noise.

### What to add
- evidence roles:
  - `core`
  - `supporting`
  - `background`
- explicit pack selection before synthesis,
- smaller, more intentional synthesis context,
- optional pack summary metadata.

### Expected payoff
Very high.
This is the best next tactical slice.

### Definition of done
- synthesis no longer operates on a flat, loosely selected evidence set,
- core evidence is intentionally selected,
- supporting/background evidence are kept separate,
- report quality improves without reducing core answer coverage.

---

## Slice 2 — compiled research artifact v1

### Goal
Promote research results from transient run outputs into reusable topic artifacts.

### What to add
- structured artifact shape, for example:
  - topic title / scope,
  - summary,
  - claims,
  - supporting evidence,
  - open questions,
  - next checks,
  - source references.
- ability to persist as a reusable artifact, not just a run result.

### Expected payoff
Very high strategically.
This is the first real bridge into cumulative knowledge workflow.

### Definition of done
- at least one completed run can be transformed into a structured artifact,
- the artifact is reusable later,
- the artifact is visibly distinct from the ephemeral run result.

---

## Slice 3 — artifact lint / health checks

### Goal
Move from result evaluation to artifact health inspection.

### What to add
- provenance gap detection,
- contradiction flags,
- weakly supported claims,
- stale or unsupported sections,
- suggested repair actions.

### Expected payoff
High, but dependent on Slice 2.

### Definition of done
- a compiled artifact can be linted,
- lint output identifies gaps/questions/contradictions,
- the output is operator-readable and structurally actionable.

---

## Slice 4 — follow-up branch proposals

### Goal
Make Deep Research propose next useful inquiries instead of ending at “answer delivered”.

### What to add
- `open_questions`
- `high_value_followups`
- `branch_candidates`
- `stop_here_if_good_enough`

### Expected payoff
Medium-high.
Very aligned with Karpathy-style iterative inquiry.

### Definition of done
- every suitable artifact can emit structured follow-up branches,
- branches reflect evidence gaps rather than generic brainstorming.

---

## 7. Why this order is correct

This order avoids locking in noise too early.

### First: evidence packing
Without it, compiled artifacts may only fossilize weak context selection.

### Second: compiled artifact
Once runs are cleaner, it becomes worth preserving them as durable structures.

### Third: lint
Lint is much more valuable once there is a stable artifact to inspect.

### Fourth: follow-up branches
This becomes much more useful once both artifact structure and health checks exist.

---

## 8. Change impact by subsystem

## Querying / retrieval
- already significantly improved,
- should be considered “good enough for now” unless evidence packing shows a fresh bottleneck.

## Extraction
- now improved by authority-first filtering,
- next change should focus on output structuring rather than more procedural-admin retrieval tweaks.

## Synthesis
- major next focus area,
- needs evidence packing discipline.

## Evaluation
- good v1 foundation,
- should later split into:
  - result evaluation,
  - artifact linting.

## Persistence
- currently adequate for run artifacts,
- needs extension for compiled artifacts.

## UI\n- now good enough to support iterative development,
- future UI work should surface evidence roles, compiled artifacts, and lint findings rather than just polish visuals.

---

## 9. Risk notes

### Risk 1 — over-building too early
Avoid jumping straight to a giant knowledge system.
Start with compiled artifacts, not a full “LLM operating system”.

### Risk 2 — preserving noise
If evidence packing is skipped, compiled artifacts may just preserve noisy synthesis decisions.

### Risk 3 — evaluator bloat
Do not overload evaluator v1 with all future lint behavior.
Keep result evaluation and artifact lint conceptually separate.

### Risk 4 — premature generalization
Keep early slices narrow.
Do not turn this immediately into a universal policy engine for every query class.

---

## 10. Concrete next step recommendation

The best next implementation brief to write is:

## `deep-research-evidence-packing-implementation-slice-brief-v1.md`

because evidence packing is the clearest remaining tactical bottleneck and the best bridge between the already-improved retrieval stack and future compiled artifacts.

---

## 11. Final recommendation

Proceed with this roadmap as the Karpathy-aligned update plan for SourceTrace Deep Research:
1. evidence packing,
2. compiled research artifact,
3. artifact lint,
4. follow-up branch proposals.

This sequence gives SourceTrace the best chance of evolving from a strong research runner into a stronger system for cumulative, inspectable knowledge work.
