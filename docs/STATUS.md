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

## 2026-06-27 — SourceTrace v2 bounded quality pass v4 checkpoint

Closed the collision-focused quality pass after `eval corpus v4`.

What changed:
- wrote `docs/sourcetrace-v2-bounded-quality-pass-v4-2026-06-27.md`
- checked policy v2 against authority-vs-relevance and official-vs-commentary collision fixtures
- concluded that the current selected-evidence stack is good enough for the bounded v2 baseline

Current posture:
- the evidence-selection layer no longer looks like the main unfinished weakness in the bounded v2 track
- further policy tweaks should now be requirement-driven, not reflexive
- the smarter next move is probably to freeze the current baseline or explicitly open a more ambitious post-baseline policy track

Best next bounded slice:
- choose whether to freeze the current evidence-policy baseline for v2, or define a separate post-baseline authority/relevance policy track

## 2026-06-27 — SourceTrace v2 evidence-policy baseline freeze checkpoint

Closed the baseline decision for the current bounded v2 evidence-selection stack.

What changed:
- wrote `docs/sourcetrace-v2-evidence-policy-baseline-freeze-2026-06-27.md`
- explicitly froze the current evidence-selection policy as the bounded v2 baseline
- defined reopen conditions so future policy work must be requirement-driven or corpus-driven

Current posture:
- `selected_evidence` policy should now be treated as stable for the bounded v2 line
- further heuristic tweaks are no longer the default next move
- any future authority/relevance policy expansion should be opened as a deliberate post-baseline track, not as drift inside the current closure line

Best next bounded slice:
- shift from evidence-policy tweaking to broader v2 closure/packaging work, or explicitly define a post-baseline authority/relevance policy track if that is now the goal

## 2026-06-27 — SourceTrace v2 closure / packaging checkpoint

Recorded the current closure posture for the bounded v2 line.

What changed:
- wrote `docs/sourcetrace-v2-closure-packaging-checkpoint-2026-06-27.md`
- separated what is already closed enough for the bounded baseline from what remains explicitly out of scope
- defined what should count as release-like closure for this line without pretending it is full product closure

Current posture:
- v2 can now be described not only as a stack of slices, but as a bounded baseline system with a closure posture
- evidence-policy work is baseline-frozen and no longer the default destination for more iteration
- the next sensible work should be either packaging/closure polish or a deliberate post-baseline expansion track

Best next bounded slice:
- write one concise v2 release/closure note and one short v2-only operator/start-here note, or explicitly open a post-baseline track if new capability work is desired

## 2026-06-27 — SourceTrace v2 packaging notes checkpoint

Closed the last obvious small packaging/closure docs gap for the bounded v2 line.

What changed:
- wrote `docs/sourcetrace-v2-release-closure-note-2026-06-27.md`
- wrote `docs/sourcetrace-v2-operator-start-here-2026-06-27.md`
- made the continuation posture explicit for both closure/packaging mode and post-baseline expansion mode

Current posture:
- v2 now has a baseline closure note, a packaging checkpoint, and a simple operator start-here path
- restartability is materially better than before
- further work should now either be small packaging polish or an explicitly named new track

Best next bounded slice:
- stop here and treat the bounded v2 baseline as closed enough, or explicitly open the next named track if new work is wanted

## 2026-06-28 — SourceTrace v2 production-readiness track / live LLM path v1 checkpoint

Opened a separate production-readiness track and closed the first live-LLM runtime slice.

What changed:
- wrote `docs/sourcetrace-v2-production-readiness-track-2026-06-28.md`
- wrote `docs/sourcetrace-v2-live-llm-runtime-path-v1-2026-06-28.md`
- added provider-specific model ids to runtime profiles
- added a real env-backed LiteLLM live runtime path
- fixed Azure `research_fast` compatibility by setting a config-level temperature compatible with `gpt-5.4-mini`

Current posture:
- v2 now has a real provider-configured live LLM runtime path instead of only a seam plus injected callback story
- Azure is the first real provider implementation, but the config shape is no longer locked to raw logical model names only
- this does not make v2 fully production-ready yet, but it removes one of the sharpest blockers

Best next bounded slice:
- rerun and evaluate the live smoke path, then decide whether the next blocker is PDF/document read, operator entrypoint polish, or another provider/runtime compatibility edge

