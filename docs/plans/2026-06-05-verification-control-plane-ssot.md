# SourceTrace verification control plane SSOT

Status: active execution SSOT
Date: 2026-06-05
Scope: canonical execution plan for shifting SourceTrace toward a verification-first control plane with explicit sufficiency, publication gating, auditability, and bounded robustness/economics instrumentation

Related docs:
- `docs/architecture/architecture-ssot.md`
- `docs/research/research-ledger.md`
- `docs/plans/2026-05-26-source-trace-research-to-backlog-plan.md`
- `docs/plans/local-launcher-readiness-ssot.md`

## Goal
Turn SourceTrace into a trustworthy verification system that can explicitly decide whether evidence is sufficient, whether a stronger publication state is allowed, what evidence supports the verdict, and when analyst review is required.

## Product decision
Treat SourceTrace as a **verification control plane**, not as a generic agent runtime or answer engine.

Operationally this means:
1. truthfulness gates before broader feature expansion,
2. auditability and analyst-facing evidence clarity before retrieval acceleration,
3. robustness and cost-of-failure visibility before broader scope expansion,
4. defer MCP / multi-agent / graph-heavy work unless later evidence changes the priority.

## Confirmed current state
- SourceTrace already has claim-centric verification seams, evidence links, analyst review structures, and report assembly paths.
- The repo already exposes `evidence_sufficiency`, `publication_gate`, and `gate_reason` on verification/report-facing paths.
- Current verification controls appear rule-based and verdict-driven; broader diagnostic richness from the staged backlog may still be missing.
- Slice 1.1 is now implemented: verification/report payloads also expose `support_signals_present`, `conflict_signals_present`, `evidence_count`, and `sufficiency_summary`.
- Focused verification passed: `PYTHONPATH=src pytest -q tests/unit/pipeline/test_verification_runtime.py tests/unit/web/test_web_delivery.py tests/unit/application/test_verification.py` -> `36 passed`.
- Full repo verification passed after the slice: `PYTHONPATH=src pytest -q` -> `346 passed in 0.28s`.
- The existing staged backlog in `docs/plans/2026-05-26-source-trace-research-to-backlog-plan.md` remains directionally correct and aligned with current daily AI/runtime signals.
- The working tree was clean at the start of this plan activation.

## Main gap
The first planned slice is no longer “add sufficiency/gate fields” — those exist already.
The real current gap is to **harden the control-plane contract with richer diagnostics and explicit operator visibility**, then verify the behavior with bounded tests and smoke summaries.

## Execution rules
- Keep slices bounded and contract-first.
- Prefer deterministic/rule-based logic before introducing heavier model-side judging.
- Update this SSOT after each meaningful slice with: what changed, what was verified, blockers, and the next smallest slice.
- Record uncertainties explicitly under `Do weryfikacji` instead of masking them as closure.
- Do not broaden into major retrieval/runtime/platform work while this control-plane hardening plan is active.

## Staged plan

### Stage 1 — control-plane contract hardening
Purpose: make verification decisions more explicit, inspectable, and testable.

#### Slice 1.1 — verification diagnostics contract v1
Status: completed
Purpose:
- extend the existing sufficiency/gate contract with bounded diagnostics so operators can see *why* a claim landed in a given state.

Delivered:
- verification/report payloads now expose:
  - `support_signals_present`
  - `conflict_signals_present`
  - `evidence_count`
  - `sufficiency_summary`
- pipeline/runtime outcomes now carry the same diagnostics on `ClaimVerificationOutcome`
- tests were added for supported / insufficient / refuted paths and verification/report payload serialization

Expected files:
- `src/sourcetrace/application/verification.py`
- `src/sourcetrace/pipeline/verification.py`
- `src/sourcetrace/web/delivery.py`
- `tests/unit/application/`
- `tests/unit/web/`
- optionally `tests/unit/pipeline/`

Verification:
- `PYTHONPATH=src pytest -q tests/unit/pipeline/test_verification_runtime.py tests/unit/web/test_web_delivery.py tests/unit/application/test_verification.py` -> `36 passed`
- `PYTHONPATH=src pytest -q` -> `346 passed`

