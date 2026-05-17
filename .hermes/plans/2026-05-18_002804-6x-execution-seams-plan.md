# SourceTrace 6.x Execution Seams Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ustalić minimalne execution-side seams między domkniętą warstwą `application` a przyszłymi warstwami `pipeline` i `storage`, bez wchodzenia jeszcze w konkretne adaptery lub silniki.

**Architecture:** Po domknięciu kontraktów `domain` i `application` kolejnym krokiem jakościowym nie jest implementacja engine, tylko jawne granice odpowiedzialności. `6.x` powinno wprowadzić cienkie `Protocol`-like albo abstract-interface seams dla wykonywania use case’ów: ingestion, document preparation, extraction, verification, review/report assembly, credibility assessment. Nadal bez runtime adapters i bez storage implementation.

**Tech Stack:** Python 3.12+, `typing.Protocol` albo równoważne lekkie interfejsy, pytest, istniejące kontrakty z `src/sourcetrace/domain/` i `src/sourcetrace/application/`.

---

## Confirmed baseline

- Warstwa `domain` jest domknięta kontraktowo.
- Warstwa `application` jest domknięta kontraktowo dla:
  - case intake
  - document preparation
  - claim extraction
  - claim verification
  - human review
  - report assembly
  - credibility assessment
- Testy po `5.8` przechodzą lokalnie:
  - confirmed: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q` → `84 passed`
- Repo docs zostały zsynchronizowane do stanu „domain + application contracts in place”.

## Scope rule for 6.x

Każdy slice 6.x ma spełniać wszystkie warunki:
- definiuje tylko jawny execution seam,
- nie implementuje konkretnego storage, retrievera, parsera ani model runnera,
- nie dodaje side-effectful runtime behavior,
- jeśli używa `Protocol`, to tylko jako granica wołania, nie jako ukryty service locator,
- testuje shape i importowalność kontraktu, nie prawdziwe wykonanie.

## Recommended 6.x slice order

### Slice 6.1 — freeze execution seam package shape
**Objective:** Ustalić, gdzie mieszczą się execution-side interfaces i jak są eksportowane.

**Files:**
- Create: `src/sourcetrace/pipeline/interfaces.py` lub `src/sourcetrace/application/interfaces.py` (do wyboru po krótkim review)
- Modify: `src/sourcetrace/pipeline/__init__.py` albo `src/sourcetrace/application/__init__.py`
- Create: `tests/unit/<layer>/test_*_package_exports.py`

**Decision to make first:**
- czy seams należą do `application` jako dependency contracts,
- czy do `pipeline` jako execution adapters boundary.

### Slice 6.2 — case intake execution seam
**Objective:** Jawny seam dla wykonania `CaseCreationRequest` i `SourceIngestionRequest`.

**Likely contracts:**
- `CaseCreator`
- `SourceIngestor`

**Input/output:**
- application request/outcome records z `application/cases.py`

### Slice 6.3 — document preparation execution seam
**Objective:** Jawny seam dla przejścia `DocumentPreparationRequest -> DocumentPreparationOutcome`.

**Likely contracts:**
- `DocumentPreparer`

### Slice 6.4 — claim extraction execution seam
**Objective:** Jawny seam dla `ClaimExtractionRequest -> ClaimExtractionOutcome`.

**Likely contracts:**
- `ClaimExtractor`

### Slice 6.5 — claim verification execution seam
**Objective:** Jawny seam dla `ClaimVerificationRequest -> ClaimVerificationOutcome`.

**Likely contracts:**
- `ClaimVerifier`
- do weryfikacji: czy retrieval dependency ma być częścią tego seam, czy osobnym seamem poniżej

### Slice 6.6 — review/report assembly execution seams
**Objective:** Jawne seams dla review i report assembly bez mieszania ich w jeden wielki service.

**Likely contracts:**
- `ClaimReviewer`
- `ReportAssembler`

### Slice 6.7 — credibility assessment execution seam
**Objective:** Jawny advisory seam dla `CredibilityAssessmentRequest -> CredibilityAssessmentOutcome`.

**Likely contracts:**
- `CredibilityAssessor`

### Slice 6.8 — retrieval and storage dependency seams
**Objective:** Dopiero tutaj rozpisać cienkie lower-level seams wymagane przez verification / ingestion, bez implementacji adapterów.

**Likely contracts:**
- `ChunkRetriever`
- `CaseRepository`
- `DocumentRepository`
- `ClaimRepository`
- do weryfikacji: czy report persistence w MVP w ogóle potrzebuje osobnego repo contract na tym etapie

---

## Main design question before execution

Najpierw trzeba rozstrzygnąć jedną rzecz:
- **wariant A:** seams mieszkają przy `application`, bo `application` definiuje zależności use case’ów,
- **wariant B:** seams mieszkają przy `pipeline/storage`, bo to te warstwy realizują wykonanie.

Robocza rekomendacja:
- preferuję **wariant A** dla use-case-facing interfaces,
- a niższe repo/retrieval seams umieścić bliżej `storage`/`pipeline`.

Powód:
- to lepiej zachowuje direction dependency: `application` mówi, czego potrzebuje; adaptery później to implementują.

## Do weryfikacji

- Czy `typing.Protocol` jest lepszy niż własne abstract base classes dla czytelności repo.
- Czy retrieval seam powinien pojawić się wcześniej niż `ClaimVerifier`, jeśli verification logicznie zależy od retrieval.
- Czy review seam w MVP w ogóle potrzebuje osobnego execution interface, czy pozostaje czystym synchronizatorem nad istniejącymi rekordami.
- Czy storage seams powinny być rozpisane per aggregate (`CaseRepository`, `DocumentRepository`, `ClaimRepository`) czy najpierw jako jeden węższy persistence boundary.

## Later at execution start

Jeśli użytkownik da go-ahead na 6.x:
- zacząć od `6.1 freeze execution seam package shape`,
- nie skakać od razu do repo contracts i adapterów,
- po `6.1` podjąć krótką decyzję lokalizacyjną A/B i dopiero wtedy wdrażać pierwsze bounded interfaces.
