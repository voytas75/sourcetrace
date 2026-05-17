# SourceTrace Research Ledger

Status: active
Purpose: track reviewed repositories, papers, and thematic sources; extract architecture implications; record what changed in SourceTrace thinking.

## How to use this ledger
For each research cycle:
1. Add the source.
2. Capture what it is about.
3. Record what is confirmed, what is only suggestive, and what remains to verify.
4. Note whether it changes SSOT or execution blueprint.

---

## Research questions
- What is the smallest architecture that still preserves evidence traceability?
- Which retrieval pattern gives the best MVP quality/cost ratio?
- Which validation steps most effectively reduce hallucinated claims?
- What should remain human-reviewed in iteration 1?
- When does a graph layer become worth its complexity?

---

## Reviewed sources

### Source: `oskarbrzycki/llm-cerebroscope`
Type: open-source GitHub repository
Status: reviewed at high level

#### Useful signals
- Evidence-centric document analysis framing.
- Citation tracking at chunk granularity.
- Conflict detection and reliability scoring as explicit modules.
- Separate reporter layer instead of raw LLM answer dump.

#### Confirmed implications
- A dedicated validator/reporter layer improves auditability.
- Chunk-level traceability should be first-class in SourceTrace.

#### Do weryfikacji
- How production-ready the implementation really is.
- How well the design generalizes from document analysis to broader OSINT workflows.

#### Impact on SourceTrace
- Strengthened the decision to keep claims, validation, and reporting as separate layers.

---

### Source: `rahulanand1103/rag-citation`
Type: open-source GitHub repository
Status: reviewed at high level

#### Useful signals
- Lightweight citation generation.
- Support for mapping answer sentences to source documents.
- Basic hallucination detection around unsupported entities.

#### Confirmed implications
- Citation generation should be a dedicated concern, not an afterthought.
- The system should keep a structured claim-to-evidence contract.

#### Do weryfikacji
- Whether its approach is sufficient for claim-level validation rather than answer-level post-processing only.

#### Impact on SourceTrace
- Reinforced evidence-link enforcement and the need for `claim_evidence` style modeling.

---

### Source: `Knowledgator/RetriCo`
Type: open-source GitHub repository
Status: reviewed at high level

#### Useful signals
- Modular pipeline design.
- Swappable stores and retrieval strategies.
- Graph support without forcing a monolithic stack.

#### Confirmed implications
- SourceTrace should stay modular even before implementation starts.
- Storage, retrieval, and extraction should not be fused into one runtime object.

#### Do weryfikacji
- Which parts of this modularity are worth carrying into iteration 1 without overengineering.

#### Impact on SourceTrace
- Strengthened the provisional package plan around domain/app/pipeline/storage/web separation.

---

### Source: `microsoft/graphrag`
Type: open-source GitHub repository + documentation
Status: reviewed at high level

#### Useful signals
- Strong concept model: entities, relationships, claims, local/global retrieval modes.
- Useful reminder that graph-based retrieval can help with holistic and multi-hop questions.

#### Confirmed implications
- Claims should be modeled explicitly, not buried in summaries.
- Retrieval modes may eventually need to diverge by question type.

#### Confirmed cautions
- Graph-heavy indexing is costly.
- Out-of-the-box quality is not guaranteed.
- Prompt tuning is likely needed in real deployments.

#### Impact on SourceTrace
- Supports deferring graph complexity from MVP while keeping the domain model extensible.

---

### Source: `deeplethe/ForgeRAG`
Type: open-source GitHub repository
Status: reviewed at high level

#### Useful signals
- Strong layering between ingestion, parser, persistence, retrieval, and answering.
- Explicit operational caveats around concurrency and backend choice.
- Hybrid retrieval as a first-class pattern.

#### Confirmed implications
- Hybrid retrieval deserves default consideration.
- Operational constraints should be explicit in architecture docs rather than discovered late.

#### Do weryfikacji
- Which of its production-style complexity actually pays off at MVP scale.

#### Impact on SourceTrace
- Strengthened the execution blueprint around layered components and conservative MVP infra.

---

### Source: `cany7/LumiCite`
Type: open-source GitHub repository
Status: reviewed at high level

