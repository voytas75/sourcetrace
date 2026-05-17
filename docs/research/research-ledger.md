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

## Current synthesis
### Confirmed now
- Evidence-first design remains the strongest direction.
- Claims and citations must be modeled explicitly.
- Hybrid retrieval is favored over naive vector-only search.
- Modular boundaries should exist before implementation, but remain lightweight.
- Contradictory evidence and report gating are important enough to influence the architecture now.
- Analyst review should be claim-focused and localized.

### Working hypotheses
- A case/document/chunk/claim/review/report model is sufficient for iteration 1.
- Graph support is a later concern, not a blocker for a quality MVP.
- Typed provenance relations are likely valuable later, but are not yet required for MVP.

### Do weryfikacji next
- lightweight contradiction/entailment evaluation options suitable for MVP
- practical provenance schemas that are useful without overfitting to academic QA
- source credibility scoring approaches suitable for investigative workflows
- when reranking becomes worth its cost in the MVP roadmap

## Next research batch
1. Papers or implementations for lightweight entailment / contradiction validation.
2. Practical literature on source credibility scoring and conflict resolution.
3. Analyst workflow and review-interface material focused on triage efficiency and trust.
