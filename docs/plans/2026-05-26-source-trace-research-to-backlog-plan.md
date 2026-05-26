# SourceTrace research-to-backlog plan

Status: staged backlog ready
Scope: convert recent external research signals into a bounded, repo-facing execution backlog for SourceTrace
Purpose: prioritize the smallest high-leverage product/architecture upgrades that improve verification truthfulness, auditability, and analyst utility without reopening broad architecture work

## Goal
Translate validated external research patterns into a staged SourceTrace backlog that can be executed slice-by-slice on top of the current evidence-first, claim-centric baseline.

## Confirmed current state
- SourceTrace already has an evidence-first, claim-centric baseline with local web/API flow, claim extraction, credibility drafting, analyst-facing delivery, and smoke coverage.
- The architecture SSOT already treats contradiction-aware validation, claim-to-evidence provenance, and analyst review as core product concerns.
- The current product baseline still has a gap between retrieval/output availability and explicit evidence sufficiency gating.
- The current repo direction is better aligned with verification workbench patterns than with generic answer-first RAG.
- Existing docs already encode `support`, `contradict`, and `insufficient evidence` as the useful validation triad.
- Current repo state is dirty; this plan should not overwrite or reorganize unrelated in-flight files.

## Decision
Prioritize truthfulness and auditability slices before broader feature expansion.

Operationally, that means:
1. add explicit evidence sufficiency and abstain/publication gating,
2. harden against misleading evidence and weak attribution,
3. improve analyst-facing attribution granularity,
4. only then expand retrieval intelligence such as claim-match retrieval and stronger multilingual paths.

Do not start with larger model changes, graph work, or broad retrieval rewrites. The highest-value gap is decision quality over already-retrieved evidence.

## Research signals translated into product direction

### 1. Evidence sufficiency is distinct from retrieval relevance
Primary external signal:
- `SURE-RAG` (2026)

Implication for SourceTrace:
- Retrieval hit quality and evidence sufficiency must be modeled separately.
- A claim/report path needs an explicit sufficiency decision, not only evidence presence.

Backlog consequence:
- add `evidence_sufficiency` style contract and gating before stronger report publication.

### 2. Correct abstention is a product feature, not a fallback accident
Primary external signals:
- `GaRAGe` (2025)
- `SURE-RAG` (2026)

Implication for SourceTrace:
- When grounding is insufficient or conflicting, the system should explicitly refuse stronger publication states.

Backlog consequence:
- add `publication_gate` / `reason_not_publishable` style output to report and verification surfaces.

### 3. Citation quality is richer than support/not-support
Primary external signals:
- `CiteEval` (2025)
- `Correctness is not Faithfulness in RAG Attributions` (2025)

Implication for SourceTrace:
- claim/report citations should carry issue flags such as missing better evidence, redundant evidence, misleading evidence, or non-retrieval-attributable statements.

Backlog consequence:
- add citation-quality diagnostics instead of treating any attached citation as enough.

### 4. Fine-grained attribution reduces analyst load
Primary external signals:
- `RECLAIM` (2025)
- `SAFE` (2025)

Implication for SourceTrace:
- analyst-facing surfaces should expose the best evidence snippets/spans per claim, not only chunk/document references.

Backlog consequence:
- prioritize claim-level best-snippet rendering before broader UI work.

### 5. Misleading retrieval is a first-class failure mode
Primary external signal:
- `RAGUARD` (2025)

Implication for SourceTrace:
- test/eval should include actively misleading and conflicting evidence, not only empty or supportive evidence.

Backlog consequence:
- add robustness fixtures and expected downgrade behavior.

### 6. Previously fact-checked claim retrieval is a practical accelerator
Primary external signal:
- `SemEval-2025 Task 7: Multilingual and Crosslingual Fact-Checked Claim Retrieval`

Implication for SourceTrace:
- matching new claims to prior verified claims/cases can shorten analyst work and reduce duplicate verification effort.

Backlog consequence:
- add a bounded claim-match retrieval slice after gating and attribution basics are in place.