#### Useful signals
- Clear parse/search/query split.
- Citation-aware answering over document corpora.
- Multimodal chunk model as a future growth path.

#### Confirmed implications
- Parse/search/query separation is a good structural cue.
- Citation-aware generation should only use actually selected retrieval context.

#### Do weryfikacji
- Whether multimodal support is worth any MVP design concessions.

#### Impact on SourceTrace
- Supports keeping interfaces narrow between parse, search, and answer/report phases.

---

### Source: `eTracer: Towards Traceable Text Generation via Claim-Level Grounding`
Type: research paper / arXiv 2026
Status: reviewed at abstract/method level

#### Useful signals
- Treats claims as atomic and independently verifiable units.
- Uses claim decomposition followed by evidence retrieval and entailment polarity.
- Explicitly links supportive and contradictory evidence to claims.
- Reports improved verification efficiency from claim-level grounding.

#### Confirmed implications
- SourceTrace should keep claim decomposition as a first-class concept.
- Validation should support contradiction, not only positive support.
- Claim-to-evidence scoring should be separate from final reporting.

#### Do weryfikacji
- How lightweight an MVP version of entailment polarity can be.
- Whether contradiction handling should block reporting or downgrade certainty by default.

#### Impact on SourceTrace
- Strengthened the need for signed claim-evidence relations and contradiction-aware validation.

---

### Source: `GenProve: Learning to Generate Text with Fine-Grained Provenance`
Type: research paper / arXiv 2026
Status: reviewed at abstract/method level

#### Useful signals
- Distinguishes provenance relations such as quotation, compression, and inference.
- Argues that citation alone is too coarse for accountability.
- Shows a reasoning gap between direct quotation and inference-based provenance.

#### Confirmed implications
- SourceTrace should not treat all citations as equivalent.
- The system should eventually preserve how evidence supports a claim, not only where it came from.

#### Working hypothesis
- MVP may start without typed provenance relations, but should leave room for them in the data model.

#### Impact on SourceTrace
- Strengthened the idea that provenance typing is a likely later upgrade path.

---

### Source: `Ground Every Sentence: Improving Retrieval-Augmented LLMs with Interleaved Reference-Claim Generation`
Type: research paper / arXiv 2024
Status: reviewed at abstract level

#### Useful signals
- Fine-grained attribution can be generated sentence by sentence.
- Interleaving references and claims improves citation accuracy over coarse passage attribution.

#### Confirmed implications
- Output generation should stay close to sentence/claim units, not only whole-document summaries.
- Reporting should remain grounded in small evidence units.

#### Do weryfikacji
- Whether interleaved generation is worth the complexity for iteration 1 versus post-hoc claim grounding.

#### Impact on SourceTrace
- Supports sentence/claim-level output contracts in reports.

---

### Source: `ClaimVer: Explainable Claim-Level Verification and Evidence Attribution of Text Through Knowledge Graphs`
Type: research paper / EMNLP Findings 2024
Status: reviewed at abstract/method level

#### Useful signals
- Human-centric claim verification reduces cognitive load.
- Rich annotations and rationale matter for trust.
- Attribution score and localized evidence presentation are key usability features.

#### Confirmed implications
- Analyst review UX should localize problematic claims rather than output blanket pass/fail labels.
- Explanations and attribution scores are useful design cues for review screens.

#### Do weryfikacji
- Whether SourceTrace needs attribution scoring in MVP or only later.
- Whether KG-backed verification has any MVP role without introducing graph complexity too early.

#### Impact on SourceTrace
- Strengthened the requirement for claim-focused analyst review rather than document-level verdicts.

---

### Source: `From Fluent to Verifiable: Claim-Level Auditability for Deep Research Agents`
Type: research paper / arXiv 2026
Status: reviewed at abstract level

#### Useful signals
- Distinguishes action traces from semantic provenance.
- Argues that unsupported statements and missing claim-evidence structure remain a core agent failure.
- Recommends explicit conflict representation and operational gating for unverified claims.

#### Confirmed implications
- SourceTrace should not confuse workflow logs with proof of support.
- Validation needs to represent conflicts explicitly.
- The system should gate downstream outputs based on evidence quality.

#### Impact on SourceTrace
- Strengthened the decision to keep report eligibility tied to validation status rather than generation alone.

