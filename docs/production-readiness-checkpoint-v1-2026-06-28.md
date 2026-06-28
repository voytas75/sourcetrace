# SourceTrace v2 production readiness checkpoint v1 — 2026-06-28

## Goal

Checkpoint current production readiness honestly after the recent retrieval, regression, trust-contract, and storage-posture work.

This is a review checkpoint, not a declaration of broad production readiness.

## External bounded review input

A bounded Codex CLI repo review was used as a secondary check on current posture.
Its most useful finding was sharp and concrete:
- the focused v2 slices are in materially better shape,
- but the broader `tests/unit/v2` suite is still not clean on current HEAD because `tests/unit/v2/test_logging_execution_integration.py` now fails after `execute_minimal_research_flow(...)` gained a required `search` dependency and those tests were not updated.

That is a real readiness signal, not noise.

## Readiness verdict

## **Conditionally ready for bounded/operator use**

## **Not ready yet for broad trust-sensitive production deployment**

## Why this is the verdict

### Green

#### 1. Retrieval line is materially stronger than before
Recent work improved:
- retrieval query handoff
- institutional source survival
- source typing visibility
- candidate target quality within the bounded retrieval pool
- regression coverage for both healthy and weak/ambiguous retrieval shapes

Interpretation:
- retrieval is no longer broadly broken
- some representative cases now look healthy enough for bounded operator use

#### 2. Persistence/readback honesty is good enough for current bounded scope
Recent work improved:
- artifact/marker semantics for `FOUND`
- partial/incomplete/absent readback truthfulness
- JSONL trailing-tail corruption tolerance
- explicit durability-posture decision

Interpretation:
- current storage is still limited, but it is honest enough for bounded local/operator use

#### 3. Operator surface is clearer
Recent work improved:
- repo-owned run/readback entrypoints
- trust block (`usable / weak / needs_review / degraded`)

Interpretation:
- the operator now gets a more honest top-line status than before

### Yellow

#### 1. Retrieval quality is still mixed, not stable everywhere
Representative healthy or mostly healthy cases exist, but so do still-weak ones:
- healthy/mostly healthy: breach notification, records retention, incident response, break-glass
- still weak/unstable: remote-work Poland, legal-hold fallback, cross-border data transfer drift

Interpretation:
- retrieval is better, but not yet broadly stable enough to call the line production-closed

#### 2. Trust contract is useful but still shallow
Current trust projection improves honesty, but it is not yet tightly aligned with real retrieval/evidence quality.
Some weak retrieval shapes can still look more usable than they should.

Interpretation:
- good enough for operator caution
- not yet a strong trustworthiness contract for broader autonomous or trust-sensitive use

### Red

#### 1. The broader v2 suite is not clean on current HEAD
Bounded Codex review surfaced a concrete failure in `tests/unit/v2`:
- `tests/unit/v2/test_logging_execution_integration.py`
- failure mode: `execute_minimal_research_flow(...)` now requires `search`, but the logging integration tests still call it without that dependency

Interpretation:
- this is integration drift inside the v2 line
- until fixed, it weakens any claim of production readiness

#### 2. Broad trust-sensitive deployment is still blocked by unstable retrieval cases plus shallow trust semantics
Even with recent improvements, the current system can still produce weak answer shapes in important official-intent cases.

Interpretation:
- bounded/operator use: plausible
- broad trust-sensitive deployment: not yet honest to claim

## Practical production posture right now

### Reasonable to say
- good enough for bounded operator-facing use
- worth exercising in a limited production-like loop with human oversight
- significantly stronger than it was before this sequence of slices

### Not reasonable to say yet
- fully production-ready for broad trust-sensitive deployment
- retrieval line is stable enough across representative official-intent cases
- v2 integration line is clean enough to stop checking for test drift

## Single best next bounded slice

`v2-integration-drift-fix-v1`

## Why this is next

Before any stronger production-readiness claim, the repo should at least have the broader v2 test surface back in sync.
That is a sharper and more honest next move than more retrieval polishing right now.

Target:
- repair the `test_logging_execution_integration.py` drift caused by the required `search` dependency
- rerun the broader `tests/unit/v2` suite
- then reassess whether the next highest-value slice returns to retrieval stabilization or trust-quality alignment