### 7. Multilingual and numeric claims deserve explicit contracts
Primary external signals:
- `SemEval-2025 Task 7`
- `CheckThat! 2025` numerical-claim verification

Implication for SourceTrace:
- cross-language normalization drift and numeric/temporal claim handling should be visible in contracts/tests rather than left implicit.

Backlog consequence:
- add risk flags and targeted tests before larger multilingual retrieval ambitions.

## Staged backlog

## Stage 1 — verification truthfulness gates
Purpose: stop overclaiming when evidence is weak, partial, or conflicting

### Slice 1.1 — evidence sufficiency contract v1
Purpose:
- add an explicit sufficiency decision between evidence retrieval/presence and stronger verification/report usage

Primary files:
- `src/sourcetrace/application/`
- `src/sourcetrace/domain/`
- `src/sourcetrace/web/api.py`
- `tests/unit/application/`
- `tests/unit/web/`

Proposed contract shape:
- `evidence_sufficiency`: `supported | refuted | insufficient`
- optional diagnostics:
  - `support_signals_present`
  - `conflict_signals_present`
  - `evidence_count`
  - `sufficiency_summary`

Minimum implementation rule:
- start rule-based using existing evidence links / verdict state / missing-evidence conditions
- do not wait for a new NLI component

Validation:
- `PYTHONPATH=src pytest -q`

Done condition:
- at least one verification or report-facing path returns a stable sufficiency decision with tests covering supported / refuted / insufficient branches

### Slice 1.2 — publication gate / abstain contract v1
Purpose:
- make stronger report inclusion conditional on sufficiency, conflict state, and weak-source conditions

Primary files:
- `src/sourcetrace/application/`
- `src/sourcetrace/web/`
- `tests/unit/application/`
- `tests/unit/web/`

Proposed contract shape:
- `publication_gate`: `allowed | blocked | review_required`
- `gate_reason` values such as:
  - `grounding_insufficient`
  - `conflicting_evidence`
  - `weak_source_only`
  - `no_verified_support`

Validation:
- `PYTHONPATH=src pytest -q`

Done condition:
- report or verification outputs explicitly expose whether stronger publication is allowed

## Stage 2 — attribution quality and analyst review signal
Purpose: improve auditability and reduce analyst verification load

### Slice 2.1 — citation quality flags v1
Purpose:
- expose whether the attached evidence is merely present or actually good enough

Primary files:
- `src/sourcetrace/domain/`
- `src/sourcetrace/application/`
- `src/sourcetrace/web/`
- `tests/unit/`

Proposed flags:
- `missing_best_evidence`
- `redundant_citation`
- `misleading_citation`
- `non_retrieval_attributable`
- `weak_source_only`

Minimum implementation rule:
- start with deterministic diagnostics from current evidence/citation selection paths
- no model-based citation judge in v1

Validation:
- `PYTHONPATH=src pytest -q`

Done condition:
- claim/report payloads can signal `citation_ok` vs `citation_needs_review` and provide issue codes

### Slice 2.2 — best-evidence snippet rendering
Purpose:
- render 1–2 best snippets/spans per claim in analyst-facing surfaces

Primary files:
- `src/sourcetrace/web/api.py`
- HTML rendering helpers/templates if present
- `tests/unit/web/`

Minimum implementation rule:
- reuse existing chunk/snippet data
- no ranking overhaul in this slice

Validation:
- `PYTHONPATH=src pytest -q`

Done condition:
- claim/case/report HTML or JSON exposes compact best-evidence snippets tied to the claim

## Stage 3 — robustness against misleading evidence
Purpose: verify the system downgrades correctly under adversarial or low-quality retrieval conditions

### Slice 3.1 — misleading-evidence fixture pack
Purpose:
- extend test/eval fixtures with supporting, conflicting, misleading, and unrelated evidence cases

Primary files:
- `tests/fixtures/`
- `tests/unit/application/`
- `tests/unit/web/`
- optional smoke helpers under `src/sourcetrace/*smoke*.py`

Minimum fixture set:
- one supportive case
- one conflicting case
- one misleading-but-topically-related case
- one unrelated case

Validation:
- `PYTHONPATH=src pytest -q`