---

### Source: `Reason and Verify: A Framework for Faithful Retrieval-Augmented Generation`
Type: research paper / arXiv 2026
Status: reviewed at abstract level

#### Useful signals
- Uses explicit rationale generation with evidence spans.
- Emphasizes reranking and structured verification taxonomy.
- Treats faithful reasoning as more than basic retrieval grounding.

#### Confirmed implications
- A verification taxonomy may be useful even before full graph/provenance sophistication.
- Reranking remains a serious candidate for quality improvement after MVP baseline retrieval.

#### Do weryfikacji
- Whether a lightweight rationale layer belongs in iteration 1 or iteration 2.

#### Impact on SourceTrace
- Reinforced the importance of explicit verification categories and future reranking work.

---

### Source: `PaperTrail: A Claim-Evidence Interface for Grounding Provenance in Scholarly QA`
Type: research paper / arXiv 2026
Status: reviewed at abstract level

#### Useful signals
- Uses offline extraction of source claims/evidence and real-time answer-level claim matching.
- Builds a claim-evidence interface rather than only a back-end provenance store.
- Emphasizes user-facing indicators for unsupported and omitted claims.

#### Confirmed implications
- SourceTrace should think about provenance as an interface concern, not only a storage concern.
- Offline extraction plus real-time matching may be a useful future split.

#### Do weryfikacji
- Whether omitted-claim indicators make sense for OSINT investigation outputs.

#### Impact on SourceTrace
- Strengthened the analyst-facing framing of claim-evidence inspection.

---

### Source: `Agentic AI framework for OSINT` (missing persons proof-of-concept paper)
Type: thematic OSINT paper
Status: reviewed at high level from extracted text

#### Useful signals
- Keeps human review in the loop even in an agentic framing.
- Mentions credibility assessment as a distinct stage.
- Treats ethics, transparency logging, and validation as integral rather than optional.

#### Confirmed implications
- Human review should remain non-optional in SourceTrace.
- Credibility assessment deserves explicit treatment in the roadmap.

#### Do weryfikacji
- Claimed gains versus baseline are not yet independently validated here.
- The practical rigor of the proposed framework is unclear from the extracted overview alone.

#### Impact on SourceTrace
- Supports keeping credibility assessment and transparency in the near-term research scope without adopting an agentic architecture prematurely.

---

### Source: `A Hybrid Retrieval and Reranking Framework for Evidence-Grounded RAG`
Type: research paper / arXiv 2026
Status: reviewed at abstract level

#### Useful signals
- Separates answer generation from a judge model for claim grounding evaluation.
- Treats a claim as supported only when evidence covers the full meaning, not just overlaps vaguely.
- Uses hybrid retrieval plus reranking before generation.

#### Confirmed implications
- SourceTrace should keep generation and claim verification as separate stages.
- Partial or vague evidence should not count as support.
- Hybrid retrieval remains the stronger default path.

#### Do weryfikacji
- Claimed 100% grounding accuracy comes from a small pilot and is not enough to generalize operationally.

#### Impact on SourceTrace
- Strengthened the architecture choice to split extraction/generation from validation and to keep a conservative support threshold.

---

### Source: `RAFTS — retrieval augmented fact verification through synthesis of contrasting arguments`
Type: research paper / ACL 2024
Status: reviewed from extracted paper text

#### Useful signals
- Retrieves and reranks evidence from verifiable sources.
- Explicitly synthesizes both supporting and refuting arguments.
- Treats absence of pertinent evidence as operationally meaningful.

#### Confirmed implications
- Contradiction handling should not be a side channel; it belongs in the main validation flow.
- SourceTrace should consider support/refute/insufficient as a useful operational triad.

#### Do weryfikacji
- Whether argument synthesis is worth the complexity for MVP or should stay behind simpler verdicts first.

#### Impact on SourceTrace
- Reinforced the need to model both supportive and refuting evidence explicitly.

---

### Source: `CLATTER: Comprehensive Entailment Reasoning for Hallucination Detection`
Type: research paper / arXiv 2025
Status: reviewed at abstract/method level

