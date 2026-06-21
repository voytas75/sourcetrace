# Deep Research benchmark pack v1

Status: proposed next-step pack
Date: 2026-06-21
Scope: bounded benchmark set for evaluating SourceTrace Deep Research output quality before any Odysseus-comparison or heuristic porting work.

## 1. Verdict

SourceTrace Deep Research now has enough externally testable API surface for black-box benchmarking.

Usable benchmark surface:
- `POST /api/research/start`
- `GET /api/research/jobs?owner_id=...`
- `GET /api/research/status/{job_id}`
- `GET /api/research/stream/{job_id}`
- `GET /api/research/result/{job_id}`
- `POST /api/research/run/{job_id}`
- `POST /api/research/cancel/{job_id}`
- `GET /research`

This is sufficient to benchmark:
- job lifecycle correctness,
- progress/event visibility,
- result artifact availability,
- report-shape consistency,
- source relevance quality,
- output truthfulness and restraint.

This is not yet an analyst-grade evaluation harness. It is the smallest useful benchmark pack for deciding the next bounded quality slice.

---

## 2. Why benchmark before checking Odysseus

Do not compare against Odysseus yet just because an older implementation exists.

First determine:
1. whether SourceTrace already clears the required quality bar,
2. where it fails in a measurable way,
3. whether the failure is about ranking, source filtering, synthesis discipline, or telemetry.

Only after that should Odysseus be opened as a reference implementation for a specific missing behavior.

---

## 3. Benchmark goals

The benchmark pack should answer four questions:

1. **Does the system complete the full Deep Research flow reliably through its public API?**
2. **Do the returned sources match the query class rather than just containing overlapping words?**
3. **Does the final report stay evidence-first and appropriately uncertain when evidence is weak?**
4. **Is the result metadata truthful enough to support future debugging and tuning?**

---

## 4. Benchmark dimensions

Each benchmark run should be scored on these dimensions.

### A. Lifecycle/API correctness
Pass criteria:
- job can be started,
- job can be run,
- status transitions are visible,
- final state is reachable,
- result artifact can be fetched,
- stream/status are coherent with final result.

### B. Source relevance
Assess whether top findings are actually about the query, not loosely related keyword collisions.

### C. Source quality
Assess whether better sources are favored when query class suggests they should be.
Examples:
- official docs for procedural/admin queries,
- concrete market/symbol pages for pair-specific market queries,
- primary or clearly attributable reporting for news-style queries.

### D. Synthesis truthfulness
Assess whether the final report:
- distinguishes answer from uncertainty,
- avoids overclaiming beyond evidence,
- keeps weak evidence weak,
- does not smuggle speculation into the answer section.

### E. Output shape consistency
Assess whether the report keeps the expected operator-facing structure:
- `## Current answer`
- `## Key findings`
- `## Uncertainty`
- `## Next checks`

### F. Telemetry truthfulness
Assess whether metadata such as `result.stats.search_providers` accurately reflects the actual search path used.

---

## 5. Canonical benchmark queries

Use a small but intentionally mixed set.

### Query 1 — market symbol precision
- Query: `analiza ostatniego tygodnia ETHUSDC`
- Purpose: verify exact pair-symbol relevance and resistance to near-match noise.
- What good looks like:
  - exact `ETHUSDC` sources are favored,
  - unrelated pairs like `USDCAD` do not contaminate top findings,
  - result discusses recent period movement rather than generic crypto explainers,
  - uncertainty is explicit if authoritative market data is thin.
- Likely failure modes:
  - symbol collision,
  - generic crypto articles outranking pair-specific pages,
  - technical-analysis fluff dominating evidence.

### Query 2 — procedural / official-doc preference
- Query: `How do I create configuration baselines in SCCM?`
- Purpose: verify official-doc prioritization for procedural enterprise queries.
- What good looks like:
  - Microsoft Learn or clearly authoritative ConfigMgr documentation appears near the top,
  - generic blogs / forums / YouTube are demoted,
  - answer is procedural rather than discursive,
  - next checks suggest version/scope validation when needed.
