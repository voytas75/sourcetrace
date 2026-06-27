# SourceTrace v2 production-readiness track — 2026-06-28

## Purpose

Open a separate post-baseline track for moving `sourcetrace_v2` from bounded baseline to something closer to production-ready runtime posture.

This track is intentionally separate from the bounded closure line.
It exists because the baseline is already closed enough, while production readiness still has clear gaps.

## Why this track exists

Current bounded v2 baseline is coherent, but it is not production-ready.
The sharpest missing pieces are:
- live LLM runtime path,
- PDF/document read seam,
- operator-friendly live entrypoint.

## First bounded slice

### `live-llm-runtime-path-v1`

Goal:
- replace the current LLM seam with one real env-backed runtime path,
- support Azure/OpenAI-compatible live completion calls,
- keep scope bounded to LLM runtime wiring only.

Done when:
- there is one explicit live LLM runtime builder,
- it no longer requires manual `completion_fn` injection for normal use,
- it can be paired with the existing real search path for a bounded live smoke run,
- focused tests pass,
- docs checkpoint is recorded.

## Out of scope for this slice

- PDF/document read seam
- production deployment packaging
- UI/runtime polish
- evidence-policy changes
- broader provider fan-out

## Working rule

Do not blur this production-readiness track with the bounded closure line.
Every new slice here must be named, scoped, and justified by a real readiness gap.
