# Deep Research architecture upgrade plan v1

Status: proposed implementation plan
Date: 2026-06-24
Scope: bounded architecture-upgrade plan for SourceTrace Deep Research, based on a broader Research Agent spec but translated into SourceTrace-safe implementation slices.

## 1. Executive verdict

The supplied Research Agent spec is a good architectural direction, but it should **not** be implemented inside SourceTrace as one large rewrite or one giant workflow epic.

The correct posture for SourceTrace is:
- preserve the current bounded Deep Research runtime,
- formalize the pieces that already exist implicitly,
- add missing decision artifacts where they materially improve execution quality,
- keep branching bounded,
- separate evaluation, reflection, and criticism instead of collapsing them into one layer,
- and delay heavier memory / graph / recursive-orchestration ideas until run quality and artifact structure are stronger.

This plan therefore translates the broad spec into a staged SourceTrace roadmap.

---

## 2. Current SourceTrace baseline

SourceTrace Deep Research already has meaningful infrastructure and should not be treated as greenfield.

Already present in bounded form:
- async research job lifecycle,
- persisted job/result/progress model,
- bounded planner/query-generation loop,
- web search through SearxNG,
- procedural/admin retrieval specialization,
- extraction,
- synthesis,
- post-result evaluator v1,
- operator UI at `/research`,
- runtime diagnostics and persisted artifacts.

This matters because the next architecture step should be **structural strengthening**, not workflow replacement.

### Source references
- `docs/deep-research-implementation-slice-v1.md`
- `docs/deep-research-post-result-evaluator-design-v1.md`
- `docs/karpathy-gap-analysis-to-sourcetrace-deep-research-update-plan-v1.md`
- `docs/restart-brief-2026-06-23-deep-research-ui-and-runtime.md`

---

## 3. Spec-to-SourceTrace mapping

| Broad spec component | SourceTrace status | Recommended posture |
| --- | --- | --- |
| Problem Analyzer | partial / implicit | formalize next |
| Planner | present but light | strengthen with explicit plan artifact |
| Thought Generator | mostly absent as explicit artifact | introduce bounded branch proposal, not full ToT |
| Research Branches | implicit bounded loop exists | evolve into branch-aware execution selectively |
| Evaluator | present as post-result evaluator v1 | keep and later split responsibilities |
| Synthesizer | present | keep, but feed it better structured evidence |
| Reflection | absent as explicit layer | add after branching/evidence structure improves |
| Critic | absent as explicit layer | add later as bounded final-review pass |
| Final Report | present | keep |
| Memory Layer | partial (run artifacts exist) | delay full memory; add compiled artifacts first |

---

## 4. Design principles for the upgrade

### 4.1 Preserve boundedness
The current runtime should remain bounded and testable.
Do not introduce open-ended recursion, unbounded branch growth, or hidden retry loops.

### 4.2 Prefer explicit artifacts over hidden heuristics
If a new reasoning stage matters, it should emit a structured artifact, not just alter prompt text.

### 4.3 Separate responsibilities
Do not overload one component to do planning, evaluation, self-critique, and memory promotion simultaneously.

### 4.4 Branch selectively
Branching should be used only where it changes quality meaningfully.
Not every query needs multi-branch analysis.

### 4.5 Delay strategic memory until artifacts are worth preserving
Run results are not yet equivalent to durable topic knowledge.
Compiled artifacts should come before long-term strategy memory.

---

## 5. Recommended target architecture for SourceTrace

Recommended near-to-mid-term flow:

`query -> problem analysis -> research plan -> bounded branch proposal -> branch execution -> evidence packing -> synthesis -> result evaluation -> reflection -> optional bounded retry/revision -> critic -> final report -> compiled artifact -> artifact lint -> follow-up branch proposals`

This differs from the broader spec in important ways:
- it keeps the current runtime backbone,
- it inserts explicit artifacts at decision points,
- it keeps reflection and critic separate,
- it treats compiled artifacts as a later persistence layer rather than pretending session memory is already a robust long-term research memory.

---

## 6. Components to add or formalize

## 6.1 Problem Analyzer v1

### Purpose
Convert user query input into a structured problem description that downstream stages can share.

### Proposed output contract
```json
{
  "intent": ["Research"],
  "domains": ["Security", "PKI"],
  "entities": ["AD CS"],
  "goal": "Assess security posture",
  "constraints": [],
  "missing_information": [],
  "complexity": "HIGH",
  "subproblems": [
    "Analyze CA configuration",
    "Analyze template permissions",
    "Analyze escalation paths"
  ]
}
```

### Why this is worth adding
Today, pieces of this exist indirectly through query-class heuristics and evaluator posture. A formal artifact would make:
- planning more explicit,
- branch proposal less ad hoc,
- evaluator criteria more grounded,
- reflection later easier to implement.

### Scope rule
Only include fields that downstream code will actually consume in v1.
Avoid speculative schema bloat.

---

## 6.2 Research Plan v2

### Purpose
Represent the chosen execution strategy and ordered plan steps explicitly.

