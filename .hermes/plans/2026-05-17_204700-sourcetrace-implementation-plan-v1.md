# SourceTrace MVP v1 Implementation Plan

> **For Hermes:** Use bounded execution slices. Do not widen scope beyond the listed files without first patching SSOT/blueprint.

**Goal:** Move SourceTrace from research-only docs into a first implementation-ready MVP foundation centered on claim-level verification, advisory OSINT-style credibility metadata, and analyst review contracts.

**Architecture:** Start with import-safe domain/application contracts and contract tests before any real web/runtime wiring. Build from inside out: domain models and enums, then application services and in-memory repositories, then a minimal API/read-model surface, then reporting/export seams.

**Tech Stack:** Python, pytest, standard library dataclasses/typing, lightweight in-memory adapters first, later FastAPI or equivalent only after contracts stabilize.

---

## Planning mode scope
This file is the execution-ready checklist. It does **not** itself start implementation. Current repo docs remain the canonical research SSOT. When execution begins, implement slices in order and verify after each slice.

## Confirmed baseline
- Repo path: `/home/voytas/projects/sourcetrace`
- Current docs SSOT: `docs/architecture/architecture-ssot.md`
- Current blueprint: `docs/plans/execution-blueprint-v0.md`
- Current research ledger: `docs/research/research-ledger.md`
- Current code: package skeleton only under `src/sourcetrace/`
- Current tests: package-layout smoke only

## Implementation principles for v1
- Keep `system verdict`, `human review status`, and analyst disposition separate.
- Keep `source_reliability` and `information_credibility` advisory only.
- Prefer dataclasses + simple protocols over framework-heavy abstractions.
- Use in-memory adapters first to freeze contracts before DB/web work.
- Each slice must add or update tests before broadening runtime behavior.

---

## Slice 1: Freeze domain language and status contracts

### Task 1.1: Add domain enums for verification and review states
**Objective:** Create one canonical source of truth for statuses used across the app.

**Files:**
- Create: `src/sourcetrace/domain/types.py`
- Create: `tests/unit/domain/test_types.py`

**Steps:**
1. Write failing tests for expected enums and values.
2. Add enums for:
   - `VerificationVerdict`: `support`, `contradict`, `insufficient_evidence`
   - `HumanReviewStatus`: `unreviewed`, `reviewed_accept`, `reviewed_override`, `needs_followup`, `excluded`, `escalated`
   - `AnalystDisposition`: `confirmed_support`, `confirmed_contradiction`, `insufficient_evidence`, `needs_more_collection`, `exclude_from_report`
   - `QueueStatus`: `new`, `triaged`, `in_review`, `on_hold`, `resolved`, `escalated`
3. Run focused tests.
4. Commit.

### Task 1.2: Add credibility factor enums and OSINT naming
**Objective:** Freeze credibility vocabulary before model creation.

**Files:**
- Modify: `src/sourcetrace/domain/types.py`
- Create: `tests/unit/domain/test_credibility_types.py`

**Steps:**
1. Write failing tests for credibility bands and provenance distance.
2. Add enums for:
   - `CredibilityBand`: `high`, `medium`, `low`, `unknown`
   - `ProvenanceDistance`: `primary`, `near_primary`, `secondary`, `unknown`
3. Add tests that confirm OSINT naming stays `source_reliability` / `information_credibility` in any exported field constants if constants are added.
4. Run focused tests.
5. Commit.

### Task 1.3: Export domain types cleanly
**Objective:** Make domain contracts importable from one place.

**Files:**
- Modify: `src/sourcetrace/domain/__init__.py`
- Test: `tests/unit/domain/test_types.py`

**Steps:**
1. Write/extend test for `from sourcetrace.domain import ...` imports.
2. Re-export the new enums.
3. Run focused tests.
4. Commit.

---

## Slice 2: Create core domain records

### Task 2.1: Add document and credibility assessment records
**Objective:** Represent raw documents plus advisory credibility metadata.

