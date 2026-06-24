# Deep Research compiled artifact hardening implementation slice brief v1

Status: planned / implementing
Date: 2026-06-24
Scope: bounded Slice 7 implementation for SourceTrace Deep Research

## Goal
Enrich the existing `CompiledResearchArtifact` with selected snapshots from the new artifact chain so compiled artifacts become a stronger reusable knowledge boundary without expanding into a new persistence system.

## Why this slice now
SourceTrace now has a coherent result-artifact chain:
- `ProblemAnalysis`
- `ResearchExecutionPlan`
- `ResearchEvidencePack`
- `ResearchBranchProposalSet`
- `ResearchBranchEvaluation`
- `ResearchReflection`

Compiled artifacts already exist, but they do not yet preserve enough of that chain to support later artifact lint and reusable-topic workflows.

## Non-goals
- no new compiled-artifact storage subsystem
- no artifact lint expansion in this slice
- no wiki/memory promotion path yet
- no UI redesign beyond payload exposure

## Proposed hardening
Add bounded snapshots to `CompiledResearchArtifact`:
- keep existing `problem_analysis_snapshot`
- add `execution_plan_snapshot`
- add `reflection_snapshot`
- optionally add compact branch summary snapshot if already cheap

Do **not** copy the full raw result artifact wholesale.

## Snapshot rules
- preserve only compact, structurally useful artifacts
- avoid duplicating raw findings/evidence blobs unnecessarily
- keep compiled artifact reusable and inspectable

## Persistence target
- existing `CompiledResearchArtifact`

## API surfaces
Expose the new snapshots in:
- compiled artifact payloads
- existing debug JSON surfaces through serializer inclusion

## Implementation plan
1. Extend compiled artifact contract with compact snapshots.
2. Wire snapshot population in `_compile_research_artifact()`.
3. Expose serializer payloads.
4. Add focused tests.

## Definition of done
- compiled artifacts retain selected snapshots from the artifact chain
- payloads expose those snapshots
- focused tests pass

## Risks
### Risk: compiled artifact becomes a copy of result artifact
Mitigation: include only selected compact snapshots.

### Risk: snapshot sprawl
Mitigation: add only what materially helps future lint / reuse.

### Risk: persistence duplication noise
Mitigation: keep evidence pack out unless compact summary is needed later.

## Rollback
Revert:
- compiled artifact contract additions
- compile-path wiring
- serializer wiring
- focused tests for this slice
