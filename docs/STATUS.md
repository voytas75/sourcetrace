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

## 2026-06-27 — SourceTrace v2 compiled artifact contract v1 checkpoint

Closed the first minimal knowledge-layer slice above the current run artifact.

What changed:
- added `CompiledResearchArtifact` and `CompiledEvidenceSnapshot` contracts
- added a bounded builder that derives a compiled artifact from the current run artifact
- extended in-memory and JSONL persistence with compiled artifact save/load support
- exposed a compact `compiled_artifact` block in readback/HTTP projection

Current posture:
- v2 now has a separate minimal knowledge-layer object rather than only a run artifact
- the compiled artifact is still intentionally thin and derived from current selected evidence
- persistence semantics are honest: compiled artifact can survive independently from the run artifact in partial paths

Verification:
- focused bounded v2 tests passed after the slice (`15 passed`)

Best next bounded slice:
- do a bounded docs unification pass so v2 is clearly the active line and v1 is explicitly marked legacy where needed

## 2026-06-27 — SourceTrace docs posture unification checkpoint

Closed a bounded docs pass to make the active line explicit.

What changed:
- wrote `docs/sourcetrace-v2-docs-posture-2026-06-27.md`
- updated `README-dev.md` so `sourcetrace_v2` is clearly the active implementation line
- explicitly downgraded existing v1 / deep-research runtime docs to legacy-reference status for normal forward work

Current posture:
- repo docs now point new implementation work toward v2 first
- legacy runtime docs are still preserved for migration/support context
- the docs split is explicit without trying to rewrite the whole historical corpus in one pass

Best next bounded slice:
- implement `compiled artifact persistence + readback v1` as the next knowledge-layer closure step, or do a small follow-up pass that tags the most important legacy docs headers explicitly

## 2026-06-27 — SourceTrace v2 explain/debug contract v1 checkpoint

Closed a bounded explain/debug slice over the current `selected_evidence` surface.

What changed:
- extended `selected_evidence` with compact explain/debug fields
- added `selection_notes`, `dropped_count`, and `rejected_reasons`
- kept the current bounded selection policy intact instead of widening into a scoring subsystem

Current posture:
- v2 now shows not only what evidence was promoted, but also why and what was dropped by the current rule
- the operator/debug surface is more self-explaining without hiding the still-simple policy
- this remains a compact contract, not a large evidence-evaluation framework

Verification:
- focused bounded v2 tests passed after the slice (`18 passed`)

Best next bounded slice:
- add one non-rank quality rule to `selected_evidence` (`selected-evidence policy v1`), or formalize compiled-artifact readback as its own explicit HTTP/read-model slice

## 2026-06-27 — SourceTrace v2 eval corpus v1 checkpoint

Closed the next bounded confidence slice after the retrieval/evidence/compiled-artifact surfaces.

What changed:
- added a small runnable eval corpus fixture at `tests/fixtures/v2/eval_corpus_v1.json`
- added `tests/unit/v2/test_eval_corpus_v1.py` to execute the corpus across stub, SearxNG-backed, and preferred-search runtime paths
- pinned expectations for retrieval count, selected-evidence shape, selection basis, compiled artifact presence, and compiled readback status

Current posture:
- v2 now has a small but real reusable evaluation set instead of only slice-local tests
- provider-backed and stubbed paths are both represented
- this is still a bounded corpus, not a benchmark harness or quality scoreboard

Best next bounded slice:
- run one bounded benchmark/quality pass over this corpus and use the findings to justify the next quality-oriented slice

## 2026-06-27 — SourceTrace v2 bounded quality pass checkpoint

Closed a short quality pass over the new v2 eval corpus.

What changed:
- wrote `docs/sourcetrace-v2-bounded-quality-pass-2026-06-27.md`
- used the eval corpus to confirm coherence across stub, SearxNG-backed, and preferred-search runtime paths
- recorded the sharpest remaining weakness as evidence-quality depth rather than contract-shape instability

Current posture:
- v2 now has both a runnable eval corpus and one explicit quality-pass checkpoint over it
- contract-level coherence is good across the currently exercised bounded surfaces
- the next real decisions should now be driven by evidence-quality ambition rather than missing infrastructure seams

Best next bounded slice:
- either extend the eval corpus (`eval corpus v2`) or add one more bounded evidence-quality rule (`selected-evidence policy v2`)

## 2026-06-27 — SourceTrace v2 eval corpus v2 checkpoint

Extended the bounded eval corpus with a few more representative cases.

What changed:
- added `tests/fixtures/v2/eval_corpus_v2.json`
- added `tests/unit/v2/test_eval_corpus_v2.py`
- expanded coverage beyond happy-path run flows to include a thin selected-evidence case and a compiled-readback partial-path case