**Files:**
- Create: `src/sourcetrace/domain/documents.py`
- Create: `tests/unit/domain/test_documents.py`

**Steps:**
1. Write failing tests for `Document` and `DocumentCredibilityAssessment` dataclasses.
2. Implement dataclasses with minimal fields:
   - `Document`: ids, source type, source url, publisher, author, title, published_at, retrieved_at, content_hash, language
   - `DocumentCredibilityAssessment`: `source_reliability`, `information_credibility`, factor fields, method, notes, assessed_by, assessed_at, override
3. Add simple validation in `__post_init__` only when clearly necessary.
4. Run focused tests.
5. Commit.

### Task 2.2: Add claim and claim-evidence records
**Objective:** Represent the core verification unit.

**Files:**
- Create: `src/sourcetrace/domain/claims.py`
- Create: `tests/unit/domain/test_claims.py`

**Steps:**
1. Write failing tests for `Claim` and `ClaimEvidenceLink`.
2. Implement dataclasses with fields for exact claim text, source span reference, system verdict, evidence rank, rationale, and chunk/document references.
3. Keep scoring fields optional and minimal.
4. Run focused tests.
5. Commit.

### Task 2.3: Add review and queue item records
**Objective:** Capture human decisions and queueable analyst work.

**Files:**
- Create: `src/sourcetrace/domain/reviews.py`
- Create: `tests/unit/domain/test_reviews.py`

**Steps:**
1. Write failing tests for `ClaimReviewDecision` and `ReviewQueueItem`.
2. Implement dataclasses that separate:
   - system verdict
   - human review status
   - final analyst disposition
3. Add required rationale/override note expectations in tests where appropriate.
4. Run focused tests.
5. Commit.

### Task 2.4: Export domain records
**Objective:** Keep the domain import surface stable.

**Files:**
- Modify: `src/sourcetrace/domain/__init__.py`
- Test: `tests/unit/domain/test_documents.py`
- Test: `tests/unit/domain/test_claims.py`
- Test: `tests/unit/domain/test_reviews.py`

**Steps:**
1. Add import-surface tests.
2. Re-export dataclasses.
3. Run focused tests.
4. Commit.

---

## Slice 3: Add application-level protocols and in-memory repositories

### Task 3.1: Define repository protocols
**Objective:** Freeze storage contracts before implementing adapters.

**Files:**
- Create: `src/sourcetrace/application/protocols.py`
- Create: `tests/unit/application/test_protocols.py`

**Steps:**
1. Write failing tests or typing-oriented smoke assertions for repository method names.
2. Add protocols for document, claim, review queue, and review decision persistence.
3. Keep methods minimal: add/get/list/update by id/case.
4. Run focused tests.
5. Commit.

### Task 3.2: Implement in-memory repositories
**Objective:** Make contracts executable without DB choices.

**Files:**
- Create: `src/sourcetrace/storage/memory.py`
- Create: `tests/unit/storage/test_memory_repositories.py`

**Steps:**
1. Write failing tests for CRUD-like behavior over in-memory stores.
2. Implement in-memory repositories matching protocols.
3. Run focused tests.
4. Commit.

### Task 3.3: Define review service contract
**Objective:** Provide one application seam for queue and review behavior.

**Files:**
- Create: `src/sourcetrace/application/review_service.py`
- Create: `tests/unit/application/test_review_service.py`

**Steps:**
1. Write failing tests for:
   - queue listing
   - claim review submission
   - report eligibility gate based on unresolved contradiction / followup
2. Implement minimal service using in-memory repos.
3. Keep policy logic explicit and local.
4. Run focused tests.
5. Commit.

---

## Slice 4: Add minimal read models for analyst workflow

### Task 4.1: Build case overview read model
**Objective:** Produce the summary shape needed by the planned review UI.

**Files:**
- Create: `src/sourcetrace/application/read_models.py`
- Create: `tests/unit/application/test_read_models.py`