## 2026-06-28 — SourceTrace v2 authority/relevance judgment contract v1 checkpoint

Closed the first bounded authority/relevance judgment slice above the selected-evidence baseline.

What changed:
- added a shared `selected_evidence` policy helper in `src/sourcetrace_v2/core/policies/selected_evidence.py`
- removed the compiled-artifact selector drift by reusing the same bounded selected-evidence decision path as the API projection
- formalized `authority-relevance-judgment-contract-v1` as a provider-agnostic judgment contract over query/title/url/snippet
- projected judgment details both in `selected_evidence` API output and in compiled-artifact selected evidence
- exposed compiled-artifact `selected_evidence_contract_version` so downstream consumers can pin the bounded judgment shape explicitly

Current posture:
- selected-evidence promotion and compiled-artifact promotion now share one bounded decision path instead of silently diverging on raw rank slicing
- the new authority/relevance layer is still compact and provider-agnostic; it is a judgment contract, not a topic-specific heuristic bundle
- this closes the immediate design mismatch without reopening the earlier baseline-frozen evidence-policy track

Verification:
- focused v2 tests passed after the slice (`14 passed`)

Best next bounded slice:
- validate whether this contract is sufficient for downstream authority/relevance consumers, or open a separate bounded slice for judgment-consumer integration rather than expanding the contract ad hoc

## 2026-06-28 — SourceTrace v2 authority/relevance judgment consumer integration v1 checkpoint

Closed one real downstream consumer validation path for the new authority/relevance judgment contract.

What changed:
- added a focused compiled-readback test in `tests/unit/v2/test_compiled_readback.py`
- verified that persisted compiled-artifact HTTP readback preserves `selected_evidence_contract_version`
- verified that compiled selected-evidence items preserve the bounded judgment payload shape: `authority`, `topic_match`, `specificity`, `answer_fit`
- kept the slice strictly on consumer validation: no contract expansion and no new deterministic heuristics

Current posture:
- the judgment contract is now exercised not only at live projection time but also through one persisted downstream consumer path
- compiled-artifact readback is a real consumer boundary because it depends on saved artifact state, not only in-memory projection helpers
- this is enough to treat `authority-relevance-judgment-consumer-integration-v1` as closed in bounded form

Verification:
- focused v2 compiled-readback/compiled-artifact tests passed after the slice (`7 passed`)

Best next bounded slice:
- stop here unless another concrete downstream consumer proves missing judgment fields in practice; prefer a second consumer-only validation slice over contract drift

## 2026-06-28 — SourceTrace v2 production-readiness live smoke evaluation v1 checkpoint

Ran one real v2 live smoke on the current env-backed LiteLLM + SearxNG runtime path and used it to identify the actual next blocker.

What happened:
- confirmed Azure live LLM env was present and SearxNG at `http://127.0.0.1:18080` was reachable
- ran a real v2 live smoke through `build_env_backed_live_litellm_with_searxng_jsonl_runtime(...)`
- first live run completed the research flow but failed during persisted execution readback projection
- the concrete blocker was `JsonlResultArtifactRepository.get_compiled_artifact(...)` restoring compiled selected-evidence `judgment` payloads as raw dicts instead of typed `EvidenceJudgmentSnapshot` values
- repaired JSONL compiled-artifact judgment deserialization and preserved `selected_evidence_contract_version` on readback
- added focused JSONL storage coverage for compiled-artifact judgment readback shape
- reran the real live smoke successfully after the repair

Current posture:
- the v2 live runtime path now completes one real end-to-end smoke with live Azure LLM calls and real SearxNG retrieval
- the blocker exposed by the first live smoke was not PDF/document read or operator entrypoint polish yet; it was a persistence/readback seam in compiled-artifact JSONL restoration
- after the repair, live smoke returns `201/found` with `candidate_count=3`, `selected_count=2`, `llm_calls=4`, `degraded_calls=0`, `compiled_artifact.present=true`, and `selected_evidence_contract_version=authority-relevance-judgment-contract-v1`

Verification:
- focused tests passed after the repair (`11 passed`)
- real live smoke passed end-to-end on Azure + SearxNG after the fix

Best next bounded slice:
- choose the next production-readiness blocker above this repaired runtime path: either `pdf-document-read-seam-v1` if end-to-end document ingestion is the sharpest real gap, or `operator-live-entrypoint-v1` if the sharper problem is repeatable operator execution without ad hoc harness code