### Proposed output contract
```json
{
  "strategy": "deep_research",
  "steps": [
    {
      "id": "step1",
      "objective": "Collect baseline evidence",
      "depends_on": []
    },
    {
      "id": "step2",
      "objective": "Inspect contradictions or weak evidence",
      "depends_on": ["step1"]
    },
    {
      "id": "step3",
      "objective": "Synthesize final answer",
      "depends_on": ["step1", "step2"]
    }
  ]
}
```

### Strategy values
Initial bounded strategy set:
- `simple_answer`
- `research`
- `deep_research`
- `branch_investigation`

### Why this is worth adding
The current planner/runtime seam exists, but a formal plan artifact would:
- improve progress visibility,
- support later reflection against intended coverage,
- support selective branching without inventing an entire workflow engine.

---

## 6.3 Bounded Branch Proposal Engine

### Purpose
Introduce structured alternative analytical paths without committing SourceTrace to a full Tree of Thoughts runtime.

### Recommendation
Use **branch proposal**, not unconstrained thought-tree expansion.

### Rules
- max 3 branches,
- branch only when complexity is `HIGH` or `VERY_HIGH`, or when the query class is broad/comparative/decision-oriented,
- no recursive branch spawning in v1,
- no branch fanout for routine procedural/admin queries.

### Example branch types
- pro / contra / unresolved,
- technical / operational / risk,
- baseline state / failure modes / mitigation path,
- official evidence path / independent evidence path only when justified.

### Proposed output contract
```json
{
  "branches": [
    {
      "branch_id": "A",
      "objective": "Evidence supporting the main claim"
    },
    {
      "branch_id": "B",
      "objective": "Contradictory or limiting evidence"
    },
    {
      "branch_id": "C",
      "objective": "Unresolved evidence gaps"
    }
  ]
}
```

### Why not full ToT now
A full Tree of Thoughts runtime would increase:
- cost,
- state complexity,
- test burden,
- persistence complexity,
- UI complexity.

The product does not need that yet.

---

## 6.4 Branch Evaluator

### Purpose
Score branch outputs before synthesis.

### Recommendation
Add a dedicated branch-evaluation stage rather than overloading the existing result evaluator.

### Proposed scoring dimensions
- evidence score,
- consistency score,
- completeness score,
- confidence score.

### Proposed output contract
```json
{
  "branch_scores": [
    {
      "branch_id": "A",
      "evidence_score": 0.9,
      "consistency_score": 0.8,
      "completeness_score": 0.7,
      "confidence_score": 0.85,
      "combined_score": 0.84
    }
  ],
  "selected_branch_ids": ["A", "C"]
}
```

### Selection rule
Retain approximately top 20-40%, but bounded by branch count and practical utility.
In v1, with max 3 branches, that usually means keeping 1-2 branches.

---

## 6.5 Reflection Engine v1

### Purpose
Perform structured self-check after synthesis/result evaluation.

### Important posture
Reflection is not a free second research engine.
It is a bounded diagnostic pass.

### Proposed output contract
```json
{
  "missing_topics": [],
  "contradictions": [],
  "weak_evidence_areas": [],
  "goal_coverage": "full",
  "should_research_again": false,
  "recommended_followup": null
}
```

### Runtime rule
At most one targeted retry cycle in v1.
No open-ended recursive loop.

### Why add it
This layer is the correct place to answer:
- did we miss a meaningful subproblem,
- are there contradictions worth one more pass,
- did the result achieve the original goal stated in `ProblemAnalysis`.

---

## 6.6 Critic

### Purpose
Provide a bounded final-review layer that does not depend on internal chain-of-thought history.

### Inputs
The critic should see only:
- user query,
- final draft,
- compact evidence references,
- possibly small structured metadata.

### Checks
- fact support,
- logic coherence,
- internal consistency,
- completeness relative to the user’s question.

### Important rule
Critic should remain independent from the earlier reflective/planning path.
It is a report reviewer, not another planner.

---

## 6.7 Compiled Research Artifact v1

### Purpose
Promote selected research results from run artifacts into reusable topic artifacts.

### Why not earlier
Compiled artifacts become much more valuable once:
- evidence packing is cleaner,
- planning is explicit,
- and reflection can identify what remains unresolved.

### Proposed artifact shape
```json
{
  "topic": "...",
  "summary": "...",
  "claims": [...],
  "evidence": [...],
  "open_questions": [...],
  "next_checks": [...],
  "source_refs": [...]
}
```

### Boundary
This is distinct from raw run results.
Run results are execution artifacts.
Compiled artifacts are reusable knowledge artifacts.

---

## 6.8 Artifact Lint

### Purpose
Inspect the health of compiled artifacts rather than only the quality of a single run output.

### Suggested checks
- provenance gaps,
- contradictions,
- stale/unsupported claims,
- unresolved evidence gaps,
- suggested repair actions.

### Important rule
Do not overload the current result evaluator with artifact-lint responsibilities.
Keep them separate.

---

## 7. What should explicitly wait