#### Useful signals
- Frames entailment checking as a 3-step process: decomposition, attribution + entailment, aggregation.
- Uses sub-claim level reasoning instead of monolithic sentence verdicts.
- Shows that supported / contradicted / neutral aggregation is more faithful than coarse checks.

#### Confirmed implications
- A lightweight MVP validator can still follow a three-step structure conceptually.
- Sub-claim decomposition is not optional if the goal is meaningful contradiction detection.

#### Impact on SourceTrace
- Strengthened the proposed minimal validation pipeline design.

---

### Source: `MedRAGChecker`
Type: research paper / arXiv 2026
Status: reviewed at abstract level

#### Useful signals
- Uses atomic claim verification with `Entail`, `Neutral`, `Contradict` verdicts.
- Aggregates claim-level outcomes into answer-level diagnostics rather than a single blunt score.
- Distinguishes different failure profiles such as under-evidence versus contradiction.

#### Confirmed implications
- SourceTrace should separate at least two negative states: missing evidence and contradictory evidence.
- Aggregated report quality should emerge from claim-level diagnostics.

#### Impact on SourceTrace
- Reinforced the need for per-claim verdicts with richer aggregation into report sections.

---

### Source: `VerifAI` (biomedical RAG with entailment-based verification)
Type: research paper / arXiv 2026
Status: reviewed from extracted text

#### Useful signals
- Combines hybrid retrieval, citation-aware generation, and post-hoc entailment verification.
- Explicitly distinguishes support, contradict, and no evidence.
- Verifies cited evidence rather than trusting citations at face value.

#### Confirmed implications
- SourceTrace should never treat citation presence as proof of support.
- Verification should operate on cited or linked evidence directly.

#### Impact on SourceTrace
- Strengthened the rule that claim-evidence links must still be validated semantically.

---

### Source: `Using soft-hard fusion for misinformation detection and pattern of life analysis in OSINT`
Type: OSINT credibility paper / 2017
Status: reviewed at abstract level

#### Useful signals
- Builds local consistency scores for both documents and sources.
- Uses conflict detection in fused multi-source knowledge structures.

#### Confirmed implications
- Source credibility and document-level credibility should remain analytically separate.
- Reliability scoring should consider conflicts across sources, not just per-source reputation.

#### Impact on SourceTrace
- Strengthened the roadmap item around separate source-versus-claim trust signals.

---

### Source: `Automated OSINT Source Evaluation Workflow`
Type: thematic article / practitioner workflow
Status: reviewed at high level

#### Useful signals
- Uses cross-referencing against trusted and suspicious source lists.
- Recommends provisional grading engines and manual override.
- Treats source evaluation as triage, not final truth.

#### Confirmed implications
- SourceTrace can start with rule-based provisional source grading.
- Human override should exist from the beginning if any credibility score is surfaced.

#### Do weryfikacji
- Specific external services and rating lists need separate validation before any integration claims are made.

#### Impact on SourceTrace
- Supports a simple, editable credibility model for early iterations.

---

### Source: `Amsterdam Matrix handbook`
Type: OSINT methodology handbook
Status: reviewed at overview level

#### Useful signals
- Trustworthiness assessment is parameterized and evidence-based.
- Social-media OSINT reliability should not be reduced to style or tone.

#### Confirmed implications
- Credibility scoring should use explicit criteria rather than vague global trust labels.
- Social or open web sources need different handling than institutional documents.

#### Impact on SourceTrace
- Strengthened the idea of criteria-based credibility evaluation rather than single opaque scores.

---

### Source: `CREDIBLE framework`
Type: source evaluation framework paper
Status: reviewed at high level

#### Useful signals
- Separates credibility and reliability as distinct judgments.
- Provides a compact checklist style model: credibility, reliability, evidence, date, intent, bias, logic, expertise.

#### Confirmed implications
- SourceTrace should separate immediate source-context trust cues from longitudinal reliability.
- A compact analyst-facing rubric may be more usable than a black-box score alone.

#### Impact on SourceTrace
- Supports a dual model of `source context cues` plus `historical reliability` in future credibility scoring.

---

### Source: `Assessing source credibility as a regression task` (news source scoring dataset/paper)
Type: research paper
Status: reviewed from extracted text

#### Useful signals
- Predicts source credibility from richer features rather than single labels.
- Notes that model outputs are most reliable outside the ambiguous middle range.

