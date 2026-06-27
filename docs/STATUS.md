# STATUS

## 2026-06-27 — SourceTrace v2 runtime surface cleanup checkpoint

Closed a bounded cleanup slice on `sourcetrace_v2` after the earlier runtime/composition work.

What changed:
- unified both HTTP entrypoints on `RuntimeAssembly`
- added `build_stubbed_memory_runtime()` as the canonical in-memory runtime builder for tests
- removed legacy `app/composition/minimal_flow.py`
- rewired v2 tests off `run_minimal_flow(...)` and off `*_demo.py` helper paths
- kept lite-like runtime assembly coverage in place

Current posture:
- canonical v2 path is clearer in both code and tests
- legacy/demo path drift was reduced materially
- v2 test suite is green after cleanup (`26 passed`)\n
Open edge still intentionally left outside this checkpoint:
- JSONL remains a proof-grade persistence seam, not production-grade storage
- real provider path is still lite-like rather than full production integration

## 2026-06-27 — SourceTrace v2 runtime bootstrap correction checkpoint

Closed a small corrective slice after the env-backed LiteLike runtime variant.

What changed:
- moved LiteLike env bootstrap resolution out of the adapter into runtime/bootstrap
- kept `build_env_backed_litellm_like_jsonl_runtime(...)` as a composition facade
- added fail-fast coverage for missing API key env
- changed composition testing from adapter internal-state assertions to behavior-based checks

Current posture:
- env/config responsibility is cleaner again
- adapter seam is narrower and closer to a true gateway
- v2 test suite is green after the correction (`30 passed`)

## 2026-06-27 — SourceTrace v2 run persistence marker checkpoint

Closed the next bounded v2 slice around durable run completion semantics.

What changed:
- added `RunPersistenceMarker` as an explicit run-level persistence completion signal
- extended persistence/readback contracts to save and read a run marker
- wired markers into both in-memory and JSONL storage adapters
- changed readback semantics so `FOUND` now requires both artifact and run marker
- kept partial states explicit as `INCOMPLETE`
- added marker-aware readback and persistence coverage in unit tests

Current posture:
- durable truth is stronger than before because `FOUND` no longer means only “artifact exists”
- run-level persistence completion is now explicit instead of inferred
- v2 unit suite is green after this slice (`33 passed`)

Best next bounded slice:
- add a thin persisted run-envelope/read model projection that exposes marker state and persistence completeness more explicitly without widening transport/framework scope

## 2026-06-27 — SourceTrace v2 persisted run-envelope projection checkpoint

Closed the next bounded v2 slice on persisted readback clarity.

What changed:
- added `PersistedRunEnvelope` as a thin read-model layer over persisted run state
- made persistence completeness explicit as `absent | partial | complete`
- exposed marker presence/state and artifact presence directly in the persisted envelope
- extended API readback projection with a dedicated `persistence` block
- kept storage adapters, persistence flow, and transport surface otherwise unchanged

Current posture:
- persisted run semantics are now explicit instead of being inferred from raw fields
- marker state and persistence completeness are visible in the read model and API projection
- scope stayed bounded: no new backend, no framework expansion, no persistence rewrite

Verification:
- bounded v2 tests passed after the slice (`10 passed`)

Best next bounded slice:
- add a minimal HTTP contract test matrix for `404/202/200` that asserts the new `persistence` block across not-found / incomplete / found readback states
\n## 2026-06-27 — SourceTrace v2 HTTP readback persistence contract checkpoint

Closed the next bounded v2 slice on HTTP readback surface semantics.

What changed:
- added a minimal HTTP contract matrix for persisted readback states `404 / 202 / 200`
- asserted the `persistence` block explicitly across `not_found / incomplete / found`
- covered both partial persistence variants: artifact-only and marker-only
- tightened the happy-path HTTP projection assertions for marker state and persistence presence

