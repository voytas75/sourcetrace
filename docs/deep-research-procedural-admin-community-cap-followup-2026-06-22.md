# Deep Research procedural_admin community-cap follow-up — 2026-06-22

Status: implemented
Date: 2026-06-22
Scope: final bounded polish slice to reduce community-source bleed when enough official procedural docs are already present.

## What changed

Added a small community-cap behavior for `procedural_admin`:

### Pre-extraction filter
If two official-doc hits already survive as strong candidates:
- keep the official hits,
- do not admit an extra secondary/community hit into the kept set.

### Evidence packing
If official docs are already present in the procedural core:
- do not promote extra `docs` / `generic` material into supporting evidence,
- keep that material in background instead.

This is intentionally narrow.
\n## Verification

### Focused tests
Added coverage confirming:
- when two official Microsoft Learn hits exist, the pre-extraction kept set no longer admits the extra community result.

### Procedural rerun
Observed outcome for the SCCM procedural query:
- top URLs:
  1. `learn.microsoft.com/.../create-configuration-baselines`
  2. `learn.microsoft.com/.../deploy-configuration-baselines`
- `source_quality = strong`
- `relevance = strong`
- `truthfulness = strong`
- `should_revise_report = false`

### Full repo gate
- `412 passed`

## Result

This achieved the intended final polish:
- the procedural/admin row no longer carries an unnecessary community-source penalty when official docs are already sufficient,
- evaluator now upgrades source quality from `mixed` to `strong` in the tested SCCM path.

## Verdict

This was the right last bounded quality slice for the current thread.

The original procedural/admin weakness has now been addressed end-to-end:
- better upstream recall via query-class-specific Unified Search path,
- safe fallback when Unified Search is weak,
- downstream authority-first filtering,
- final community-cap to avoid needless mixed-source downgrade once official docs are already enough.
