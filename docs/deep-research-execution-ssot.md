# Deep Research execution SSOT

Status: active SSOT
Date: 2026-06-24
Scope: canonical runtime-truth and execution-semantics reference for SourceTrace Deep Research.

## 1. Purpose

This file is the canonical execution SSOT for Deep Research runtime truth.
Use it to answer:
- whether Deep Research is actually available,
- what lifecycle state a job is in,
- how to interpret terminal outcomes,
- how to interpret result artifacts versus compiled artifacts versus lint,
- what operator-facing truth rules apply.

Do not use restart notes or slice follow-ups as the canonical answer when this file is sufficient.

## 2. Runtime posture truth

Deep Research has exactly three operator-facing runtime posture states.

### `disabled`
Meaning:
- no Deep Research execution runtime is wired into delivery.

Expected behavior:
- research routes may still exist as HTTP surface,
- start/run should not claim research is available,
- readiness/runtime/capabilities should report research as not available.

Canonical signals:
- `research_enabled = false`
- `research_ready = false`
- `research_status = "disabled"`

### `not_ready`
Meaning:
- a Deep Research runtime is wired into delivery,
- but the execution path is not actually ready, currently because search is not configured.

Expected behavior:
- reads may still work for already-persisted data,
- start/run should return unavailable rather than pretending to execute,
- UI should clearly block start/run.

Canonical signals:
- `research_enabled = true`
- `research_ready = false`
- `research_status = "not_ready"`

### `ready`
Meaning:
- a Deep Research runtime is wired,
- and the execution path is ready enough to accept start/run requests.

Canonical signals:
- `research_enabled = true`
- `research_ready = true`
- `research_status = "ready"`

## 3. Job lifecycle

The top-level job lifecycle is:

`queued -> probing -> running -> done | error | cancelled`

Interpretation:
- `queued`: accepted but not executing yet
- `probing`: runtime/configuration probing just after start
- `running`: active search/extract/analyze/write loop
- `done`: terminal state with a completed result artifact or a partial-salvage result artifact
- `error`: terminal state with no usable result artifact
- `cancelled`: terminal state caused by operator cancellation

Important rule:
- top-level job state alone is not enough to interpret quality or operator readiness.
- `done` only means the job finished its bounded flow.

## 4. Terminal outcome semantics

Terminal interpretation must use both job state and result state.

### Full success
Shape:
- `job.status = done`
- result exists
- `result.completion_mode = full`
- `termination_reason = null`

Meaning:
- the runtime completed its bounded path without partial-salvage semantics.
- this still does **not** mean the artifact is decision-ready.

### Partial salvage
Shape:
- `job.status = done`
- result exists
- `result.completion_mode in {partial_error, partial_timeout}`
- `termination_reason = partial_salvage`

Meaning:
- some useful result was preserved,
- but the execution path ended in a degraded way.

Interpretation rule:
- treat as usable-for-review, not normal success.

### Provider failure
Shape:
- `job.status = error`
- no result artifact
- `termination_reason = provider_failure`

Meaning:
- the run failed without salvage.

### Interrupted on recovery
Shape:
- `job.status = error`
- no result artifact
- `job.error = interrupted_on_recovery`
- `termination_reason = interrupted_on_recovery`

Meaning:
- the process found an in-flight job during recovery and marked it as terminal error.
- this is recovery-as-error, not true resume.

### Cancelled
Shape:
- `job.status = cancelled`
- usually no result artifact
- `termination_reason = cancelled`

Meaning:
- the operator explicitly stopped the job.

## 5. Artifact semantics

There are three different layers to interpret.

### Result artifact
This is the direct output of one Deep Research run.
It contains, among other things:
- final report text,
- raw findings,
- run stats,
- problem analysis,
- execution plan,
- evidence pack,
- evaluation,
- reflection.

Rule:
- a result artifact explains what one run produced.
- it is not yet the same thing as a durable, operator-triaged knowledge artifact.

### Compiled artifact
This is the higher-level durable artifact derived from a finished result.
It is the reusable structured form meant for later inspection and follow-up.

Rule:
- compiled artifact is the durable knowledge-oriented layer above a single run result.

### Compiled artifact lint
This is a separate health/quality diagnostic over the compiled artifact.

Rule:
- lint is the operator-facing health signal,
- not the same thing as run completion.

## 6. Operator truth rules

### Rule 1 — `done/full` does not mean decision-ready
A Deep Research run can complete fully and still have weak evidence.

### Rule 2 — weak lint beats success optics
If compiled artifact lint is `weak`, treat the outcome as needing revision even if the job is `done` and the result says `full`.

### Rule 3 — terminal is not the same as useful
`cancelled`, `provider_failure`, and `interrupted_on_recovery` are terminal outcomes, but they are not successful results.

### Rule 4 — partial salvage is degraded success
`partial_salvage` is better than hard failure, but worse than full success.
It should be interpreted as review material, not silent success.

### Rule 5 — runtime truth beats route presence
The existence of HTTP routes does not mean Deep Research is actually executable.
Operator interpretation must follow runtime posture (`disabled` / `not_ready` / `ready`), not mere route visibility.

## 7. Canonical payload expectations

The operator-facing HTTP surface should stay aligned on the following meanings:
- `/api/ready`: readiness truth
- `/api/runtime`: runtime composition + research posture truth
- `/api/capabilities`: advertised capability truth relative to runtime state
- `/api/research/status/{job_id}`: lifecycle truth + progress + inferred terminal reason
- `/api/research/result/{job_id}`: result truth or terminal-without-result truth
- `/research`: operator UI should visually respect runtime truth

If these diverge, treat it as a bug against this SSOT.

## 8. What this file does not decide

This SSOT does not define:
- broader/community retrieval quality thresholds,
- future background worker architecture,
- resume implementation,
- docs-repo reorganization,
- compiled artifact evolution beyond current operator truth semantics.

Those belong to later slices.

## 9. Current next recommended slice

The next bounded slice after this SSOT is:
- benchmark-driven quality pass for `general` / broader/community queries,
- using current runtime-truth semantics as fixed ground.

Reason:
- execution/control truth is now clearer,
- the next repeated uncertainty is not runtime posture but evidence quality in broad/general queries.