Done condition:
- verification-facing payloads expose the bounded diagnostics above,
- tests cover supported / refuted / insufficient paths,
- this SSOT is updated with the verified result.

#### Slice 1.2 — gate-aware operator surfaces
Status: completed
Purpose:
- ensure report/API/HTML surfaces make the gate status and reason obvious enough for an analyst/operator.

Delivered:
- markdown report entries now expose:
  - `Support signals present`
  - `Conflict signals present`
  - `Evidence count`
  - `Sufficiency summary`
- case HTML claim rows now expose the same diagnostics alongside:
  - `Evidence sufficiency`
  - `Publication gate`
  - `Gate reason`
- duplicated sufficiency-summary logic was consolidated behind `_verification_sufficiency_summary(...)` so JSON / markdown / HTML surfaces stay aligned.

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py tests/unit/pipeline/test_verification_runtime.py tests/unit/application/test_verification.py` -> `73 passed`
- `PYTHONPATH=src pytest -q` -> `346 passed`

Done condition:
- operator-facing markdown and case HTML surfaces expose gate-aware diagnostics clearly enough to inspect support/conflict/evidence volume without opening raw JSON,
- tests cover the new markdown and HTML rendering expectations,
- this SSOT is updated with the verified result.

#### Slice 1.3 — reason-coded smoke summary
Status: completed
Purpose:
- provide a small smoke helper/report that summarizes verification outcomes by gate/sufficiency category.

Delivered:
- case report JSON now exposes `verification_summary` with deterministic aggregate counts for:
  - `publication_summary`
  - `evidence_sufficiency`
  - `publication_gate`
  - `gate_reason`
- markdown report now renders a compact `Verification summary` block with aggregate smoke counts.
- case HTML now renders the same summary block above the case continuity/operator sections.
- aggregation stayed within existing report/case surfaces; no new endpoint or runtime surface was added.

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py tests/unit/pipeline/test_verification_runtime.py tests/unit/application/test_verification.py` -> `73 passed`
- `PYTHONPATH=src pytest -q` -> `346 passed`

Done condition:
- operator-facing surfaces expose a compact aggregate smoke summary for verification outcomes,
- excluded claims still count as blocked in report-level summaries without forcing excluded per-claim lines into markdown,
- this SSOT is updated with the verified result.

### Stage 2 — attribution quality and analyst utility
Purpose: reduce analyst load and improve confidence in attached evidence.

#### Slice 2.1 — citation quality flags v1
Status: completed
Delivered flags:
- `missing_best_evidence` *(implemented only when evidence-link context is actually available)*
- `redundant_citation`
- `non_retrieval_attributable`

Deferred:
- `misleading_citation`
- `weak_source_only`

Delivered:
- verification payloads now expose `citation_quality_flags`
- verification inspection payloads pass persisted `evidence_links` into citation-flag evaluation
- report entry payloads also expose `citation_quality_flags`, but intentionally stay conservative when evidence-link context is absent
- v1 logic is deterministic and bounded:
  - `missing_best_evidence` when retrieved support/conflict exists and explicit evidence-link context shows no citations,
  - `non_retrieval_attributable` when citations exist but no retrieval support/conflict exists,
  - `redundant_citation` when the same chunk is cited more than once in provided evidence links
- tests cover no-guess behavior without evidence-link context plus positive flagging for non-retrieval and redundant citation cases

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py tests/unit/pipeline/test_verification_runtime.py tests/unit/application/test_verification.py` -> `75 passed`
- `PYTHONPATH=src pytest -q` -> `348 passed`

Done condition:
- citation quality flags are exposed on bounded analyst-facing payloads,
- flagging remains deterministic and does not guess when required context is absent,
- this SSOT is updated with the verified result.

#### Slice 2.2 — best-evidence snippet rendering
Status: completed
Purpose:
- expose 1–2 best snippets/spans per claim in analyst-facing payloads/surfaces.

Delivered:
- verification inspection payloads now expose `best_evidence`
- `best_evidence` is a deterministic top-2 subset of existing `evidence_links`
- ordering is rule-based by `evidence_rank` first (with score as a tie-break helper)
- each best-evidence item currently reuses the existing evidence-link payload contract:
  - `chunk_id`
  - `evidence_rank`
  - `evidence_verdict`
  - `snippet`
  - `rationale`
  - `score`
- markdown report entries now expose a bounded `Best evidence chunks` line derived from the currently available report-entry contract
  - this uses top supporting chunk ids first, then contradicting chunk ids when support is absent
  - no live evidence-link lookup or snippet hydration was added to report assembly in this slice
- case HTML claim rows now expose `Best evidence: ...` based on the existing claim-level `links`
  - this uses the same top-2 evidence selection logic as inspection payloads
  - HTML renders snippet text when already present on the evidence links without changing application/report contracts

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py` -> `62 passed`
- `PYTHONPATH=src pytest -q` -> `349 passed`

