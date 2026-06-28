# SourceTrace v2 retrieval query refinement handoff v2 — 2026-06-28

## Goal

Shift the remaining retrieval shaping pressure away from deterministic scoring rules and back into the existing LLM-backed `query_refinement` seam, while preserving the bounded query-handoff contract.

This slice is intentionally narrow:
- no selector-policy change
- no trust-policy change
- no PDF/storage work
- no query-specific or country-specific hardcoded overrides

## Problem addressed

The earlier query-handoff repair correctly stopped retrieval from consuming freeform answer prose.
But after that repair, retrieval still effectively relied on:
- normalized seed passthrough, and
- deterministic target-quality/source-mix shaping inside retrieval

Given the updated posture, that was no longer the cleanest seam.
If query-level shaping is needed, it should come from a dynamic LLM-built retrieval query, not from more static heuristics in retrieval ordering.

## Change made

Updated:
- `src/sourcetrace_v2/app/services/execution.py`

What changed:
- `QUERY_REFINEMENT` now receives an explicit prompt asking for exactly one bounded retrieval query line
- retrieval consumes the validated output of that stage when it is query-like
- if the stage returns prose, placeholders, multi-line output, or otherwise invalid text, the flow falls back to the normalized seed query
- fallback is recorded as a degraded query-refinement receipt via `validation_fallback`

## Why this is coherent

This keeps the existing bounded handoff contract intact while making the seam actually dynamic:
- retrieval query generation is now allowed to adapt to query/context through the LLM
- invalid LLM output cannot silently poison search
- deterministic retrieval scoring no longer has to carry all of the intent-shaping burden alone

## Verification

Focused tests passed:
- `tests/unit/v2/test_query_handoff_contract.py`
- `tests/unit/v2/test_retrieval_target_quality.py`
- `tests/unit/v2/test_logging_execution_integration.py`

Result: `5 passed`

Broader check:
- `tests/unit/v2`

Result: `97 passed`

## Practical verdict

This is the right directional follow-up after the trust-jurisdiction rerank.
It does not solve retrieval quality by itself, but it moves query shaping into the correct seam:
- dynamic when useful
- bounded and validated when risky

## Remaining posture

What this does not yet prove:
- that live retrieval quality is now broadly stable
- that hard cases like remote-work Poland or legal-hold are solved

What it does prove:
- any additional retrieval-shaping intelligence can now come through the dedicated LLM query-refinement stage instead of requiring more deterministic retrieval heuristics by default

## Recommended next bounded slice

`retrieval-query-refinement-live-eval-v1`

Goal:
- run a small live pack against the updated query-refinement handoff
- check whether hard cases improve materially in candidate-pool quality
- decide from evidence whether the next move should be further query-refinement refinement, retrieval survival adjustment, or regression-pack expansion
