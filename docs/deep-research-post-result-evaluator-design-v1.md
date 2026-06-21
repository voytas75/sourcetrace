# Deep Research post-result evaluator design v1

Status: proposed design
Date: 2026-06-21
Scope: bounded design for a post-result evaluation layer in SourceTrace Deep Research.

## 1. Verdict

A post-result evaluation layer is worth adding to SourceTrace, but only as a **bounded quality-control pass** with a strict structured contract.

It should **not** be introduced as:
- a second research loop,
- a freeform meta-prompt that merely “comments on” another LLM output,
- or a compensating layer that hides weak retrieval/ranking behavior.

Its correct role is:
- inspect the completed research artifact,
- classify quality risks,
- recommend the smallest next corrective action,
- optionally signal whether the final report should be revised,
- and improve observability of weak result classes.

This layer is diagnostic first, corrective second.

---

## 2. Why add this layer

The current benchmark run showed that Deep Research can already:
- complete jobs end-to-end,
- produce stable output sections,
- and stay reasonably restrained in uncertainty handling.

But it also showed recurring quality problems that are not purely lifecycle problems:
- weak source ranking on procedural queries,
- noisy source mixes on broad conceptual queries,
- telemetry/debug truthfulness gaps.

A post-result evaluator can help with these by answering a different question than the research runtime itself.

The research runtime asks:
- “what is the best answer we can currently assemble from gathered evidence?”

The evaluator asks:
- “how trustworthy, on-topic, and complete does this finished artifact look for this query class?”

That separation is useful.

---

## 3. Design goals

This layer should:
1. evaluate a finished research result using explicit criteria,
2. adapt its evaluation posture to the query class,
3. produce structured outputs that can be logged, tested, and later surfaced in UI/API,
4. avoid silently rewriting the report in v1,
5. support future benchmarking and targeted quality tuning.

This layer should not:
- invent new evidence,
- perform a hidden second retrieval pass,
- replace explicit retrieval/ranking improvements,
- or generate vague narrative feedback without actionable structure.

---

## 4. Placement in the Deep Research pipeline

Recommended placement:

`query -> search/extract/synthesize -> final research artifact -> post-result evaluator -> evaluation artifact`

So the evaluator runs **after** the research result is produced.

### v1 pipeline rule
The evaluator does **not** mutate the final report directly.
It produces a separate evaluation artifact attached to the same research job/result.

### optional later v2 rule
A later version may allow:
- `should_revise_report = true`
- followed by one bounded revision pass

But that should not be part of v1.

---

## 5. Inputs

The evaluator should operate on a structured payload, not only the final markdown report.

### Minimum input contract
- `query`
- `query_class`
- `result.raw_findings`
- source titles / URLs / summaries
- final report content (`raw_report` or normalized report field)
- research stats / metadata
- optionally progress summary or runtime warnings

### Why this matters
If the evaluator reads only the final report, it becomes an LLM reviewing another LLM’s prose.
That is too lossy.

If it sees the structured result components, it can judge:
- whether the answer is supported by the findings,
- whether source mix fits the query class,
- whether uncertainty is justified,
- whether obvious next checks are missing.

---

## 6. Query classes

The evaluator should not use one flat rubric for all research jobs.

Recommended initial query classes:
- `market_symbol`
- `procedural_admin`
- `broad_concept`
- `current_news`
- `unknown`

### Class-specific emphasis
- `market_symbol`
  - exact symbol matching
  - source comparability
  - avoidance of pair drift
  - explicit time-window caution

- `procedural_admin`
  - preference for official docs
  - demotion of blogs/forums/videos unless clearly necessary
  - step correctness and scope clarity

- `broad_concept`
  - breadth vs specificity balance
  - avoidance of fake consensus
  - explicit ambiguity handling

- `current_news`
  - recency and attribution
  - conflict awareness
  - restraint under fragmented evidence

---

## 7. Output contract

The evaluator must return a structured object.

### Proposed v1 output shape
```json
{
  "query_class": "market_symbol | procedural_admin | broad_concept | current_news | unknown",
  "source_quality_verdict": "strong | mixed | weak",
  "source_quality_reasons": ["..."],
  "relevance_verdict": "strong | mixed | weak",
  "relevance_risks": ["..."],
  "truthfulness_verdict": "strong | mixed | weak",
  "overclaim_risks": ["..."],
  "missing_checks": ["..."],
  "recommended_next_check": "...",
  "should_revise_report": false
}
```

### Notes
- `should_revise_report` in v1 is advisory only.
- Reasons and risks should be concise, specific, and evidence-facing.
- The evaluator should prefer explicit failure modes over generic critique.

---

## 8. Evaluation dimensions

The evaluator should judge at least these dimensions.

### A. Source quality
Does the result rely on sources appropriate for the query class?

### B. Relevance
Do the findings actually answer the query rather than merely sharing keywords?

### C. Truthfulness / overclaim risk
Does the answer stay inside the evidence envelope?

### D. Missing checks
What is the single most important missing validation step?

### E. Report revision recommendation
Is the result weak enough that a bounded rewrite would be justified later?

---

## 9. Runtime posture

### v1 posture
- one bounded evaluation call,
- no hidden recursion,
- no second search pass,
- no auto-rewrite,
- no automatic user-facing rejection of the result.

### reason
This keeps the evaluator interpretable and prevents it from becoming a silent patch layer over weak upstream quality.

---

## 10. Storage / artifact model

The evaluator should write a separate structured artifact associated with the research job.

Recommended artifact shape:
- one evaluation object per completed research result,
- persisted alongside research result artifacts,
- retrievable from API/UI later,
- suitable for benchmark analysis and regression testing.

Possible future placement:
- `data/research/evaluations/`
- or embedded under the persisted result payload if the artifact boundary stays simple.

### recommendation
Prefer a distinct stored evaluation object, even if physically persisted near result artifacts.
This keeps the research output and evaluation output conceptually separate.

---

## 11. API / UI posture

Not required for the first design slice, but the evaluator should be designed so that it can later support:
- API retrieval of evaluation results,
- UI surfacing of quality flags,
- benchmark harness reuse,
- manual operator inspection of weak-result reasons.
\n### Recommended future surface
- add evaluation data to the research result payload, or
- expose a dedicated evaluation endpoint per job/result.

This does not need to ship in the first implementation slice.

---

## 12. Interaction with current known issues

This design must not be used to hide current issues already identified by benchmarking.

Specifically, the evaluator must not become a substitute for:
- fixing `result.stats.search_providers`,
- improving official-doc preference for procedural/admin queries,
- improving source rejection/ranking when query-class heuristics are weak.

So the intended order remains:
1. telemetry truthfulness fixes,
2. source-quality/ranking hardening,
3. post-result evaluator v1.

---

## 13. Definition of done for the future implementation slice

The implementation slice for this design should be considered done when:
- completed research jobs can produce a structured evaluation artifact,
- evaluation uses query-class-aware criteria,
- the output follows the agreed schema,
- benchmark runs can inspect the evaluation artifact,
- no hidden second retrieval loop exists,
- no automatic rewrite is performed in v1.

---

## 14. Recommended next step

Do not implement this immediately as the very next slice.

First complete:
- telemetry truthfulness hardening,
- procedural-source-quality ranking improvements.

Then implement the evaluator as a **diagnostic flagger**.
Only after that should SourceTrace consider evaluator-driven conditional revision.