Done condition:
- best-evidence hints are now visible across inspection payloads, markdown reports, and case HTML,
- all additions stayed within existing delivery/report surfaces,
- this SSOT is updated with the verified result.

#### Slice 2.3 — compact claim trace summary
Status: completed
Purpose:
- expose a small per-claim audit packet: verdict, sufficiency, gate, top evidence, issue flags, review note.

Delivered:
- `verification_inspection_to_payload(...)` now includes `claim_trace_summary`
- `claim_trace_summary` is a compact inspection-only packet assembled from existing verification + review + best-evidence data
- fields included:
  - `final_verdict`
  - `evidence_sufficiency`
  - `publication_gate`
  - `gate_reason`
  - `sufficiency_summary`
  - `citation_quality_flags`
  - `best_evidence`
  - `review_note`
- no new heuristics or endpoints were added
- no markdown/HTML projection was added in this slice; this remains payload-first by design

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py` -> `25 passed`
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py tests/unit/pipeline/test_verification_runtime.py tests/unit/application/test_verification.py` -> `76 passed`
- `PYTHONPATH=src pytest -q` -> `349 passed`

Done condition:
- operator-facing inspection payload now exposes one compact per-claim audit packet,
- the packet reuses already-verified Stage 1/2 fields instead of adding new runtime behavior,
- this SSOT is updated with the verified result.

### Stage 3 — robustness and failure-mode coverage
Purpose: prove the system downgrades correctly under weak/conflicting/misleading evidence.

#### Slice 3.1 — misleading-evidence fixture pack
Status: completed
Minimum fixture set:
- supportive
- conflicting
- misleading-but-related
- unrelated

Delivered:
- added a bounded robustness fixture pack in `tests/unit/pipeline/test_verification_runtime.py`
- fixture coverage now explicitly includes four named baseline scenarios:
  - supportive evidence baseline
  - conflicting evidence baseline
  - misleading-but-related lexical-hit baseline
  - unrelated lexical-hit baseline
- the new tests intentionally record current runtime behavior rather than inventing new heuristics early
- important finding captured by the fixture pack:
  - with the current lexical retriever + evidence-presence verifier, both `misleading-but-related` and `unrelated` can still become support/allowed baselines because weak lexical overlap produces hits
  - this is now encoded as verified baseline risk for Stage 3.2/3.3 instead of being hidden behind assumptions

Verification:
- `PYTHONPATH=src pytest -q tests/unit/pipeline/test_verification_runtime.py` -> `11 passed`
- `PYTHONPATH=src pytest -q` -> `353 passed`

Done condition:
- the minimum robustness fixture set exists and is executable,
- current failure-mode baselines are explicit and regression-testable,
- this SSOT is updated with the verified result.

#### Slice 3.2 — robustness smoke summary
Status: completed
Purpose:
- show how SourceTrace classifies/support-gates each evidence condition on the bounded fixture pack.

Delivered:
- added `_robustness_smoke_row(...)` in `tests/unit/pipeline/test_verification_runtime.py`
- added `_build_baseline_runtime(...)` helper to run bounded lexical baseline fixtures with real pipeline execution
- added one smoke-summary test that executes the 3.1 fixture pack baselines and aggregates the resulting control-plane signals into a compact per-scenario map:
  - `verdict`
  - `evidence_sufficiency`
  - `publication_gate`
  - `gate_reason`
