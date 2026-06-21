# Deep Research procedural_admin unified-search integration v1 follow-up — 2026-06-21

Status: implemented
Date: 2026-06-21
Scope: query-class-specific Unified Search integration for `procedural_admin` with safe fallback to the current search path.

## What shipped

Promoted the Unified Search spike into a bounded v1 integration pattern.

### Added behavior
- `procedural_admin` queries try a Unified Search-backed path first,
- non-procedural queries continue using the current search path,
- if Unified Search returns no useful official-doc-capable signal in the top slice, the adapter falls back to the current search path.

### Current fallback rule
Fallback triggers when Unified Search top results do not contain an official-doc-like hit in the top 5.

This is intentionally conservative.

## Verification

### Focused tests
Added coverage for:
- preferring Unified Search hits when official docs are present,
- falling back to the current search path when Unified Search returns only weak/community-style hits.

Focused procedural tests passed.

### Controlled procedural rerun
Observed outcome for the SCCM procedural query:
- top URLs:
  1. `learn.microsoft.com/.../create-configuration-baselines`
  2. `learn.microsoft.com/.../deploy-configuration-baselines`
  3. `anoopcnair.com/...`
- `source_quality = mixed`
- `relevance = strong`
- `truthfulness = strong`
- `should_revise_report = false`
- `recommended_next_check = Tighten source authority and rerun the same query for comparison.`

### Full repo gate
- `411 passed`

## Verdict

This is a good v1 shape.

It improves upstream recall for the procedural/admin class while preserving a safe escape hatch when Unified Search underperforms.

## Recommendation

Keep this integration bounded:
- query-class-specific,
- fallback-backed,
- benchmarked mainly on the procedural row.

Do not generalize it yet to the rest of the search stack.
