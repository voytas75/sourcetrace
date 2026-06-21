# Deep Research procedural_admin unified-search integration spike follow-up — 2026-06-21

Status: completed spike
Date: 2026-06-21
Scope: bounded experiment to test Unified Search as an upstream acquisition path for `procedural_admin` queries.

## What shipped

Implemented a narrow experimental adapter:
- `build_procedural_admin_unified_search_adapter(...)`

Behavior:
- for `procedural_admin` queries, prefer a Unified Search-backed hit set,
- for non-procedural queries, fall back to the current search path,
- if Unified Search returns nothing, fall back to the current search path.

This is intentionally a spike, not a global default switch.

## Verification

### Focused test
Added coverage confirming that the procedural/admin adapter prefers Unified Search hits for procedural queries.

### Controlled procedural runtime rerun
Ran the SCCM procedural query through the spike path with a controlled Unified Search hit set.

Observed outcome:
- top URLs:
  1. `learn.microsoft.com/.../create-configuration-baselines`
  2. `learn.microsoft.com/.../deploy-configuration-baselines`
  3. `anoopcnair.com/...`
- `source_quality = mixed`
- `relevance = strong`
- `truthfulness = strong`
- `should_revise_report = false`

### Full repo gate
- `410 passed`

## Main conclusion

The spike confirms the working hypothesis:

When `procedural_admin` queries get a better official-doc-capable upstream hit set, the existing downstream pipeline performs well enough.

That means Unified Search is a credible upstream fix candidate for this query class.

## Recommendation

The integration is **worth continuing**, but with guardrails:
- keep it query-class-specific (`procedural_admin` only),
- keep source control / biasing,
- do not replace the global default search path,
- continue to benchmark only the procedural row before any broader rollout.

## Verdict

Recommendation: **worth integrating for `procedural_admin`, with source control / biasing**.