## 2026-06-28 — SourceTrace v2 pdf-document-read-seam-v1 checkpoint

Closed the first bounded v2-native PDF/document seam slice without pretending the minimal flow is already fully PDF-aware.

What changed:
- added a v2 PDF contract in `src/sourcetrace_v2/adapters/pdf/interfaces.py`
- added a thin runtime-backed adapter in `src/sourcetrace_v2/adapters/pdf/runtime_ingest.py`
- exposed an optional `pdf` slot on `RuntimeAssembly` so v2 runtime composition can carry a typed PDF gateway explicitly
- added focused adapter coverage in `tests/unit/v2/test_pdf_runtime_adapter.py`
- refreshed one legacy PDF-ingest test expectation to match the current preview -> page-selection -> full-read path

Current posture:
- v2 now has an explicit PDF/document seam in its own adapter layer instead of an empty `adapters/pdf/` placeholder
- this slice keeps v2 structurally honest: it reuses the runtime PDF analyzer through a bounded adapter, but does not wire v1 internals directly into v2 core contracts
- minimal v2 research flow is still not claiming full PDF-aware evidence promotion yet; this slice only establishes the production seam needed for that next integration step

Verification:
- focused PDF/runtime tests passed after the slice (`22 passed`)

Best next bounded slice:
- wire one real v2 consumer path to the new PDF seam, likely `pdf-document-read-consumer-integration-v1`, instead of broadening the seam contract or pretending full PDF policy is done

## 2026-06-28 — SourceTrace v2 pdf-document-read-consumer-integration-v1 checkpoint

Closed one real consumer path for the new v2 PDF/document seam using the native PDF-reading route rather than an image-model fallback.

What changed:
- wired the retrieval stage so PDF-like candidates can be post-processed through the optional v2 `pdf` gateway
- kept the integration bounded: when a PDF candidate is positively read, its snippet is enriched with PDF-derived scope/entity/findings text instead of inventing a new wide artifact contract
- threaded the optional `pdf` gateway through execution, run-use-case, and HTTP entrypoint paths
- added focused coverage in `tests/unit/v2/test_pdf_consumer_integration.py`

Current posture:
- v2 now has one real consumer path for native PDF reading/analysis: retrieval -> PDF seam -> candidate snippet enrichment -> normal selected-evidence/compiled-artifact flow
- this uses the proper PDF-reading mechanism through the runtime analyzer seam, not an image-model shortcut
- the slice is still intentionally bounded: it improves one consumer path without claiming full PDF-aware deep-research policy or broad document-processing semantics

Verification:
- focused v2 tests passed after the slice (`10 passed`)

Best next bounded slice:
- either promote this from snippet enrichment into a more explicit typed evidence carry-forward path, or switch tracks to `operator-live-entrypoint-v1` if production readiness now hurts more on repeatable operator execution than on document semantics

## 2026-06-28 — SourceTrace v2 operator-live-entrypoint-v1 checkpoint

Closed the first real operator-facing live entrypoint for v2.

What changed:
- added a repo-owned v2 CLI entrypoint in `src/sourcetrace_v2/operator/run_minimal_flow.py`
- added a package hook in `pyproject.toml` as `sourcetrace-v2-run`
- the entrypoint builds the env-backed live Azure + SearxNG runtime, wires the native PDF-reading gateway, runs one bounded minimal flow, and emits the operator-facing JSON payload to stdout
- added focused test coverage in `tests/unit/v2/test_operator_entrypoint.py`

Current posture:
- v2 no longer depends on ad hoc inline Python harness code for one real operator path
- there is now a repeatable operator command for a bounded live run path that stays aligned with the current v2 runtime composition and projections
- this is intentionally a narrow CLI path, not a broad new UI/runtime manager

Verification:
- focused entrypoint tests passed (`3 passed`)
- a real live operator smoke through `python -m sourcetrace_v2.operator.run_minimal_flow ...` completed successfully and returned `status=found`, `candidate_count=3`, `selected_count=2`, `compiled_artifact.present=true`, `top_provider=searxng`

Best next bounded slice:
- pause and reassess the next practical production-readiness gap from this stronger baseline; the sharpest next move is likely either typed PDF evidence carry-forward or a thin operator readback/status CLI companion rather than more runtime plumbing

