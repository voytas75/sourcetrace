# SourceTrace Application Contract Slices Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ustalić jawny, minimalny kontrakt warstwy `application`, żeby kolejne slice’y wynikały z architektury i istniejących kontraktów domeny, a nie z ad hoc interpretacji.

**Architecture:** Warstwa `application` ma pozostać cienka i kontraktowa. Nie wprowadza storage, Protocols wykonawczych, pipeline runtime ani UI. Modeluje tylko wejścia/wyjścia use case’ów, które orkiestrują istniejące rekordy domenowe między etapami: ingestion, extraction, verification, review, reporting, credibility assessment.

**Tech Stack:** Python 3.12+, `dataclasses`, pytest, istniejące kontrakty z `src/sourcetrace/domain/`.

---

## Confirmed baseline

- `docs/plans/execution-blueprint-v0.md` definiuje application layer jako: `create case`, `ingest source into case`, `chunk and enrich document`, `extract entities and claims`, `validate claims`, `assemble report`, `review workflow actions`, `credibility assessment workflow`.
- Domena ma już gotowe kontrakty dla:
  - case/report: `Case`, `CaseReport`
  - documents: `Document`, `DocumentCredibilityAssessment`
  - chunks: `DocumentChunk`
  - retrieval: `RetrievalQuery`, `RetrievalHit`, `RetrievalResultSet`
  - claims/review/report flow: `Claim`, `ClaimEvidenceLink`, `ClaimVerification`, `ClaimReviewDecision`, `ClaimReportEntry`
- `src/sourcetrace/application/` było prawie puste; po ostatnim kroku istnieje już pierwszy kontrakt `verification.py`.

## Scope rule for this plan

Każdy slice `application` ma spełniać wszystkie warunki:
- tylko immutable `@dataclass(frozen=True)` albo cienki export surface,
- bez metod wykonawczych,
- bez zależności od storage/web/pipeline runtime,
- używa tylko już istniejących kontraktów domeny,
- reprezentuje jawne wejście/wyjście use case’a.

## Application contract map

### A. Case intake
Cel: rozpoczęcie sprawy i przypięcie źródeł do case.

Minimalne kontrakty docelowe:
- `CaseCreationRequest`
- `CaseCreationOutcome`
- `SourceIngestionRequest`
- `SourceIngestionOutcome`

Powiązane rekordy domeny:
- `Case`
- `Document`

### B. Document preparation
Cel: przejście od dokumentu do chunków gotowych do dalszej analizy.

Minimalne kontrakty docelowe:
- `DocumentPreparationRequest`
- `DocumentPreparationOutcome`

Powiązane rekordy domeny:
- `Document`
- `DocumentChunk`

### C. Claim extraction
Cel: przejście od przygotowanego dokumentu/chunks do claimów i ich podstawowych evidence links.

Minimalne kontrakty docelowe:
- `ClaimExtractionRequest`
- `ClaimExtractionOutcome`

Powiązane rekordy domeny:
- `Document`
- `DocumentChunk`
- `Claim`
- `ClaimEvidenceLink`

### D. Claim verification
Cel: połączyć claim z retrieval context i wynikiem weryfikacji.

Minimalne kontrakty docelowe:
- `ClaimVerificationRequest`
- `ClaimVerificationOutcome`

Powiązane rekordy domeny:
- `RetrievalQuery`
- `RetrievalResultSet`
- `ClaimVerification`

Status:
- pierwszy cienki wariant już istnieje w `src/sourcetrace/application/verification.py`
- do późniejszej rewizji pod kątem spójności nazewnictwa całego pakietu

### E. Human review
Cel: oddzielić system verification od decyzji analityka.

Minimalne kontrakty docelowe:
- `ClaimReviewRequest`
- `ClaimReviewOutcome`

Powiązane rekordy domeny:
- `ClaimVerification`
- `ClaimReviewDecision`

### F. Report assembly
Cel: z reviewed claims zbudować report-ready entries i case-level report.

Minimalne kontrakty docelowe:
- `ReportAssemblyRequest`
- `ReportAssemblyOutcome`

Powiązane rekordy domeny:
- `ClaimReportEntry`
- `CaseReport`

### G. Credibility assessment
Cel: oddzielny application flow dla advisory OSINT scoring dokumentu.

Minimalne kontrakty docelowe:
- `CredibilityAssessmentRequest`
- `CredibilityAssessmentOutcome`

Powiązane rekordy domeny:
- `Document`
- `DocumentCredibilityAssessment`

---

## Recommended slice order

### Slice 5.1 — freeze application package shape
**Objective:** Ustalić jawny zakres pakietu `application` i jego modułów kontraktowych.

**Files:**
- Modify: `src/sourcetrace/application/__init__.py`
- Create: `tests/unit/application/test_package_exports.py`
- Modify or create: `tests/unit/test_package_layout.py`

