# Deep Research artifact lint / health implementation slice brief v1

Status: proposed implementation slice
Date: 2026-06-21
Scope: bounded first lint / health layer for compiled research artifacts.

## 1. Slice verdict

This is the right next slice after `compiled research artifact v1`.

Reason:
- compiled artifacts now exist as a durable layer,
- evaluator snapshots are already embedded into them,
- so the next useful move is not richer generation yet,
- it is checking whether the artifact is structurally healthy, complete enough, and trustworthy enough to be reused.

This should stay diagnostic-first.
No auto-rewrite, no hidden self-repair loop, no artifact mutation engine yet.

---

## 2. Problem statement

`compiled research artifact v1` gives SourceTrace a first reusable knowledge object.
But right now the system has no explicit judgment layer about whether a compiled artifact is:
- structurally complete,
- evidence-backed enough,
- operationally useful,
- or brittle / under-supported.

Without that layer, artifacts can accumulate but remain uneven in quality.
That would recreate the same problem at a new layer: persistence without health discipline.

---

## 3. Objective

Add a first lint / health artifact that evaluates one compiled research artifact and reports:
- completeness,
- evidence sufficiency,
- follow-up readiness,
- quality risks,
- and a small set of recommended repairs/checks.

Desired outcome:
- each compiled artifact can be assessed without mutating it,
- weak artifacts become visibly weak,
- later slices can decide whether to branch, revise, or escalate.

---

## 4. Non-goals

Do not do these in this slice:
- no automatic artifact rewriting,
- no background repair workflow,
- no multi-artifact merge or dedup,
- no stale-time or freshness policy engine,
- no advanced UI console for lint triage,
- no scoring ML system.

This is a small, explicit health-check layer.

---

## 5. Proposed shape

Add a new artifact such as:
- `CompiledResearchArtifactLint`

Suggested fields:
- `lint_id`
- `artifact_id`
- `owner_id`
- `status`
- `completeness_verdict`
- `evidence_verdict`
- `followup_verdict`
- `risk_flags`
- `missing_sections`
- `recommended_repairs`
- `recommended_next_action`
- `created_at`

Optional overall status bands:
- `healthy`
- `needs_review`
- `weak`

Keep it simple and deterministic.

---

## 6. Minimum lint checks

### A. Structural completeness
Check presence / non-triviality of:
- `title`
- `summary`
- `current_answer`
- at least one of `key_claims` or `supporting_evidence`
- `evaluation_snapshot`

### B. Evidence health
Check for signals such as:
- empty `supporting_evidence`
- empty `source_refs`
- `evaluation_snapshot.source_quality_verdict != strong`
- `evaluation_snapshot.truthfulness_verdict == weak`
- `evaluation_snapshot.should_revise_report == true`

### C. Follow-up readiness
Check whether the artifact has:
- `open_questions`
- `next_checks`
- evaluator `recommended_next_check`

If there are open questions but no next checks, that should be flagged.

### D. Risk flags
Possible v1 flags:
- `missing_summary`
- `missing_current_answer`
- `missing_evidence`
- `missing_sources`
- `missing_evaluation_snapshot`
- `weak_truthfulness`
- `weak_source_quality`
- `needs_revision`
- `open_questions_without_next_checks`

---

## 7. Recommended evaluation posture

This lint should be deterministic and cheap.
Do not use another LLM pass yet.

Reason:
- the checks are mostly structural + rule-based,
- deterministic checks are better for trust and repeatability,
- later slices can add more interpretive review if necessary.

---

## 8. Persistence model

Persist lint artifacts separately from compiled artifacts.

Suggested namespace:
- `data/research/compiled-lint/`

Reason:
- compiled artifact = knowledge object
- lint artifact = diagnostic view over that object

Do not mutate compiled artifact files just to attach health output.

---

## 9. Transformation path

Add a function such as:
- `_lint_compiled_research_artifact(artifact: CompiledResearchArtifact) -> CompiledResearchArtifactLint`

Recommended v1 behavior:
- run lint automatically when a compiled artifact is created,
- persist lint output alongside it.

This keeps the path simple and keeps health visibility close to creation time.

---

## 10. Retrieval / API path

Minimal v1 retrieval:
- `GET /api/research/compiled-lint/{lint_id}`
- optionally `GET /api/research/compiled-lint?owner_id=...`
- optionally `GET /api/research/compiled/{artifact_id}/lint`

### Recommendation
For v1, prefer artifact-scoped read:
- `GET /api/research/compiled/{artifact_id}/lint`

That keeps the operator mental model tight.

---

## 11. Suggested verdict logic

### `completeness_verdict`
- `strong`: key fields present and non-trivial
- `mixed`: one important field missing / thin
- `weak`: multiple important fields missing

### `evidence_verdict`
- `strong`: evidence/source presence + evaluator snapshot not weak
- `mixed`: evidence thin or evaluator mixed
- `weak`: evidence absent or evaluator says truth/source quality is weak

### `followup_verdict`
- `strong`: open loops and next checks are coherent
- `mixed`: one exists without the other
- `weak`: neither useful open questions nor next checks exist

### overall `status`
- `healthy`: no major flags, no weak verdicts
- `needs_review`: mixed signals or repairable gaps
- `weak`: serious evidence/truthfulness/completeness problem

---

## 12. Domain additions

Likely minimal objects:
- `CompiledResearchArtifactLintStatus`
- `CompiledResearchArtifactLint`

Maybe reuse `ResearchEvaluationVerdict` for banding instead of inventing too many enums.

Keep the type surface small.

---

## 13. Tests to add

### A. Healthy artifact test
Artifact with:
- answer,
- summary,
- evidence,
- evaluation snapshot strong,
- next checks present

Expected:
- `status = healthy`
- low/no risk flags

### B. Thin artifact test
Artifact with:
- summary but no supporting evidence,
- no source refs,
- mixed evaluator snapshot

Expected:
- `status = needs_review` or `weak`
- `missing_evidence`, `missing_sources`

### C. Follow-up gap test
Artifact with open questions but no next checks.
Expected flag:
- `open_questions_without_next_checks`

### D. Persistence / API tests
- lint persisted separately,
- lint retrievable by artifact-scoped endpoint.

---

## 14. Verification steps

After implementation:
1. run focused tests,
2. run full repo gate,
3. execute one real research run,
4. confirm compiled artifact exists,
5. confirm lint exists,
6. inspect whether the lint status feels truthful for that artifact.

---

## 15. Success criteria

Minimum success:
- each compiled artifact can produce a persisted lint/health output,
- lint is deterministic and readable,
- important missing structure or weak evidence is surfaced explicitly,
- full gate remains green.

Preferred success:
- the lint output is good enough to drive future branch/revise logic,
- operator can quickly see whether an artifact is worth trusting or extending.

---\n
## 16. Rollback

If lint proves too noisy:
- keep compiled artifact generation intact,
- disable automatic lint generation,
- preserve manual/internal lint function for refinement,
- revise flags/rules against real artifact examples.

This slice should be low-risk because it is additive and diagnostic.

---

## 17. Recommended execution order

1. define lint datamodel,
2. add lint persistence,
3. implement deterministic lint function,
4. auto-run lint on compiled artifact creation,
5. add minimal retrieval path,
6. add tests,
7. run full gate,
8. inspect one real artifact + lint pair.

---

## 18. Final recommendation

Proceed with `artifact lint / health v1` next.

Reason:
- compiled artifacts now exist,
- they need health discipline before richer workflow branching,
- and this slice stays aligned with the overall posture: structured, benchmarkable, diagnostic-first progress rather than magic behavior.