## 2026-06-28 — SourceTrace v2 operator-readback-status-cli-companion-v1 checkpoint

Closed the next narrow operator-facing gap after the live run entrypoint.

What changed:
- added a repo-owned v2 readback CLI in `src/sourcetrace_v2/operator/readback.py`
- added a package hook in `pyproject.toml` as `sourcetrace-v2-readback`
- the CLI exposes two bounded persisted-view modes: `execution` and `compiled`
- it loads existing JSONL-backed persisted views and emits the same operator-facing JSON projections already used by the HTTP/service path
- added focused coverage in `tests/unit/v2/test_operator_readback.py`

Current posture:
- v2 now has a simple repo-owned operator pair: one command to run a bounded live flow and one command to read back persisted execution/compiled state
- operators no longer need ad hoc inline Python for the basic run -> inspect loop on JSONL-backed artifacts
- this stays intentionally narrow: it is a CLI companion over existing readback services, not a new runtime manager or dashboard

Verification:
- focused operator tests passed (`7 passed`)
- real smoke passed through the full operator loop: `run_status=found`, `execution_status=found`, `compiled_status=found`, `execution_receipts=10`, `compiled_artifact.present=true`

Best next bounded slice:
- if the next real pain is evidence semantics, move to typed PDF evidence carry-forward; if the next real pain is operator ergonomics, the next narrow move would be lightweight filtering/summary polish on the readback CLI rather than new runtime plumbing

## 2026-06-28 — SourceTrace v2 typed-pdf-evidence-carry-forward-v1 checkpoint

Closed the first bounded typed carry-forward slice for PDF-derived evidence.

What changed:
- added typed `pdf_context` on retrieval-side evidence candidates in `src/sourcetrace_v2/core/domain/models.py`
- added typed `pdf_context` snapshot support on compiled selected-evidence artifacts in `src/sourcetrace_v2/core/contracts/compiled_artifacts.py`
- retrieval-stage PDF enrichment now stores structured PDF-derived fields alongside the snippet, not only inside the snippet text
- compiled-artifact building now carries that typed PDF context into selected-evidence snapshots
- compiled-artifact projection now exposes `selected_evidence[*].pdf_context`
- JSONL result + compiled-artifact roundtrip now preserves PDF context through persistence/readback
- added focused coverage in `tests/unit/v2/test_pdf_typed_carry_forward.py` and `tests/unit/v2/test_pdf_jsonl_roundtrip.py`

Current posture:
- PDF-derived evidence is no longer snippet-only; v2 now has a narrow typed carry-forward path from retrieval enrichment into compiled selected-evidence artifacts
- this does not change selected-evidence policy, judgment contract, or broader evidence semantics
- the slice stays intentionally bounded: one typed seam for PDF context, not a broad document contract expansion

Verification:
- focused tests passed (`9 passed`)
- a real operator loop smoke confirmed the run/compiled readback path remained healthy after the change
- note: the live smoke query/provider mix did not yield a selected evidence item with positive `pdf_context` in that specific run, so the live check verified non-regression of the operator path rather than a positive live PDF-context hit

Best next bounded slice:
- the sharpest next move is likely a consumer-validation slice for typed PDF context through one persisted downstream readback boundary, or a query/fixture-shaped live verification slice if you specifically want proof of positive live PDF-context carry-forward rather than just typed persistence support

## 2026-06-28 — SourceTrace v2 typed-pdf-context-consumer-validation-v1 checkpoint

Closed one real downstream consumer validation path for the new typed PDF context payload.

What changed:
- added focused compiled-readback coverage in `tests/unit/v2/test_compiled_readback.py`
- validated that persisted compiled-artifact HTTP/readback projection preserves `selected_evidence[*].pdf_context`
- validated bounded typed shape only: `document_scope`, `entity_match_summary`, `key_findings`
- kept the slice strictly on consumer validation: no contract expansion, no policy changes, no extra runtime plumbing

Current posture:
- typed PDF context is now exercised not only at build/projection time but also through one persisted downstream consumer boundary
- this is the right validation seam because it proves the new typed payload survives saved compiled-artifact state and readback projection, not only in-memory assembly
- together with the previous carry-forward slice, this is enough to treat typed PDF context as a real persisted consumer-facing capability in bounded form

Verification:
- focused validation tests passed (`7 passed`)