**Output:**
- jawny export surface dla application layer
- test, że `application` jest osobnym kontraktowym pakietem
- bez dodawania nowych runtime behaviors

### Slice 5.2 — case intake contracts
**Objective:** Dodać kontrakty dla startu sprawy i przypięcia źródła.

**Files:**
- Create: `src/sourcetrace/application/cases.py`
- Create: `tests/unit/application/test_cases.py`
- Modify: `src/sourcetrace/application/__init__.py`

**Contracts:**
- `CaseCreationRequest`, `CaseCreationOutcome`
- `SourceIngestionRequest`, `SourceIngestionOutcome`

### Slice 5.3 — document preparation contracts
**Objective:** Dodać kontrakty dla przejścia dokument -> chunki.

**Files:**
- Create: `src/sourcetrace/application/documents.py`
- Create: `tests/unit/application/test_documents.py`
- Modify: `src/sourcetrace/application/__init__.py`

**Contracts:**
- `DocumentPreparationRequest`, `DocumentPreparationOutcome`

### Slice 5.4 — claim extraction contracts
**Objective:** Dodać kontrakty dla przejścia chunked document -> claims.

**Files:**
- Create: `src/sourcetrace/application/extraction.py`
- Create: `tests/unit/application/test_extraction.py`
- Modify: `src/sourcetrace/application/__init__.py`

**Contracts:**
- `ClaimExtractionRequest`, `ClaimExtractionOutcome`

### Slice 5.5 — verification contract cleanup/freeze
**Objective:** Dopiąć już istniejący verification flow do spójnej mapy pakietu.

**Files:**
- Modify: `src/sourcetrace/application/verification.py`
- Modify: `tests/unit/application/test_verification.py`
- Modify: `src/sourcetrace/application/__init__.py`
- Modify: `tests/unit/application/test_package_exports.py`

**Contracts:**
- utrzymujemy `ClaimVerificationRequest`, `ClaimVerificationOutcome`
- tylko ewentualne ujednolicenie naming/exports, bez rozszerzania do services

### Slice 5.6 — human review contracts
**Objective:** Dodać kontrakty dla review decision flow.

**Files:**
- Create: `src/sourcetrace/application/review.py`
- Create: `tests/unit/application/test_review.py`
- Modify: `src/sourcetrace/application/__init__.py`

**Contracts:**
- `ClaimReviewRequest`, `ClaimReviewOutcome`

### Slice 5.7 — report assembly contracts
**Objective:** Dodać kontrakty dla składania outputu reportowego.

**Files:**
- Create: `src/sourcetrace/application/reporting.py`
- Create: `tests/unit/application/test_reporting.py`
- Modify: `src/sourcetrace/application/__init__.py`

**Contracts:**
- `ReportAssemblyRequest`, `ReportAssemblyOutcome`

### Slice 5.8 — credibility assessment contracts
**Objective:** Dodać osobny advisory flow dla OSINT credibility metadata.

**Files:**
- Create: `src/sourcetrace/application/credibility.py`
- Create: `tests/unit/application/test_credibility.py`
- Modify: `src/sourcetrace/application/__init__.py`

**Contracts:**
- `CredibilityAssessmentRequest`, `CredibilityAssessmentOutcome`

---

## Naming rules

- Request = wejście use case’a
- Outcome = wyjście use case’a
- Nazwa modułu opisuje concern, nie technologię
- Nie używać jeszcze nazw typu `Service`, `UseCase`, `Manager`, `Protocol`
- Jeżeli kontrakt scala wiele rekordów domeny, powinien robić to jawnie przez pola, nie przez niejawne dict-y

## Verification rules per slice

Minimalnie po każdym slice:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest tests/unit/application/<target_test>.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q`

Dodatkowo dla export freeze:
- sprawdzić import z `sourcetrace.application`
- sprawdzić immutability przez `FrozenInstanceError`

## Do weryfikacji

- Czy `SourceIngestion*` powinno mieszkać razem z `CaseCreation*` czy w osobnym module `ingestion.py`.
- Czy `ClaimExtractionOutcome` powinno zawierać też entity artifacts, jeśli encje wrócą do domeny MVP.
- Czy `ReportAssemblyOutcome` ma nieść tylko `CaseReport`, czy też tuple `ClaimReportEntry` + `CaseReport`.
- Czy credibility flow powinien być wcześniej niż reporting; na razie rekomenduję później, bo jest advisory, nie blokuje core claim flow.

## Later at execution start

Jeśli użytkownik wskaże konkretny slice do wdrożenia:
- najpierw dopasować istniejący `verification.py` do zatwierdzonej mapy,
- potem iść zgodnie z powyższą numeracją 5.1–5.8,
- nie dopowiadać nowych slice’ów poza tą mapą bez aktualizacji tego planu.