Current posture:
- HTTP readback semantics now state persisted completeness explicitly across all three status classes
- transport semantics are better pinned without widening scope beyond tests
- persistence envelope + HTTP projection surface is now materially harder to regress silently

Verification:
- bounded v2 tests passed after the slice (`12 passed`)

Best next bounded slice:
- checkpoint this pair of persisted-readback slices in git so the v2 continuation point is clean before taking on another behavior change

## 2026-06-27 — SourceTrace v2 broader migration plan checkpoint

Recorded a bounded planning artifact for wider v2 migration sequencing.

What changed:
- added `docs/sourcetrace-v2-broader-migration-plan-2026-06-27.md`
- captured a 6-slice broader migration path instead of jumping to full v1 parity planning
- made the next recommended slice explicit: `real search adapter + retrieval input path`
- recorded guardrails to avoid pulling v1 orchestration sprawl into v2

Current posture:
- v2 now has not only a proven minimal spine, but also a bounded next-phase migration frame
- broader migration is now shaped as staged capability proofs, not parity pressure
- the immediate recommendation remains to prove one real evidence-input seam before widening operator or product surface further

Best next bounded slice:
- implement `Slice 1 — Real search adapter + retrieval input path` from the broader migration plan

## 2026-06-27 — SourceTrace v2 Slice 1 retrieval brief checkpoint

Recorded a bounded implementation brief for the next v2 capability slice.

What changed:
- added `docs/sourcetrace-v2-search-adapter-retrieval-input-slice-brief-2026-06-27.md`
- made the next capability target concrete: one real evidence-input seam on the v2 spine
- recommended an explicit `retrieval` stage instead of hiding retrieval inside a vague sub-step
- defined DoD, failure signals, projection posture, and implementation order for the slice

Current posture:
- v2 planning is now specific enough to begin implementation of the first post-spine capability slice
- the next bounded move is no longer abstract “search work”, but a constrained retrieval-attribution slice
- scope is still controlled: one adapter, one bounded seam, one truthful projection path

Best next bounded slice:
- start implementation of `Slice 1 — real search adapter + retrieval input path`

## 2026-06-27 — SourceTrace v2 retrieval seam + evidence-input projection checkpoint

Closed the first post-spine implementation slice for v2.

What changed:
- added explicit `StageId.RETRIEVAL`
- added typed `RetrievedEvidenceCandidate`
- introduced a v2 search seam via `adapters/search/interfaces.py` and `adapters/search/stub.py`
- added a dedicated `RetrievalStage` between `query_refinement` and `evidence_judge`
- extended `ResearchResultArtifact` with `evidence_query` and `evidence_candidates`
- exposed evidence-input provenance through minimal projection, persisted readback projection, and JSONL roundtrip
- extended runtime assembly with a `search` dependency

Current posture:
- v2 now has a real evidence-input seam rather than only an execution/persistence proof
- retrieval is explicitly attributable as its own stage and survives into artifact/readback surfaces
- the slice stayed bounded: one adapter seam, one retrieval stage, one provenance projection path
- search provider breadth is still intentionally narrow; this proves the seam, not provider richness

Verification:
- bounded v2 tests passed after the slice (`15 passed`)

Best next bounded slice:
- replace the stub-only search path with one real provider-backed adapter while preserving the same retrieval-stage and provenance projection contracts

## 2026-06-27 — SourceTrace v2 SearxNG-backed retrieval adapter checkpoint

Closed the next bounded v2 retrieval slice by introducing one real provider-backed search path.

What changed:
- added `src/sourcetrace_v2/adapters/search/searxng.py`
- introduced `SearxNGBootstrap`, `SearxNGSearchGateway`, and `SearchGatewayError`
- added env bootstrap support in `src/sourcetrace_v2/runtime/bootstrap/search.py`
- added dedicated runtime assembly paths for SearxNG-backed v2 runs
- preserved the existing v2 contract: `search seam -> retrieval stage -> typed candidates -> evidence_input projection`

