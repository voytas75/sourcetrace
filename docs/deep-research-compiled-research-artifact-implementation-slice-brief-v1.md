# Deep Research compiled research artifact implementation slice brief v1

Status: proposed implementation slice
Date: 2026-06-21
Scope: bounded implementation brief for introducing a first compiled research artifact in SourceTrace Deep Research.

## 1. Slice verdict

This is the next strategic slice after evidence packing.

Reason:
- retrieval is materially improved,
- authority-first filtering is in place,
- evidence packing now makes synthesis cleaner,
- so preserving results as structured, reusable artifacts is now much less likely to fossilize noise.

The aim is not to build a full long-lived knowledge system yet.
The aim is to introduce a **first durable artifact form** that sits above a single run result.

---

## 2. Problem statement

Current Deep Research outputs are still too run-centric.

Even with the improved pipeline, a completed run is mainly stored as:
- report markdown,
- raw findings,
- stats,
- evaluation.

That is good for execution and benchmarking, but weak for cumulative knowledge work.

Karpathy-aligned gap:
- useful research should not end life as just an ephemeral report payload,
- it should become a structured artifact that can be reviewed, extended, and later linted.

---

## 3. Objective

Add a first compiled research artifact form that can be produced from a completed Deep Research run.

The artifact should capture:
- what the topic/run was about,
- what the current answer is,
- what claims are being made,
- what evidence supports those claims,
- what remains open or uncertain,
- what next checks are worth doing.

Desired outcome:
- one run can produce one reusable artifact,
- artifacts are structurally richer than raw run results,
- later slices can lint or extend these artifacts.

---

## 4. Non-goals

Do not do these in this slice:
- no full topic dossier merging across many runs,
- no long-lived memory/wiki system,
- no artifact lint engine yet,
- no automatic artifact-to-artifact merging,
- no large UI redesign,
- no generalized multi-tenant artifact policy engine.

This is a narrow **compiled artifact v1** slice.

---

## 5. Proposed artifact shape

Suggested v1 shape:

- `artifact_id`
- `source_job_id`
- `owner_id`
- `query`
- `query_class`
- `title`
- `summary`
- `current_answer`
- `key_claims`
- `supporting_evidence`
- `open_questions`
- `next_checks`
- `source_refs`
- `evaluation_snapshot`
- `created_at`

### Notes

#### `title`
A readable artifact title, derived from the query or current answer.

#### `summary`
Short operator-facing summary of what the artifact currently concludes.

#### `current_answer`
The main answer body from the result, cleaner than raw markdown if practical.

#### `key_claims`
Small list of extracted claims, each optionally tied to evidence refs.

#### `supporting_evidence`
Compact structured list derived from packed evidence / raw findings.

#### `open_questions`
Structured unresolved questions, not only prose uncertainty.

#### `next_checks`
Operational next validation or follow-up checks.

#### `source_refs`
Compact source list with url/title pairs or short refs.

#### `evaluation_snapshot`
A copy or projection of the run’s evaluation artifact so later artifact review does not need to chase the original run for basic quality context.

---

## 6. Proposed transformation path

Add a transformation step such as:
- `_compile_research_artifact(result: ResearchResultArtifact) -> CompiledResearchArtifact`

This should happen only for completed runs with usable result content.

### Recommended posture
Make artifact compilation explicit in runtime/result finalization rather than fully hidden magic.

Two acceptable v1 options:
1. compile automatically on successful run completion,
2. compile via a narrow explicit step after result creation.

### Recommendation
For v1, compile automatically for successful full results.
That keeps the slice small and observable.

---

## 7. Persistence model

Persist compiled artifacts separately from run results.

Reason:
- run result = ephemeral execution artifact,
- compiled artifact = reusable knowledge artifact.

Suggested storage shape:
- new compiled artifact persistence interface,
- filesystem-backed store similar to existing result persistence,
- separate path namespace such as:
  - `data/research/compiled/`

This keeps conceptual boundaries clean.

---

## 8. Retrieval / view path

Add a minimal retrieval path for compiled artifacts.

v1 can be narrow:
- get artifact by `artifact_id`
- optionally list artifacts for `owner_id`

No need for advanced search yet.

If API exposure is cheap in the same slice, add:
- `GET /api/research/compiled/{artifact_id}`
- optionally `GET /api/research/compiled?owner_id=...`

If not, filesystem persistence plus internal retrieval is enough for the first pass.

---

## 9. How to derive artifact fields

## A. Summary / current answer
Source from the existing result report sections:
- `## Current answer`
- optionally summary line / answer summary

## B. Key claims
Initial heuristic extraction is acceptable.
Use the top answer-driving evidence and result sections to derive a small set of claims.
Keep it bounded: e.g. 3–5 claims max.

## C. Supporting evidence
Prefer packed `core` + `supporting` evidence over a flat raw finding dump.
This is one of the main reasons to do this slice after evidence packing.

## D. Open questions
Derive from:
- `## Uncertainty`
- evaluator `missing_checks`
- evaluator risks when useful

## E. Next checks
Derive from:
- `## Next checks`
- evaluator `recommended_next_check`

---

## 10. Suggested domain additions

Potential new domain objects:
- `CompiledResearchArtifact`
- `CompiledResearchClaim`
- `CompiledResearchEvidenceRef`

Keep them small.
Do not over-model yet.

A lightweight dataclass-based structure is enough for v1.

---

## 11. Tests to add

## A. Domain / serialization tests
- compiled artifact can be created from a result,
- artifact serializes/deserializes correctly,
- artifact persistence is separate from run result persistence.

## B. Transformation tests
1. procedural run result with strong official evidence:
- artifact title is sensible,
- claims are populated,
- supporting evidence comes from core/supporting path,
- next checks/open questions are present.

2. broad concept result:
- artifact still compiles even if evidence is more mixed.

## C. API/retrieval tests (if API added)
- fetch compiled artifact by id,
- list artifacts for owner.

---

## 12. Verification steps

After implementation:
1. run focused tests,
2. run full repo gate,
3. execute at least one Deep Research run,
4. confirm compiled artifact is persisted,
5. inspect artifact readability,
6. confirm retrieval/view path works if included.

---

## 13. Success criteria

Minimum success:
- completed research runs can produce a compiled artifact,
- the artifact is structurally richer than the raw result,
- supporting evidence is derived from the cleaned evidence path,
- artifact persistence is separate from run result persistence,
- full test gate remains green.

Preferred success:
- artifact is clearly readable and useful to an operator,
- evaluator snapshot makes the artifact self-describing enough for later lint work,
- the system now has a believable first bridge from ephemeral research to reusable knowledge.

---

## 14. Rollback

If the artifact shape proves too noisy or not useful:
- stop automatic compilation,
- keep result artifacts intact,
- preserve evidence packing and evaluator improvements,
- revisit artifact schema with real examples.

Rollback is low-risk if compilation is introduced as an additive layer.

---

## 15. Recommended execution order

1. define compiled artifact dataclasses,
2. add persistence layer,
3. add result-to-artifact transform,
4. wire auto-compilation on successful completion,
5. add retrieval path,
6. add focused tests,
7. run full gate,
8. run one real Deep Research case and inspect artifact.

---

## 16. Final recommendation

Proceed with this slice as the next implementation step when the Deep Research roadmap continues.

Reason:
- evidence flow is now clean enough,
- compiled artifacts are the right next bridge from run-centric behavior to cumulative knowledge work,
- and later artifact lint/follow-up logic depends on this layer existing first.