- the smoke summary now verifies the current baseline readout end-to-end instead of relying on static literals or stub objects

Verified baseline summary:
- `supportive` -> `support / supported / allowed / none`
- `unrelated` -> `support / supported / allowed / none`
- `misleading_related` -> `support / supported / allowed / none`
- `conflicting` -> `contradict / refuted / review_required / conflicting_evidence`

Verification:
- `PYTHONPATH=src pytest -q tests/unit/pipeline/test_verification_runtime.py` -> `12 passed`
- `PYTHONPATH=src pytest -q` -> `354 passed`

Done condition:
- the fixture pack from Slice 3.1 now has one compact, executable robustness summary,
- current failure-mode baselines are operator-readable in one place,
- this SSOT is updated with the verified result.

#### Slice 3.3 — overclaiming regression harness
Status: completed
Purpose:
- prevent regressions where weak evidence accidentally produces strong claims/publication states.

Delivered:
- added two bounded regression-guard tests in `tests/unit/pipeline/test_verification_runtime.py` for the known overclaiming baselines:
  - `unrelated`
  - `misleading_related`
- both tests are marked `pytest.mark.xfail(strict=True)` because current runtime behavior still overclaims on weak lexical hits
- each guard encodes the target policy in the smallest useful form:
  - these fixtures should **not** end with `publication_gate == "allowed"`
- this creates a real upgrade path for a future runtime fix: once the behavior is hardened, the xfails can be flipped to normal passing guards without changing the contract of the tests

Verification:
- `PYTHONPATH=src pytest -q tests/unit/pipeline/test_verification_runtime.py` -> `12 passed, 2 xfailed`
- `PYTHONPATH=src pytest -q` -> `354 passed, 2 xfailed`

Done condition:
- known overclaiming baselines are explicitly guarded,
- the current broken behavior is tracked without pretending it is already fixed,
- this SSOT is updated with the verified result.

### Stage 4 — observability and economics
Purpose: measure SourceTrace as a verification execution system.

#### Slice 4.1 — trace-based verification log v1
Status: completed
Purpose:
- capture which evidence was considered, selected, rejected, and how the gate/verdict was decided.

Delivered:
- added `verification_trace_log` to `verification_inspection_to_payload(...)`
- added bounded helper `_verification_trace_log_payload(inspection)`
- the new trace log is inspection-payload-only and reuses existing verification/review/evidence data; no new endpoint or persistence surface was added
- v1 structure:
  - `retrieval_trace`
    - `query_text`
    - `considered_chunks` (chunk/document/rank/verdict/score)
    - `selected_supporting_chunks`
    - `selected_contradicting_chunks`
  - `decision_trace`
    - `verdict`
    - `evidence_sufficiency`
    - `publication_gate`
    - `gate_reason`
    - `sufficiency_summary`
  - `review_trace`
    - `has_review`
    - `review_status`
    - `review_verdict`
    - `review_notes`
- note: v1 does not yet distinguish explicit `rejected_chunks`; it captures `considered` and `selected` from currently available data

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py` -> `62 passed`
- `PYTHONPATH=src pytest -q` -> `354 passed, 2 xfailed`

Done condition:
- inspection payload now exposes a compact, auditable verification trace,
- the trace is built only from existing deterministic data,
- this SSOT is updated with the verified result.

#### Slice 4.2 — cost-of-failure metrics v1
Status: completed (payload-first)
Candidate metrics:
- `claim_count`
- `evidence_count`
- `claims_review_required`
- `claims_insufficient`
- `publication_block_rate`

Delivered:
- added `cost_of_failure_metrics` to `report_outcome_to_payload(...)` under `case_report`
- added bounded helper `_report_cost_of_failure_metrics(entries, review_decisions)`
- v1 is deterministic and derived only from existing report entries / verification summary; no runtime timing or external cost instrumentation was added
- current v1 intentionally does **not** include `candidate_count` or execution time because those are not yet present in the report contract

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py` -> `62 passed`
- `PYTHONPATH=src pytest -q` -> `354 passed, 2 xfailed`