Best next bounded slice:
- if you want stronger proof, do a positive live-PDF-hit verification slice with a query/fixture shaped to force a PDF winner; otherwise the sharper remaining work is probably not more PDF plumbing but broader evidence-quality or operator-summary priorities

## 2026-06-28 — SourceTrace v2 authority-relevance-outcome-evaluation-v1 checkpoint

Closed a bounded outcome-evaluation slice over the current authority/relevance selection surface without changing policy.

What changed:
- added a small authority/relevance outcome fixture at `tests/fixtures/v2/authority_relevance_outcome_eval_v1.json`
- added `tests/unit/v2/test_authority_relevance_outcome_eval_v1.py`
- evaluated a few representative authority-vs-relevance cases against two concrete output surfaces:
  - selected-evidence projection
  - compiled selected-evidence artifact
- encoded explicit human verdict expectations as bounded outcome criteria: `must_include`, `must_exclude`, and a short case note

What this slice shows:
- the current bounded policy still produces coherent operator-facing pairs for the exercised cases
- the present selection surface is acceptable when asked to balance:
  - one authoritative institutional source
  - one more direct practical/commentary source
  - while dropping thin or duplicate-domain alternatives
- this gives a better quality checkpoint than raw regression expectations alone because it states what outcome shape is considered acceptable and why

Current posture:
- this is still an evaluation slice, not a policy-change slice
- no judgment-contract expansion, no deterministic heuristic additions, and no runtime plumbing changes were needed
- for the exercised fixture cases, the current authority/relevance posture is good enough to keep moving without immediate policy edits

Verification:
- focused evaluation tests passed (`5 passed`)

Best next bounded slice:
- either extend this into a small `authority-relevance-outcome-evaluation-v2` set with a few harder real-world collisions, or stay disciplined and wait for a concrete failure before touching the selection policy again

## 2026-06-28 — SourceTrace v2 authority-relevance-outcome-evaluation-v2 checkpoint

Extended the bounded authority/relevance outcome evaluation with a few harder, more realistic collision shapes.

What changed:
- added `tests/fixtures/v2/authority_relevance_outcome_eval_v2.json`
- added `tests/unit/v2/test_authority_relevance_outcome_eval_v2.py`
- exercised harder outcome cases such as:
  - broad official vs specific official vs direct commentary
  - official advisory vs vendor operator guide vs vendor duplicate-domain FAQ
  - high-rank thin official trap vs specific official document vs practical commentary
  - duplicate-domain institutional crowding vs one independent practical source

What this slice shows:
- the current bounded selection surface still produces coherent two-item outcome pairs for these harder collision shapes
- the present posture continues to prefer a balanced pair of:
  - one authoritative/institutional source
  - one direct practical/operator-facing source
- thin-content traps and duplicate-domain crowding are handled acceptably within the current bounded policy surface for the exercised fixtures
- there is still at least one intentionally uncomfortable case where a broader official page wins over a narrower official FAQ because the second slot goes to a commentary source; this is acceptable under the current bounded design, but it is now explicitly documented rather than hidden

Current posture:
- this remains an evaluation-only slice; no policy changes were made
- after v1 + v2 outcome evaluation, there is still no strong evidence that the current authority/relevance surface needs immediate heuristic expansion
- the sharper next move is no longer another synthetic quality pass by default; it is either waiting for a concrete failure or doing bounded live verification on chosen real queries

Verification:
- focused evaluation tests passed (`3 passed`)

Best next bounded slice:
- pause policy work unless a concrete failure appears; if you want stronger confidence, prefer a small live verification slice on 3–5 chosen real queries over more synthetic fixture growth

## 2026-06-28 — SourceTrace v2 authority-relevance-live-verification-v1 checkpoint

Ran a bounded live verification pass on a few real queries and used it to test whether the current authority/relevance posture still holds on the real provider mix.

What changed:
- added `docs/authority-relevance-live-verification-v1-2026-06-28.md`
- ran four live queries through the current v2 operator/runtime path with Azure + SearxNG
- evaluated compiled selected-evidence outcomes and bounded judgment bands for each live run

What this slice showed:
- this was a useful reality check because it broke the comfortable synthetic-fixture story
- the live outcomes were weak enough that the main problem is **not** best explained by downstream authority/relevance selection alone
- for multiple queries, selected evidence was commentary-heavy, broad, or plainly off-topic before any downstream refinement could save it
- the most important conclusion is negative: this live pass does **not** justify immediate authority/relevance policy expansion