Done condition:
- tests assert downgrade behavior rather than accidental strong verdicts in misleading cases

### Slice 3.2 — robustness smoke summary
Purpose:
- provide a small smoke-style summary showing how the system classified/support-gated each evidence condition

Primary files:
- `src/sourcetrace/*smoke*.py`
- `tests/unit/`

Validation:
- `PYTHONPATH=src pytest -q`

Done condition:
- a bounded smoke command or test helper reports sufficiency/gate behavior across the small robustness pack

## Stage 4 — retrieval acceleration for analysts
Purpose: reduce duplicate analyst work before broader retrieval modernization

### Slice 4.1 — previously fact-checked claim matching v1
Purpose:
- retrieve similar previously verified claims/case artifacts for a new claim

Primary files:
- `src/sourcetrace/pipeline/`
- `src/sourcetrace/storage/`
- `src/sourcetrace/application/`
- `tests/unit/`

Minimum implementation rule:
- start with lexical / normalized-text baseline
- keep it local to existing SourceTrace claims/cases
- no web-scale multilingual retriever in v1

Validation:
- `PYTHONPATH=src pytest -q`

Done condition:
- given a new claim, the system can return a small ranked list of similar existing verified claims/cases

## Stage 5 — multilingual and claim-type risk hardening
Purpose: expose semantically risky cases before claiming broader multilingual readiness

### Slice 5.1 — cross-language normalization risk flags
Purpose:
- preserve meaning and show where normalization may have drifted

Primary files:
- `src/sourcetrace/application/`
- `src/sourcetrace/llm/`
- `tests/unit/application/`

Proposed fields:
- `source_language`
- `normalized_language`
- `crosslingual_risk_flags`
- `meaning_preservation_notes`

Validation:
- `PYTHONPATH=src pytest -q`

Done condition:
- PL/EN style normalization cases have explicit tests and visible risk signaling

### Slice 5.2 — numeric/temporal claim typing
Purpose:
- distinguish claims needing stricter quantity/time review

Primary files:
- `src/sourcetrace/domain/`
- `src/sourcetrace/application/`
- `tests/unit/`

Proposed fields:
- `claim_type`: `generic | numeric | temporal | comparative`

Validation:
- `PYTHONPATH=src pytest -q`

Done condition:
- numeric/temporal/comparative claims are tagged and can trigger stricter review templates later

## Priority order
1. `evidence sufficiency contract v1`
2. `publication gate / abstain contract v1`
3. `misleading-evidence fixture pack`
4. `citation quality flags v1`
5. `best-evidence snippet rendering`
6. `previously fact-checked claim matching v1`
7. `cross-language normalization risk flags`
8. `numeric/temporal claim typing`

## Standard validation loop
For each slice:
1. implement the smallest contract change,
2. add bounded unit tests first or together with the change,
3. run:
   - `PYTHONPATH=src pytest -q`
4. if the slice touches a hotspot route, add one focused local smoke or route-level test,
5. sync docs only after the behavior is verified.

## Risks and stop conditions
- Do not mix this backlog with broad refactors while the working tree is already dirty and unrelated slices are in flight.
- Do not introduce a larger NLI/model dependency before the contract and diagnostics shape is proven useful with rule-based logic.
- Do not broaden into graph retrieval, agentic orchestration, or heavy reranking before sufficiency/gating is explicit.
- Stop a slice if it requires rewriting multiple layers at once; split the contract first and postpone smarter ranking/scoring.
- Treat multilingual and citation-faithfulness claims beyond current deterministic checks as do weryfikacji until backed by tests or live eval.

## Recommended next execution slice
Start with `verification_sufficiency_contract_v1`.

Why this first:
- it closes the highest-value trust gap,
- it aligns with the existing `support / contradict / insufficient evidence` direction already present in SourceTrace docs,
- it enables the later publication gate, robustness pack, and citation-quality slices without committing to a heavier model path.

## Definition of Done for this plan
This plan is complete when:
- the repo has one agreed staged backlog artifact for research-to-backlog translation,
- the first execution slice is explicit and bounded,
- future slice work can proceed without reopening broad external discovery.
