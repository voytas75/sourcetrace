# SourceTrace v2 Slice 1 — real search adapter + retrieval input path (2026-06-27)

## Verdict
The next healthy v2 slice should add **one real evidence-input seam**.

It should not try to deliver full Deep Research retrieval parity.
It should prove that the v2 spine can ingest external search input cleanly, attribute it truthfully, and project it without collapsing back into v1-style orchestration sprawl.

## Why this slice is next
Current v2 proves:
- runtime composition
- profile-driven stages
- typed receipts
- persistence truth
- readback semantics

Current v2 does **not** yet prove:
- real external evidence input
- retrieval provenance in execution truth
- result/readback projection of evidence candidates

Without this slice, v2 is still mostly an architecture proof.

## Slice goal
Add one bounded search/retrieval seam so a v2 run can:
1. call one real search adapter,
2. capture retrieved evidence candidates as typed records,
3. preserve provenance in execution truth,
4. expose that provenance in result/readback projection.

## Scope
Include only:
- one search contract in v2
- one concrete adapter path
- one bounded retrieval stage or retrieval sub-step
- typed retrieved-candidate record(s)
- receipt/projection support for evidence input provenance
- vertical tests for the bounded path

## Explicit exclusions
Do not include:
- provider plurality
- ranking sophistication
- scraping/content extraction richness
- PDF ingestion
- queue/background execution
- compiled artifact parity
- analyst workflow parity
- broad HTML/UI work
- migration of v1 search logic wholesale

## Recommended architecture

### 1. Add a v2 search contract
Create a small contract under v2 adapter/core boundaries for one search operation.

Recommended shape:
- input: query text, max results
- output: tuple of typed candidate records

The contract should be small enough that changing providers later does not leak provider-specific payloads into execution logic.

### 2. Add typed retrieved candidate model(s)
Add one typed domain/read model for evidence candidates.

Minimum useful fields:
- `candidate_id`
- `job_id`
- `run_id`
- `source_type` or `provider`
- `title`
- `url`
- `snippet`
- `rank`

Do not over-model early.
The first goal is explicit provenance, not complete retrieval theory.

### 3. Add one retrieval-attribution seam
There are two healthy options:

#### Option A — dedicated retrieval stage
Add a new stage identifier such as `retrieval` between `query_refinement` and `evidence_judge`.

Pros:
- clear attribution
- easy receipts
- cleaner future extension

Cons:
- slightly widens the proving flow

#### Option B — bounded sub-step inside `evidence_judge`
Keep stage count unchanged and introduce retrieval as a typed sub-step feeding evidence judgment.

Pros:
- smaller surface change

Cons:
- weaker future decomposition

### Recommendation
Prefer **Option A: dedicated `retrieval` stage**.

Reason:
This slice exists partly to prove bounded extensibility.
If adding one real capability cannot justify one explicit stage, the spine is staying too abstract.

## Minimal contract additions

### Stage identifiers
If Option A is used, add:
- `StageId.RETRIEVAL`

### Search adapter interface
Example intent, not final API:
- `search(query: str, limit: int) -> tuple[RetrievedEvidenceCandidate, ...]`

### Retrieval receipt or attribution record
One of these should become explicit:
- dedicated retrieval receipt type, or
- typed retrieval candidate collection attached to the run artifact/read model

### Recommendation
Keep this slice lighter by:
- using typed candidate records + stage receipts,
- **not** inventing a new large receipt family unless the current stage/LLM receipts prove insufficient.

## Projection requirements
The operator/readback surface should answer:
- was retrieval attempted?
- which query was used?
- how many candidates came back?
- which provider/source produced them?
- what URLs/titles were selected as candidates?

Minimum healthy projection target:
- extend persisted/result projection with a compact `evidence_input` block

Suggested fields:
- `query`
- `candidate_count`
- `candidates[]` with `title`, `url`, `provider`, `rank`

Keep snippets optional if they add noise.

## Persistence posture
Do not add a new storage backend.
Use the existing bounded persistence posture.

Healthy options for this slice:
- include retrieved candidates inside the persisted result artifact, or
- add a very small adjacent persistence seam if artifact embedding becomes awkward

### Recommendation
Prefer embedding the first bounded candidate set into the result artifact/read model path unless that clearly harms artifact clarity.

Why:
- smaller change set
- faster proof
- easier rollback if the shape is wrong

## Testing requirements
Add bounded tests proving:
1. the retrieval stage/step is invoked
2. one concrete adapter returns typed candidates
3. provenance survives into projection/readback
4. partial retrieval failure still preserves truthful execution state
5. adding retrieval does not require broad rewiring of unrelated modules

## Minimum DoD
The slice is done when all are true:
1. v2 can call one real search adapter during a run
2. retrieved candidates are captured as typed records
3. provenance is visible in execution truth and projection
4. partial retrieval failure does not silently look like success
5. bounded tests for the new path pass
6. the rest of the v2 spine remains small and explicit

## Failure signals
Treat the slice as off-track if:
- provider response shapes leak directly into execution flow
- retrieval logic spreads across many unrelated files
- stage attribution becomes blurry
- projection reads from ad hoc mutable runtime state instead of typed artifacts/records
- the team starts importing v1 search/runtime code directly into v2 core paths

## Recommended concrete implementation order
1. add typed retrieval candidate model
2. add v2 search adapter interface
3. add one concrete adapter implementation
4. add explicit retrieval stage identifier
5. wire retrieval into the bounded flow
6. project evidence-input provenance in API/readback
7. add focused unit tests + one vertical test

## Bottom line
This slice should prove one thing clearly:

**v2 can ingest real external evidence input without sacrificing explicit seams, truthful attribution, or bounded extension cost.**