#### Confirmed implications
- If SourceTrace later uses learned credibility scoring, middle-range outputs should be treated cautiously.
- Credibility UI may need coarse buckets rather than fake precision.

#### Impact on SourceTrace
- Reinforced the case for provisional credibility bands instead of over-precise scalar trust numbers in MVP.

---

### Source: `ClaimVer` paper PDF
Type: research paper
Status: reviewed for UX-oriented passages

#### Useful signals
- Highlights exact problematic spans.
- Uses explanations and attribution score to reduce cognitive burden.
- Emphasizes user trust and usability as first-class goals.

#### Confirmed implications
- SourceTrace review UI should highlight claim spans and attach concise explanations.
- Explanation design must be tied to cognitive efficiency, not only transparency.

#### Impact on SourceTrace
- Strengthened claim-localized review UX requirements.

---

### Source: `PaperTrail` UX findings
Type: research paper
Status: reviewed for interface implications

#### Useful signals
- Granular provenance can reduce trust but also clutter the interface.
- Recommends graduated cognitive engagement: overview first, zoom/filter, details on demand.
- Flexible verification workflows matter; different users verify differently.

#### Confirmed implications
- SourceTrace should use progressive disclosure in review UI.
- Provenance details should be expandable, not all shown at once.
- Interface design must balance caution with workload.

#### Impact on SourceTrace
- Strengthened a layered analyst UI model rather than a fully expanded evidence wall.

---

### Source: `Facts&Evidence`
Type: interactive verification tool paper
Status: reviewed at abstract/interface level

#### Useful signals
- Presents per-claim, per-evidence decisions and rationales.
- Lets users include/exclude evidence or source types and recompute credibility.
- Treats source categories as user-visible controls.

#### Confirmed implications
- SourceTrace should consider interactive evidence filtering in later review UX.
- Per-claim, per-evidence decisions are a strong UI pattern.

#### Do weryfikacji
- Whether source-type toggles belong in MVP or a later analyst-facing slice.

#### Impact on SourceTrace
- Strengthened the analyst-agency direction for verification interfaces.

---

### Source: `User-Centric Evidence Ranking for Attribution and Fact Verification`
Type: research paper / 2026
Status: reviewed at abstract level

#### Useful signals
- Evidence ranking can reduce reading effort and improve verification success.
- Incremental ranking outperforms presenting all selected evidence equally.
- Sufficiency should appear early in the ranked list.

#### Confirmed implications
- SourceTrace should rank evidence for analyst consumption, not just retrieve it.
- Review UX should privilege early sufficient evidence and minimize redundancy.

#### Impact on SourceTrace
- Reinforced the need for evidence ranking as part of analyst-facing verification, even if reranking internals remain simple initially.

---

### Source: `Exploring Multidimensional Checkworthiness`
Type: research paper / claim prioritization UX
Status: reviewed at abstract level

#### Useful signals
- Fact-checkers use hierarchical, multidimensional prioritization in claim triage.
- Personalized weighting and multifaceted filters help selection workflows.

#### Confirmed implications
- Claim triage should be multidimensional, not only one confidence score.
- Review queues may later need weights for relevance, harm, uncertainty, and credibility.

#### Impact on SourceTrace
- Strengthened the idea that analyst review should support prioritization beyond raw model confidence.

---

### Source: `Explanation strategies in AI-driven security dashboards`
Type: research paper / UX study
Status: reviewed from extracted text

#### Useful signals
- Progressive disclosure reduces cognitive load better than always-expanded explanations.
- Explanations should surface uncertainty, not only confidence.
- Interaction with explanations should be logged for accountability.

#### Confirmed implications
- SourceTrace should default to a scannable summary with expandable rationale/evidence.
- Review UI should expose uncertainty and counter-evidence when present.
- Explanation usage may later become part of audit trails.

#### Impact on SourceTrace
- Reinforced a high-contrast, layered explanation model for analyst workflows.

---

### Source: `Loki: An Open-Source Tool for Fact Verification`
Type: research paper + open-source tool / COLING 2025 demo
Status: reviewed at abstract/interface level

