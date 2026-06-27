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