Observed posture:
- fixture/eval-corpus checks still show the bounded selector behaves coherently when given a reasonable candidate pool
- live verification exposed that the sharper real weakness is upstream candidate quality:
  - query shaping
  - retrieval source mix
  - candidate relevance before evidence judgment/selection
- one case (`legal hold steps records retention official guidance`) failed hard enough to make this especially clear: the selected evidence was plainly off-topic, which means downstream selector tuning would be treating the symptom, not the cause

Verification:
- bounded live verification was completed on four real queries
- findings were recorded in `docs/authority-relevance-live-verification-v1-2026-06-28.md`

Best next bounded slice:
- do **not** change authority/relevance selection policy yet; the sharper next move is `authority-relevance-live-retrieval-diagnostics-v1` to localize why real queries are producing weak/off-topic candidate pools before selection

## 2026-06-28 — SourceTrace v2 authority-relevance-live-retrieval-diagnostics-v1 checkpoint

Localized the live authority/relevance failure more sharply.

What changed:
- added `docs/authority-relevance-live-retrieval-diagnostics-v1-2026-06-28.md`
- ran focused live diagnostics on the same query class that previously showed weak authority/relevance outcomes
- inspected persisted execution readback to compare:
  - original seed query
  - retrieval-stage `evidence_query`
  - stage degradation state
  - top selected results

What this slice showed:
- the sharpest current live defect is upstream **retrieval query handoff**, not downstream selector behavior
- retrieval is currently using large assistant-style prose blobs as `evidence_query` instead of a bounded search query derived directly from user intent
- this strongly explains why live candidate pools can become broad, commentary-heavy, or off-topic before authority/relevance judgment even starts
- in short: the live path is drifting because the retrieval contract is wrong or too loose, not because the selector necessarily needs more heuristics

Key observation:
- for all checked live queries, `evidence_query_equals_seed` was `false`
- retrieved query prefixes looked like answer prose or follow-up assistance prose, e.g. `This is a solid summary...`, `If you want, I can help...`, `Here are the official guidance sources...`
- one query (`identity-break-glass`) still happened to land a better top official result, but that success looked incidental rather than structurally trustworthy because the same loose handoff mechanism was still in play

Current posture:
- do not patch authority/relevance selection policy from this evidence
- the sharper next repair target is the planning/query-refinement -> retrieval handoff contract
- fixture-level quality work remains useful, but live behavior now points clearly at a bounded upstream contract issue

Verification:
- live diagnostics completed and recorded in `docs/authority-relevance-live-retrieval-diagnostics-v1-2026-06-28.md`

Best next bounded slice:
- `authority-relevance-query-handoff-contract-v1` — introduce a bounded retrieval-query handoff so retrieval consumes an explicit search-intent string rather than freeform answer prose

## 2026-06-28 — SourceTrace v2 authority-relevance-live-verification-v2 checkpoint

Re-ran the live authority/relevance verification after repairing the retrieval query handoff contract.

What changed:
- added `docs/authority-relevance-live-verification-v2-2026-06-28.md`
- re-ran four real queries through the current v2 operator/runtime path after `authority-relevance-query-handoff-contract-v1`
- evaluated persisted execution outcomes, selected evidence, and judgment bands again

What this slice showed:
- the handoff repair materially improved live behavior
- `evidence_query` now matched the bounded seed query in all four rerun cases
- live candidate sets were no longer drifting into assistant-style prose retrieval
- the overall quality of selected evidence improved significantly versus the earlier live pass

Observed posture after the repair:
- `remote work reporting` improved sharply in topicality and specificity, but still leaned commentary/legal-adjacent rather than strongly official
- `identity break-glass` improved to a broadly good pair: Microsoft Learn + practical commentary
- `breach notification` improved the most, landing a strong institutional pair (FTC + ICO)
- `legal hold steps` improved dramatically from off-topic failure to coherent practical/vendor guidance, but still lacked a stronger official/public-institutional source

Current posture:
- this is strong evidence that the query handoff defect was real and important
- downstream authority/relevance selection policy still should not be the first target
- the sharper remaining weakness is now narrower: source mix / authority profile of retrieved candidates on some topics, not freeform query drift