#### Useful signals
- Uses a five-step claim verification pipeline: claim decomposition, checkworthiness, query generation, retrieval, verification.
- Keeps decomposed claims traceable back to original text for contextual review.
- Presents a layered result UI: overall summary, claim-level analysis, evidence-level insight, detailed evidence breakdown.
- Surfaces supporting and refuting snippets instead of only a single coarse verdict.

#### Confirmed implications
- SourceTrace should keep queue/overview/claim/evidence layering rather than a flat verification screen.
- Claim review should preserve the mapping from original text span to decontextualized claim.
- Evidence review needs both support and contradiction visibility at the snippet level.

#### Impact on SourceTrace
- Strengthened the progressive-disclosure review workflow and claim-centric analyst surface.

---

### Source: `FACTS&EVIDENCE: An Interactive Tool for Transparent Fine-Grained Factual Verification of Machine-Generated Text`
Type: research paper / NAACL 2025 demo
Status: reviewed at abstract/interface level

#### Useful signals
- Presents per-claim, per-evidence decisions plus rationale in an interactive evidence panel.
- Makes source categories visible and user-controllable.
- Supports include/exclude evidence interactions and recomputation of aggregate credibility.

#### Confirmed implications
- SourceTrace should store per-claim, per-evidence decisions as first-class review artifacts.
- Analyst review benefits from an explicit evidence panel rather than hidden back-end scoring only.

#### Working hypothesis
- Interactive source-type toggles and recomputation are useful but can wait until after MVP.

#### Impact on SourceTrace
- Strengthened the design for a claim workspace with ranked evidence cards and later analyst-agency controls.

---

### Source: `Human-in-the-loop review workflow patterns` (cross-domain interface and workflow references)
Type: practitioner/reference pattern review
Status: reviewed at high level

#### Useful signals
- Effective review systems separate queue triage, case overview, focused review workspace, and audit trail.
- Review items need explicit states, ownership, escalation, and hold behavior.
- Human decisions are more usable when the interface shows recommended action, evidence, and required rationale in one place.

#### Confirmed implications
- SourceTrace MVP should expose a dedicated review queue and separate human review state from system verdict.
- Analyst overrides need note + timestamp + actor metadata.
- Report eligibility should depend on review completion and unresolved contradiction state, not only system output.

#### Impact on SourceTrace
- Strengthened the MVP workflow model around `ready_for_review -> in_review -> blocked/review_complete -> report_ready` with claim-level human dispositions.

---

## Current synthesis
### Confirmed now
- Evidence-first design remains the strongest direction.
- Claims and citations must be modeled explicitly.
- Hybrid retrieval is favored over naive vector-only search.
- Modular boundaries should exist before implementation, but remain lightweight.
- Contradictory evidence and report gating are important enough to influence the architecture now.
- Analyst review should be claim-focused and localized.
- A useful validation triad is emerging: `support`, `contradict`, `no evidence / insufficient evidence`.
- Source credibility should be treated as a separate signal from claim support.
- Review UX should follow progressive disclosure and evidence ranking, not full-detail overload by default.
- MVP analyst workflow should follow a layered structure: `review queue -> case overview -> claim workspace -> evidence detail`.
- Human review records should be distinct from model verdicts and should capture override rationale.
- OSINT-style credibility naming should separate `source_reliability` from `information_credibility`.

### Working hypotheses
- A case/document/chunk/claim/review/report model is sufficient for iteration 1.
- Graph support is a later concern, not a blocker for a quality MVP.
- Typed provenance relations are likely valuable later, but are not yet required for MVP.
- MVP credibility scoring can start as rule-based provisional bands with analyst override.
- MVP contradiction validation can likely be a lightweight claim decomposition + evidence matching + entailment verdict flow.
- MVP review can use explicit queue/item states without needing a heavy case-management platform.

### Do weryfikacji next
- whether `on_hold` should be mandatory from v1 or optional in the first UI cut
- whether queue ownership / `claim next item` should be explicit in MVP
- whether evidence-level exclusion controls belong in MVP or iteration 2
- parser stack and ingestion defaults
- retrieval/reranking depth for iteration 1
- report contract and claim-to-report gating rules

## Next research batch
1. Parser stack and ingestion defaults.
2. Retrieval/reranking depth for iteration 1.
3. Report contract and claim-to-report gating rules.