Done condition:
- case report JSON now exposes a compact cost-of-failure metric block,
- metrics are deterministic and bounded to current contract data,
- this SSOT is updated with the verified result.

#### Slice 4.3 — review queue signals
Status: completed (payload-first)
Purpose:
- expose reason-coded review buckets for analyst operations.

Delivered:
- added `review_queue_signals` to `report_outcome_to_payload(...)` under `case_report`
- added bounded helper `_report_review_queue_signals(entries, review_decisions)`
- v1 exposes:
  - `review_required_claim_count`
  - `reason_buckets`
  - `priority_buckets`
- queue counts include only claims whose computed `publication_gate` is `review_required`
- excluded claims are intentionally omitted from the review queue
- v1 priority policy is deterministic and minimal:
  - `conflicting_evidence` -> `high`
  - all other review-required reasons -> `normal`
- important finding: the current report-level baseline maps an unreviewed `INSUFFICIENT_EVIDENCE` entry to `no_verified_support`, not `grounding_insufficient`

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py` -> `63 passed`
- `PYTHONPATH=src pytest -q` -> `355 passed, 2 xfailed`

Done condition:
- case report JSON now exposes review-queue buckets operators can act on,
- signals are deterministic and bounded to current gate semantics,
- this SSOT is updated with the verified result.

### Stage 5 — acceleration after trust-layer hardening
Purpose: reduce analyst duplication and widen scope only after control-plane behavior is solid.

#### Slice 5.1 — previously fact-checked claim matching v1
Status: completed (inspection-payload-first)

Delivered:
- added `previously_fact_checked_matches` to `VerificationInspection`
- added `previously_fact_checked_matches` to `verification_inspection_to_payload(...)`
- added bounded helpers:
  - `_normalize_claim_match_text(text)`
  - `_previously_fact_checked_matches(persistence, claim)`
- v1 matching policy is intentionally minimal and deterministic:
  - same-case only
  - exact-text match after casefold + whitespace collapse + diacritic stripping
  - exclude the current claim id
  - include only candidates with persisted review or verification state
- v1 match payload fields:
  - `claim_id`
  - `case_id`
  - `exact_text`
  - `human_review_status`
  - `final_verdict`

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py` -> `64 passed`
- `PYTHONPATH=src pytest -q` -> `356 passed, 2 xfailed`

Done condition:
- inspection payload now exposes a bounded reuse signal for previously fact-checked claims,
- matching is deterministic and clearly weaker than semantic dedupe,
- this SSOT is updated with the verified result.

#### Slice 5.2 — cross-language normalization risk flags
Status: completed (inspection-payload-first)

Delivered:
- extended `previously_fact_checked_matches` with `normalization_risk_flags`
- added bounded helper `_claim_match_risk_flags(source_text, candidate_text)`
- v1 flags are deterministic and explain why a match required normalization:
  - `casefold_only_match`
  - `whitespace_normalized_match`
  - `diacritic_stripped_match`
