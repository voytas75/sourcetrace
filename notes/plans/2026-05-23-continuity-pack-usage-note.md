# SourceTrace Continuity Pack Usage Note

Status: provisional guidance
Scope: when to create a continuity pack from an existing SourceTrace artifact
Last updated: 2026-05-23

## Purpose
This note defines the smallest useful rule for when a continuity pack should be created in SourceTrace work.

A continuity pack is a lightweight decision-ready wrapper over an existing artifact.
It is not the primary research note, not the primary observation note, and not a replacement for SSOT.

Its job is narrower:
- make the current decision explicit,
- separate `potwierdzone` from `przypuszczenia` and `do weryfikacji`,
- propose one smallest sensible next test.

## Minimal format
A continuity pack should contain exactly these sections:
- `Potwierdzone`
- `Przypuszczenia`
- `Do weryfikacji`
- `Recommended next test`

Optional but preferred:
- `Decision snapshot`

## When to create one
Create a continuity pack only when an existing artifact already contains enough evidence to support a real next-step decision, but the raw artifact is still awkward to route operationally.

Good candidates:
- a real-data observation note that already shows a blocker, partial improvement, or a likely next bounded fix,
- a research-ledger entry that already changes SourceTrace direction, architecture wording, or execution priority,
- a mixed research/runtime checkpoint where the next decision would otherwise require rereading a long note.

## When not to create one
Do **not** create a continuity pack:
- for every reviewed source by default,
- for raw notes that still lack enough evidence for a next-step decision,
- when the source artifact is already short, decision-ready, and not ambiguous,
- as a replacement for the canonical SSOT or the original observation/research artifact.

## Current working recommendation
Based on the first two experiments:
- continuity packs are useful across at least two artifact classes:
  - runtime observation notes,
  - research-ledger entries,
- the value is higher for runtime/test artifacts than for already-structured research-ledger entries,
- the healthy default is **selective use**, not blanket standardization.

## Recommended usage rule
Use a continuity pack when all three conditions are true:
1. there is an existing artifact worth preserving as the source of truth,
2. the next real decision is bigger than a one-line takeaway,
3. rewriting the whole source artifact into SSOT would be too heavy for the current step.

If any of those are false, prefer leaving the source artifact as-is.

## Examples in this repo
- Runtime observation example:
  - `docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md`
- Research-ledger example:
  - `docs/plans/2026-05-23-source-trace-research-continuity-pack-cerebroscope.md`

## Decision status
- Potwierdzone:
  - continuity packs can be generated from more than one SourceTrace artifact type,
  - they improve handoff clarity for decision checkpoints.
- Do weryfikacji:
  - whether this should ever become a canonical repo-wide document type.
- Current disposition:
  - use continuity packs selectively for high-leverage decision checkpoints.