Current posture:
- the v2 eval surface is now more representative without turning into a benchmark harness
- corpus coverage now includes stub flow, provider-backed flow, preferred-search flow, thin evidence selection, and partial compiled readback
- this remains small and cheap enough to run as a bounded regression boundary

Best next bounded slice:
- use this richer corpus for one follow-up quality decision: either `selected-evidence policy v2` or a slightly broader quality pass over more realistic topic shapes

## 2026-06-27 — SourceTrace v2 selected-evidence policy v2 checkpoint

Closed one more bounded evidence-quality slice over the current selected-evidence surface.

What changed:
- extended `selected_evidence` with a lightweight domain-diversity preference above the existing minimal-content guard
- kept the policy deterministic and compact instead of widening into a scoring engine
- expanded policy/eval tests to cover both thin-content and same-domain competition cases

Current posture:
- selected evidence is now chosen by a small but more credible quality stack: minimal content guard + explain/debug + domain diversity preference
- the policy is still bounded and cheap to reason about
- eval corpus v2 now exercises the new diversity rule explicitly

Verification:
- focused bounded v2 tests passed after the slice (`12 passed`)

Best next bounded slice:
- run a quality pass v2 over the richer corpus, or add one more small realism-oriented eval case before changing policy again

## 2026-06-27 — SourceTrace v2 bounded quality pass v2 checkpoint

Closed a second bounded quality pass after `selected-evidence policy v2`.

What changed:
- wrote `docs/sourcetrace-v2-bounded-quality-pass-v2-2026-06-27.md`
- verified both `eval_corpus_v1` and `eval_corpus_v2` against the current policy-v2 surface
- sharpened the remaining-gap diagnosis from heuristic fragility to corpus realism

Current posture:
- v2 is coherent across the bounded contract, evidence-selection, compiled-artifact, and provider-backed surfaces it currently exercises
- the next likely bottleneck is not missing plumbing or one more tiny heuristic, but more realistic evaluation cases
- policy changes should now be justified by new corpus evidence rather than taste

Best next bounded slice:
- extend the corpus again (`eval corpus v3`) with a few more realistic topic shapes before changing evidence policy further

## 2026-06-27 — SourceTrace v2 eval corpus v3 checkpoint

Extended the bounded corpus again, this time toward more realistic topic shapes.

What changed:
- added `tests/fixtures/v2/eval_corpus_v3.json`
- added `tests/unit/v2/test_eval_corpus_v3.py`
- introduced more realistic remote-work, IT-admin, official-vs-duplicate-domain, and thin-news-vs-richer-source cases while keeping the harness bounded and synthetic

Current posture:
- the corpus is still lightweight, but it is less toy-like than v1/v2
- realistic topical shapes now exist for both run-flow and selected-evidence-only paths
- this should make future policy changes harder to justify without evidence and easier to evaluate when they are justified

Best next bounded slice:
- run a quality pass v3 over this richer corpus and decide whether the next bottleneck is still corpus realism or finally a new evidence-quality rule

## 2026-06-27 — SourceTrace v2 bounded quality pass v3 checkpoint

Closed a third bounded quality pass after `eval corpus v3`.

What changed:
- wrote `docs/sourcetrace-v2-bounded-quality-pass-v3-2026-06-27.md`
- checked the policy-v2 surface against more realistic topical fixture shapes
- narrowed the remaining gap diagnosis from generic corpus realism to authority-vs-relevance collision realism

Current posture:
- the current bounded v2 policy stack is coherent across synthetic but increasingly realistic topical cases
- there is still no evidence that more heuristics are the right next move
- the next best signal should come from sharper corpus collisions, not from adding another generic rule first

Best next bounded slice:
- add `eval corpus v4` focused on authority-vs-relevance and official-vs-commentary collisions before changing policy again

## 2026-06-27 — SourceTrace v2 eval corpus v4 checkpoint

Extended the bounded corpus toward authority-vs-relevance and official-vs-commentary collisions.

What changed:
- added `tests/fixtures/v2/eval_corpus_v4.json`
- added `tests/unit/v2/test_eval_corpus_v4.py`
- introduced explicit collision cases for official-broad vs direct commentary, institutional guidance vs consultancy commentary, and a run-flow collision case over the same topic shape

Current posture:
- the bounded corpus now starts to stress the exact decision boundary that earlier quality passes identified as the next weak point
- this still does not prove the policy is optimal, but it makes future policy changes far less guessy
- the next best move is to run a quality pass v4 over this collision-focused corpus before deciding whether policy should change again

Best next bounded slice:
- run `quality pass v4` over the new collision-focused corpus and use that to decide whether a policy-v3 change is justified at all