Verification:
- bounded live verification completed and recorded in `docs/authority-relevance-live-verification-v2-2026-06-28.md`

Best next bounded slice:
- `authority-relevance-source-mix-diagnostics-v1` — inspect why some corrected live queries still land commentary/vendor-heavy candidate pools instead of stronger institutional sources before changing policy

## 2026-06-28 — SourceTrace v2 authority-relevance-source-mix-diagnostics-v1 checkpoint

Ran the next bounded diagnostic pass after the handoff repair and live rerun.

What changed:
- added `docs/authority-relevance-source-mix-diagnostics-v1-2026-06-28.md`
- inspected the current search/retrieval surface for the remaining weak live cases
- checked whether institutional sources were absent entirely or merely losing in provider ranking / shallow truncation

What this slice showed:
- the remaining weakness is best described as **source-mix bias under plain retrieval**
- the search layer is currently very thin: plain query in, top-N rows out, almost no source-type metadata, no institutional biasing before truncation
- for strong cases like breach notification, institutional sources already appear near the top and the system behaves well enough
- for weaker cases like legal hold steps, institutional sources do appear in raw provider output, but practical/vendor sources outrank them early enough that the bounded candidate pool still leans commentary-heavy

Current posture:
- this is still an upstream retrieval/source-ordering problem, not a reason to expand downstream selector policy first
- after the query-handoff fix, the next honest pressure point is how to improve institutional source survival into the candidate pool for queries that imply an official/institutional preference

Verification:
- findings recorded in `docs/authority-relevance-source-mix-diagnostics-v1-2026-06-28.md`

Best next bounded slice:
- `authority-relevance-source-mix-shaping-v1` — improve the odds that official/institutional sources survive into the bounded candidate pool without changing downstream selector policy in the same slice

## 2026-06-28 — SourceTrace v2 authority-relevance-source-mix-shaping-v1 checkpoint

Closed the first bounded upstream shaping slice after the source-mix diagnostics.

What changed:
- added a narrow source-mix shaping step in `src/sourcetrace_v2/execution/stages/retrieval.py`
- shaping activates only when the query implies official/institutional intent
- shaping lightly reorders retrieved candidates toward more institutional-looking sources before later selection
- added focused coverage in `tests/unit/v2/test_source_mix_shaping.py`

What this slice showed:
- this is a valid upstream move: it improves institutional-source survival pressure without touching downstream selector policy
- strongest institutional cases (for example breach notification) did not regress
- weaker cases (for example legal hold steps) improved somewhat in result shape, but still do not consistently land a clearly public-institutional pair
- this confirms the remaining gap is now about shallow source typing / approximate institutional detection more than about the absence of any upstream shaping at all

Current posture:
- keep downstream authority/relevance selector policy unchanged
- treat this slice as a bounded retrieval/source-ordering improvement, not a final authority solution
- the next sharp move, if we keep pushing this line, is better source typing rather than more ad hoc shaping rules

Verification:
- focused tests passed (`4 passed`)
- small live check recorded in `docs/authority-relevance-source-mix-shaping-v1-2026-06-28.md`

Best next bounded slice:
- `authority-relevance-source-typing-v1` — add explicit source-type metadata early enough to support cleaner upstream shaping and diagnostics without changing selector policy in the same slice

## 2026-06-28 — SourceTrace v2 authority-relevance-source-typing-v1 checkpoint

Closed the next bounded upstream slice after source-mix shaping.

What changed:
- added explicit `source_type` on `RetrievedEvidenceCandidate`
- added a narrow early classification pass in retrieval with bounded classes: `institutional`, `vendor`, `commentary`, `unknown`
- exposed `source_type` through minimal/readback/evidence projections
- preserved `source_type` through JSONL result-artifact readback
- added focused coverage in `tests/unit/v2/test_source_typing.py` and `tests/unit/v2/test_source_type_jsonl_roundtrip.py`

What this slice showed:
- the runtime now carries explicit source-type state instead of relying only on opaque host/title scoring
- this is a cleaner upstream base for later diagnostics and shaping work
- strongest institutional live case remained stable and now visibly reports institutional source typing in readback

Current posture:
- keep downstream selector policy unchanged
- treat current source typing as intentionally shallow but useful early metadata, not final source authority truth
- the next sharp move is validating this metadata through one persisted consumer boundary rather than immediately adding more shaping logic