- Likely failure modes:
  - SEO/tutorial sludge outranking official docs,
  - generic endpoint-management pages outranking baseline-specific docs,
  - answer drifting into adjacent SCCM topics.

### Query 3 — architecture / product understanding
- Query: `deep research architecture`
- Purpose: verify the system can handle a broad conceptual query without inventing specificity.
- What good looks like:
  - answer synthesizes common architectural patterns instead of pretending there is one canonical design,
  - findings cite concrete sources or frameworks,
  - uncertainty clearly marks ambiguity across implementations.
- Likely failure modes:
  - vague word-salad answer,
  - overconfident fake consensus,
  - weak source diversity.

### Query 4 — news / current-event ambiguity control
- Query: `latest developments in passkeys enterprise rollout`
- Purpose: verify current-awareness behavior and ambiguity restraint on moving topics.
- What good looks like:
  - recent and attributable sources are preferred,
  - answer distinguishes trend from settled fact,
  - uncertainty increases when evidence is fragmented.
- Likely failure modes:
  - stale evergreen explainers dominating results,
  - weak attribution,
  - overstated consensus.

### Optional Query 5 — deliberately hard / sparse case
- Query: choose one query where strong evidence is expected to be sparse or mixed.
- Purpose: test whether SourceTrace can fail gracefully.
- What good looks like:
  - restrained answer,
  - visible uncertainty,
  - useful next checks instead of bluffing.

---

## 6. Scoring rubric

Use a simple 0–2 score per dimension per query.

### Per-dimension score meanings
- `0` = failed / clearly misleading
- `1` = partially acceptable / mixed quality
- `2` = good enough for current slice

### Dimensions to score per query
- lifecycle/api correctness
- source relevance
- source quality
- synthesis truthfulness
- output shape consistency
- telemetry truthfulness

Maximum per query: `12`

Suggested interpretation:
- `10–12` = good, no immediate Odysseus comparison needed
- `7–9` = acceptable but worth one bounded tuning slice
- `0–6` = weak; compare with Odysseus only after naming the failing dimension

---

## 7. Minimal run procedure

For each query:

1. `POST /api/research/start` with `owner_id` and query.
2. `POST /api/research/run/{job_id}`.
3. Poll `GET /api/research/status/{job_id}` until terminal state, or inspect `GET /api/research/stream/{job_id}`.
4. Fetch `GET /api/research/result/{job_id}`.
5. Score the result against the rubric.
6. Record:
   - top apparent source types,
   - obvious off-topic pollution,
   - whether uncertainty handling was honest,
   - whether telemetry matched observed behavior.

---

## 8. Pass/fail decision for the next slice

### If benchmark mostly passes
Do not inspect Odysseus.
Proceed with the smallest local quality slice only:
- telemetry fix,
- source ranking refinement,
- topic-specific reranking.

### If one dimension repeatedly fails
Inspect Odysseus only for that named dimension.
Examples:
- source ranking heuristic,
- market symbol query shaping,
- source acceptance/rejection rules,
- synthesis prompt/report discipline.

### If multiple dimensions fail
Do not cherry-pick heuristics first.
Reassess SourceTrace runtime boundaries and evaluation method before importing behavior from Odysseus.

---

## 9. Expected first follow-up slice

Based on the current known state, the most likely first follow-up remains:

### telemetry + source-quality truthfulness

Specifically:
1. make `result.stats.search_providers` reflect reality,
2. benchmark exact-symbol queries and official-doc procedural queries,
3. tune only the weakest repeated dimension shown by the benchmark.

---

## 10. Definition of done for this benchmark pack

This pack is considered successfully used when:
- at least 3 canonical queries are run through the public Deep Research API,
- each run receives rubric scores,
- one next slice is chosen from observed failures,
- any decision to inspect Odysseus is tied to a named failing dimension rather than curiosity.