Current posture:
- v2 now has both a bounded stub search seam and one real provider-backed retrieval path
- real retrieval is still isolated behind explicit runtime paths rather than silently replacing all stubbed defaults
- this keeps risk low while proving that the retrieval-stage contract survives contact with a real backend

Verification:
- focused bounded v2 tests passed after the slice (`19 passed`)

Best next bounded slice:
- decide whether to make SearxNG the preferred non-stub v2 runtime path, or move up one layer and implement one more meaningful research workflow over the now-real retrieval input

## 2026-06-27 — SourceTrace v2 retrieval-aware result summary checkpoint

Closed one small workflow-level slice above the real retrieval seam.

What changed:
- replaced the static v2 result summary with a retrieval-aware summary line
- summary now carries the effective retrieval query and top evidence candidate identity
- preserved the bounded surface: no new persistence backend, no evidence packing system, no compiled artifact layer

Current posture:
- v2 output is still intentionally minimal, but no longer looks blind to the retrieved evidence it actually used
- the final artifact now carries one compact workflow-level judgment boundary above raw candidate provenance
- this is still not full evidence packing; it is just enough to make the minimal run output materially less hollow

Verification:
- focused bounded v2 tests passed after the slice (`12 passed`)

Best next bounded slice:
- either promote SearxNG to the preferred non-stub v2 runtime path, or add one compact selected-evidence projection layer above raw candidate lists

## 2026-06-27 — SourceTrace v2 Unified Search readiness checkpoint

Closed the next bounded v2 readiness slice for Unified Search integration.

What changed:
- added `src/sourcetrace_v2/adapters/search/unified_search.py`
- added optional Unified Search bootstrap loader in `src/sourcetrace_v2/runtime/bootstrap/unified_search.py`
- introduced a preferred-search runtime path that tries Unified Search first and falls back to SearxNG
- kept the v2 dependency posture safe: no hard dependency on `mycrewhelper`, no forced default runtime switch

Current posture:
- v2 is now ready for Unified Search integration without making Unified Search mandatory
- the retrieval contract remains stable: `SearchGateway -> retrieval stage -> typed candidates -> evidence_input/result summary`
- fallback posture is explicit and bounded instead of implicit or ad hoc

Verification:
- focused bounded v2 tests passed after the slice (`19 passed`)

Best next bounded slice:
- add one compact selected-evidence projection above raw candidate lists so the output starts separating answer-driving evidence from raw retrieval input

## 2026-06-27 — SourceTrace v2 compact selected-evidence projection checkpoint

Closed the next bounded v2 workflow slice above raw retrieval input.

What changed:
- added a compact `selected_evidence` projection alongside the existing raw `evidence_input` block
- selection stays intentionally simple and deterministic: top-ranked retrieval candidates only
- preserved the old contract instead of replacing it, so operator/debug consumers still see the full raw candidate list

Current posture:
- v2 now distinguishes between raw retrieval input and a compact answer-driving evidence view
- this is still not full evidence packing or evidence-role classification
- the output is materially less hollow while remaining bounded and inspectable

Verification:
- focused bounded v2 tests passed after the slice (`15 passed`)

Best next bounded slice:
- either refine `selected_evidence` with one more compact judgment rule, or start the first truly minimal compiled-artifact projection above the current run artifact

## 2026-06-27 — SourceTrace v2 full-closure map checkpoint

Added a short closure map for finishing v2 as a bounded system.

What changed:
- wrote `docs/sourcetrace-v2-full-closure-map-2026-06-27.md`
- reduced “full v2” to six closure slices instead of vague parity goals
- made the sequencing explicit: knowledge-layer first, then evidence-selection quality, then eval confidence

Current posture:
- v2 no longer lacks only implementation slices; it now also has a bounded closure map
- the next recommended move remains the first minimal compiled-artifact projection
- the map explicitly rejects widening into v1 parity or broad runtime/platform work

Best next bounded slice:
- implement `compiled artifact contract v1` as the first knowledge-layer slice above the current run artifact