Verification:
- focused tests passed (`5 passed`)
- live sanity check recorded in `docs/authority-relevance-source-typing-v1-2026-06-28.md`

Best next bounded slice:
- `authority-relevance-source-typing-consumer-validation-v1` — validate one real persisted/readback consumer path for `source_type` before extending shaping further

## 2026-06-28 — SourceTrace v2 authority-relevance-source-typing-consumer-validation-v1 checkpoint

Closed one real downstream consumer validation path for the new `source_type` metadata.

What changed:
- added `docs/authority-relevance-source-typing-consumer-validation-v1-2026-06-28.md`
- added focused persisted/readback coverage in `tests/unit/v2/test_jsonl_storage.py`
- validated that JSONL-backed execution readback / HTTP projection carries `source_type` through to the consumer-facing evidence-input candidate surface

What this slice showed:
- `source_type` is no longer only runtime-local metadata; it now has a validated persisted consumer path
- this is enough to rely on it for future diagnostics/shaping work in bounded form
- current validation intentionally checks presence/transport rather than claiming the shallow classifier is already semantically perfect

Current posture:
- keep selector policy unchanged
- keep source typing shallow but explicit
- the next sharp move is not more validation but using explicit source-type state to make upstream shaping cleaner and less implicit

Verification:
- focused tests passed (`6 passed`)
- details recorded in `docs/authority-relevance-source-typing-consumer-validation-v1-2026-06-28.md`

Best next bounded slice:
- `authority-relevance-source-type-aware-shaping-v1` — use explicit `source_type` state to clean up upstream shaping without changing downstream selector policy in the same slice

## 2026-06-28 — SourceTrace v2 authority-relevance-source-type-aware-shaping-v1 checkpoint

Closed the next bounded upstream shaping cleanup slice.

What changed:
- refactored source-mix shaping in `src/sourcetrace_v2/execution/stages/retrieval.py` to use explicit `source_type` as the primary shaping signal
- retained only a small secondary snippet-presence bump
- preserved bounded fallback behavior: if candidates are still all `unknown`, shaping can still rely on the early annotation pass
- extended focused shaping tests so they explicitly prove `source_type` drives ordering

What this slice showed:
- shaping is now cleaner and easier to reason about because it no longer depends mostly on duplicated implicit host/title scoring during reordering
- this improves maintainability and makes future shaping changes less opaque
- live sanity check on a weak case (`legal hold steps records retention official guidance`) still landed a vendor/vendor pair, which is actually informative: the remaining weakness now points more at candidate-pool composition / classifier granularity than at hidden shaping ambiguity

Current posture:
- keep downstream selector policy unchanged
- the current shaping layer is now cleaner, but weak-topic outcomes still depend heavily on the underlying candidate mix
- the next sharp move is likely improving source typing itself rather than adding more shaping rules on top of shallow source labels

Verification:
- focused tests passed (`5 passed`)
- live sanity check recorded in `docs/authority-relevance-source-type-aware-shaping-v1-2026-06-28.md`

Best next bounded slice:
- `authority-relevance-source-typing-v2` — improve the source classifier itself in a bounded way for observed weak classes while leaving downstream selector policy unchanged

## 2026-06-28 — SourceTrace v2 authority-relevance-query-handoff-contract-v1 checkpoint

Closed the bounded upstream contract defect identified by the live retrieval diagnostics.

What changed:
- added `docs/authority-relevance-query-handoff-contract-v1-2026-06-28.md`
- changed the minimal v2 flow so retrieval input is built from normalized `seed_text`
- stopped passing `query_refinement` freeform prose into the retrieval adapter
- added focused regression coverage for the bounded handoff contract

What this fixes:
- retrieval no longer consumes assistant-style answer prose as `evidence_query` in the minimal v2 flow
- persisted execution readback now reflects the actual bounded seed-derived search intent used for retrieval

Current posture:
- keep downstream authority/relevance selection policy unchanged
- treat this as an upstream handoff repair, not a selector-policy expansion

Verification:
- focused v2 handoff/retrieval tests were updated to pin the new behavior (`5 passed`)
- live smoke on `legal hold steps records retention official guidance` confirmed `evidence_query` now exactly matches the bounded seed query and no longer drifts into assistant-style prose