- exact-text matches continue to emit an empty risk-flag list
- this slice does not widen matching semantics; it only makes normalization ambiguity visible

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py` -> `65 passed`
- `PYTHONPATH=src pytest -q` -> `357 passed, 2 xfailed`

Done condition:
- inspection payload now shows when a reuse match depends on text normalization,
- operators can distinguish exact reuse from normalization-assisted reuse,
- this SSOT is updated with the verified result.

#### Slice 5.3 — numeric/temporal claim typing
Status: completed (inspection-payload-first)

Delivered:
- extended `previously_fact_checked_matches` with `claim_type_signals`
- added bounded helper `_claim_type_signals(text)`
- v1 signals are heuristic and deterministic:
  - `numeric_claim`
  - `temporal_claim`
- numeric detection covers explicit numerals, percentages, decimal forms, and small ordinal words
- temporal detection covers years, month names, and explicit date-like forms
- this slice does not change matching semantics; it adds operator-visible type warnings for reuse review

Verification:
- `PYTHONPATH=src pytest -q tests/unit/web/test_web_delivery.py tests/unit/web/test_full_api_routes.py` -> `66 passed`
- `PYTHONPATH=src pytest -q` -> `358 passed, 2 xfailed`

Done condition:
- inspection payload now marks matches that carry numeric/temporal comparison risk,
- operators can distinguish plain textual reuse from claims needing stricter numeric/time-aware review,
- this SSOT is updated with the verified result.

## Current blockers
- None confirmed for Stage 5.3 closure.

## Current doubts / do weryfikacji
- Whether `sufficiency_summary` should remain a lightweight deterministic string or evolve into a richer reason-coded summary object in a later slice.
- Whether report assembly should later be expanded to carry hydrated snippet/span data instead of chunk-id-only markdown hints.
- Whether `best_evidence` should keep reusing the evidence-link payload shape or become a smaller dedicated snippet/span contract before later robustness/operator slices.
- Whether the first runtime hardening slice should target lexical retrieval filtering, verifier semantics, or a deterministic publication-gate clamp for weak-evidence cases.
- Whether a later trace-log slice should add explicit `rejected_chunks` / `dropped_candidates` once the runtime tracks them natively.
- Whether `cost_of_failure_metrics` should later expand to include `candidate_count` or wall-clock/runtime cost once those values exist in the report contract.
- Whether review-queue priority should later grow beyond `high|normal` once more reason codes or SLAs exist.
- Whether previously fact-checked matching should later expand beyond same-case exact-text normalization into cross-case or semantic reuse.
- Whether normalization risk flags should later include script-mixing/transliteration instead of today’s bounded diacritic-only signal.
- Whether claim typing should later add currencies, ranges, comparative operators, and stronger date parsing instead of today’s regex heuristic.

## Standard validation loop
For each slice:
1. change the smallest viable contract,
2. add bounded tests first or together with the change,
3. run the narrowest relevant tests,
4. run `PYTHONPATH=src pytest -q` before declaring slice closure,
5. update this SSOT with what changed / verified / blocked / next slice.

## Current recommended next execution slice
Completed **Slice 14.1 — continuity-pack case-page microcopy review for empty/replace warnings and next-step language**.
Status: completed (case-page continuity microcopy cleanup for status/warnings/next step)

Delivered:
- reviewed case-page continuity microcopy and confirmed remaining drift in three places:
  - empty-state sentence
  - next-step instruction wording
  - replace warning sentence
- normalized empty-state copy from a generic prose sentence to explicit operator status language:
  - `Status: No active continuity pack is assigned.`
- normalized next-step copy to a clearer operator instruction:
  - `Next step: Assign a continuity pack from docs/plans/... via POST /api/cases/{case_id}/continuity-pack.`
- normalized replace warning wording to a shorter, clearer note:
  - `Replace note: Assigning a new continuity pack replaces the current active continuity pack for this case.`
- also aligned the cleared/history fallback status copy to the same status sentence
- kept structure, links, and behavior unchanged; this was microcopy-only cleanup
- kept scope bounded to case-page microcopy only:
  - no JSON changes
  - no markdown changes
  - no runtime/assembly changes
  - no action/link behavior changes

Verified:
- empty case page now shows explicit status + next-step guidance instead of the older prose-only empty-state sentence
- active case page now shows normalized replace-note copy
- cleared/history case page now reuses the same normalized no-active status wording
- existing continuity page links/actions and URLs remain unchanged
- `PYTHONPATH=src pytest -q tests/unit/web/test_full_api_routes.py tests/unit/web/test_web_delivery.py tests/unit/pipeline/test_verification_runtime.py tests/unit/test_readme_examples.py` → `95 passed`
- `PYTHONPATH=src pytest -q` → `374 passed`

What this closes:
- the main case-page continuity microcopy now reads in one operator style across empty, active, and cleared/history states
- remaining continuity UI work has moved decisively from parity gaps to optional polish
- the continuity-pack operator surface is now cohesive enough to stop without functional loss

Recommended next slice:
- **Parking candidate** — no mandatory next slice; only optional polish remains unless product wants another operator-copy pass

Why this next:
- data contracts, read-model parity, HTML parity, and microcopy normalization are all in a good state
- additional work here is now discretionary polish, not a clear product or operator gap
