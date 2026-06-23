# Deep Research procedural report hardening — closure note (2026-06-23)

## Status
Closed as **good enough for this slice**.

## What this slice changed
- hardened the Deep Research report prompt for operator-facing procedural/admin queries
- added explicit anti-invention rules in English
- added a generic exactness guard so exact click-paths, menu chains, field labels, and setup steps are stated only when supported by direct procedural evidence
- refined procedural evidence packing and evaluator behavior around direct vs indirect procedural evidence
- improved `/research` UI run diagnostics so job execution failures are easier to inspect live

## What was verified
- unit coverage for prompt shaping, directness heuristics, evidence packing, and evaluator behavior
- focused web/API test coverage for the related UI/runtime path
- live reruns confirmed the important user-visible behavior:
  - the report stopped inventing exact unsupported admin paths
  - the report now states uncertainty when evidence is indirect or incomplete

## Final quality boundary used to stop
This slice was considered complete once:
- the report no longer invented exact procedural details
- the report communicated uncertainty explicitly when exact procedural evidence was missing
- the remaining issue was mainly evaluator/verdict calibration rather than unsafe or misleading final report content

## What remains deferred
Deferred, not part of this slice:
- `page-archetype-aware gating for procedural_admin evaluator`

Reason for deferral:
- further tuning in the current scoring layer showed diminishing returns
- additional work here would likely overfit to a small number of cases
- the next meaningful improvement should be a separate slice with a clearer page-archetype model rather than more threshold tweaking

## References
- restart brief: `docs/restart-brief-2026-06-23-deep-research-ui-and-runtime.md`
- commit: `b791bb3` — `Harden procedural research reporting and run diagnostics`