**Steps:**
1. Write failing tests for a case overview summarizing counts of `support`, `contradict`, `insufficient_evidence`, `unreviewed`, blocked claims.
2. Implement minimal dataclasses/functions for case overview output.
3. Run focused tests.
4. Commit.

### Task 4.2: Build claim workspace read model
**Objective:** Produce ranked evidence and review state for one claim.

**Files:**
- Modify: `src/sourcetrace/application/read_models.py`
- Test: `tests/unit/application/test_read_models.py`

**Steps:**
1. Write failing tests for claim workspace payload shape.
2. Add ranked evidence list output with source reliability / information credibility fields included.
3. Run focused tests.
4. Commit.

---

## Slice 5: Add minimal web/API contract surface

### Task 5.1: Create import-safe web DTO schemas
**Objective:** Freeze API-facing shapes without choosing the full framework surface yet.

**Files:**
- Create: `src/sourcetrace/web/schemas.py`
- Create: `tests/unit/web/test_schemas.py`

**Steps:**
1. Write failing tests for serialization-friendly DTOs mirroring case overview and claim workspace.
2. Implement dataclasses or TypedDicts.
3. Run focused tests.
4. Commit.

### Task 5.2: Add minimal review API stub contract
**Objective:** Prepare for later web delivery with no heavy implementation.

**Files:**
- Create: `src/sourcetrace/web/review_api.py`
- Create: `tests/unit/web/test_review_api.py`

**Steps:**
1. Write failing tests for pure-Python handler functions or adapter stubs such as:
   - `get_case_overview(case_id)`
   - `get_claim_workspace(claim_id)`
   - `submit_claim_review(...)`
2. Implement framework-agnostic functions first.
3. Run focused tests.
4. Commit.

---

## Slice 6: Add report gating contract

### Task 6.1: Define report eligibility rules explicitly
**Objective:** Make report gating a tested rule, not an implicit behavior.

**Files:**
- Create: `src/sourcetrace/application/reporting_policy.py`
- Create: `tests/unit/application/test_reporting_policy.py`

**Steps:**
1. Write failing tests for cases that should be `report_ready` vs `blocked`.
2. Implement minimal policy helpers.
3. Run focused tests.
4. Commit.

### Task 6.2: Add report summary read model
**Objective:** Prepare a future report/export seam backed by reviewed claims only.

**Files:**
- Create: `src/sourcetrace/application/report_models.py`
- Create: `tests/unit/application/test_report_models.py`

**Steps:**
1. Write failing tests for a report summary built only from eligible claims.
2. Implement minimal read model.
3. Run focused tests.
4. Commit.

---

## Cross-slice verification commands
Run after each slice:
- Focused tests for changed files, for example: `pytest tests/unit/domain/test_types.py -q`
- Then broader unit set as needed.

Run after major milestones:
- `pytest -q`

Optional static checks once code volume justifies it:
- `python -m compileall src tests`
- later: `ruff check src tests`

---

## Files likely to exist after v1 foundation
- `src/sourcetrace/domain/types.py`
- `src/sourcetrace/domain/documents.py`
- `src/sourcetrace/domain/claims.py`
- `src/sourcetrace/domain/reviews.py`
- `src/sourcetrace/application/protocols.py`
- `src/sourcetrace/application/review_service.py`
- `src/sourcetrace/application/read_models.py`
- `src/sourcetrace/application/reporting_policy.py`
- `src/sourcetrace/application/report_models.py`
- `src/sourcetrace/storage/memory.py`
- `src/sourcetrace/web/schemas.py`
- `src/sourcetrace/web/review_api.py`

## Later at execution start
If implementation begins, also update in the same pass:
- `docs/plans/execution-blueprint-v0.md` — mark Phase B entered / point to active implementation plan if repo adopts that pattern
- `docs/architecture/architecture-ssot.md` — if any contract names change during implementation
- `docs/research/research-ledger.md` — only if new implementation evidence changes prior conclusions