## 7.1 Full Tree of Thoughts runtime
Do not implement now.
Branch-aware execution is enough for the next stage.

## 7.2 Knowledge graph search
Treat as a future seam only.
Do not add it unless SourceTrace first gains a real graph-backed knowledge representation worth querying.

## 7.3 Full long-term strategy memory
Do not implement as a major subsystem until compiled artifacts and artifact lint exist.
Otherwise the system risks preserving noisy run outputs as if they were reliable research memory.

---

## 8. Recommended implementation order

## Slice 1 — Problem Analyzer v1

### Goal
Formalize query understanding into a shared artifact.

### Files likely affected
- `src/sourcetrace/application/research_runtime.py`
- domain/research schema area
- result/status payload shaping
- tests for query classes / analysis payload

### Definition of done
- each job stores `problem_analysis`,
- planner and evaluator can consume it,
- debug/status paths expose it.

---

## Slice 2 — Planner v2 formalization

### Goal
Add explicit plan structure and execution strategy.

### Definition of done
- each job stores a formal plan,
- plan steps appear in progress/debug data,
- query generation uses the plan artifact rather than only local heuristics.

---

## Slice 3 — Evidence packing hardening

### Goal
Strengthen synthesis context discipline before branching grows.

### Why here
This stays consistent with the already-documented SourceTrace roadmap: cleaner evidence handling should precede broader persistence or memory work.

### Definition of done
- evidence is separated into role-aware packs,
- synthesis consumes structured packs, not flat context blobs,
- output quality improves without wider workflow complexity.

---

## Slice 4 — Bounded branch proposal/execution

### Goal
Add selective multi-path investigation only where it materially helps.

### Definition of done
- eligible query classes can generate 1-3 branch candidates,
- branches execute independently in bounded fashion,
- branch summaries are visible in debug output,
- synthesis uses selected branch outputs.

---

## Slice 5 — Branch evaluator

### Goal
Rank branch outputs before synthesis.

### Definition of done
- branches are scored on explicit dimensions,
- top branches are selected deterministically,
- test coverage exists for at least one positive branch-selection case.

---

## Slice 6 — Reflection v1

### Goal
Add bounded self-check and at most one targeted retry.

### Definition of done
- reflection emits structured missing-topic / contradiction output,
- runtime can perform at most one targeted re-search cycle,
- no hidden recursion exists.

---

## Slice 7 — Compiled artifact v1

### Goal
Promote completed runs into reusable topic artifacts.

### Definition of done
- a completed run can be transformed into a separate compiled artifact,
- artifact structure is stable and testable,
- artifact storage is distinct from raw run-result storage.

---

## Slice 8 — Artifact lint

### Goal
Evaluate artifact health rather than only per-run quality.

### Definition of done
- compiled artifacts can be linted,
- lint output is structured and operator-readable,
- lint identifies provenance gaps and contradictions.

---

## Slice 9 — Critic + optional bounded final revision

### Goal
Add independent final report review.

### Definition of done
- critic emits issue list and recommendations,
- optional final revision remains bounded and explicit,
- no hidden rewrite loop is introduced.

---

## 9. Recommended module placement

This plan should preserve current SourceTrace layering rather than introduce a totally new orchestration stack prematurely.

Suggested placement:
- problem analysis contracts near current research domain/application contracts,
- planner and branch proposal inside `application/research_runtime.py` first, then split only if complexity proves it necessary,
- branch evaluator as a sibling to the current evaluator logic,
- reflection and critic as separate bounded application services,
- compiled artifacts and artifact lint near research persistence rather than mixed into raw result payloads.

Do not introduce framework-driven architecture changes before the product logic proves them necessary.

---

## 10. Risks and controls

### Risk 1 — overbuilding around architecture language
The spec uses strong architecture language that could trigger a rewrite impulse.

**Control:** preserve the current bounded runtime and evolve it in slices.

### Risk 2 — branch explosion
Adding alternative paths can multiply cost and state.

**Control:** hard cap branch count, no recursive branching in v1.

### Risk 3 — evaluator overload
It is easy to make evaluator responsible for everything.

**Control:** keep branch evaluation, result evaluation, reflection, critic, and artifact lint as separate concerns.

### Risk 4 — preserving noise as memory
If compiled artifacts come too early or without evidence discipline, the system will fossilize weak outputs.

**Control:** keep evidence-packing hardening before compiled-knowledge ambitions.

### Risk 5 — UI/persistence drift
New artifacts can outpace operator visibility and test coverage.

**Control:** expose each new artifact first in debug/status surfaces and add regression coverage before polishing UI.

---

## 11. Final recommendation

Proceed with the broader Research Agent vision only in this translated SourceTrace form:
1. formalize problem analysis,
2. formalize planning,
3. improve evidence packing,
4. add bounded branch proposal/execution,
5. add branch evaluation,
6. add reflection,
7. add compiled artifacts,
8. add artifact lint,
9. add critic.

This sequence gives SourceTrace the best chance of evolving into a stronger research system without losing the bounded, inspectable, operator-friendly qualities that already exist.
