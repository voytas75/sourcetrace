"""Runtime orchestration for the Deep Research lifecycle and bounded engine loop."""

from collections.abc import Callable
from functools import lru_cache
import json
from html import unescape as html_unescape
import re
import unicodedata
from typing import Any
from urllib.error import URLError
from dataclasses import dataclass, field, replace
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from sourcetrace.application.research import (
    ExternalPdfAnalyzer,
    ExtractedFinding,
    PdfIngestResult,
    ResearchExecution,
    ResearchExtractor,
    ResearchJobListOutcome,
    ResearchJobResultOutcome,
    ResearchJobStartOutcome,
    ResearchJobStartRequest,
    ResearchJobStatusOutcome,
    ResearchPlanner,
    ResearchPlanningAnalyzer,
    ResearchPdfIngestor,
    ResearchQueryGenerator,
    ResearchSearchAdapter,
    ResearchSynthesizer,
    SearchHit,
    SynthesisResult,
)
from sourcetrace.domain.research import (
    CompiledResearchArtifact,
    CompiledResearchArtifactLint,
    CompiledResearchArtifactLintStatus,
    CompiledResearchClaim,
    CompiledResearchEvidenceRef,
    EntityHypothesis,
    PlanningAnalysis,
    PlanningExecutionMode,
    ProblemAnalysis,
    ResearchBranchEvaluation,
    ResearchBranchProposal,
    ResearchBranchProposalSet,
    ResearchBranchScore,
    ResearchCompletionMode,
    ResearchReflection,
    ResearchComplexity,
    ResearchEvaluationArtifact,
    ResearchEvidencePack,
    ResearchEvaluationVerdict,
    ResearchExecutionPlan,
    ResearchExecutionPlanStep,
    ResearchFinding,
    ResearchJob,
    ResearchJobStatus,
    ResearchPhase,
    ResearchPlanStrategy,
    ResearchProgressEvent,
    ResearchQueryClass,
    ResearchResultArtifact,
    ResearchSource,
    ResearchStats,
)
from sourcetrace.storage.research import ResearchPersistence, create_in_memory_research_persistence




@dataclass(frozen=True)
class SubjectEntity:
    name: str
    type: str = "unknown"
    role: str = "other"
    confidence: float = 0.0


@dataclass(frozen=True)
class SubjectHint:
    kind: str
    value: str


@dataclass(frozen=True)
class SubjectSheet:
    query_summary: str = ""
    primary_subject: SubjectEntity = field(default_factory=lambda: SubjectEntity(name=""))
    related_entities: tuple[SubjectEntity, ...] = ()
    aliases: tuple[str, ...] = ()
    anchor_terms: tuple[str, ...] = ()
    proceeding_terms: tuple[str, ...] = ()
    must_have_signals: tuple[str, ...] = ()
    acceptable_adjacent_signals: tuple[str, ...] = ()
    disqualifying_signals: tuple[str, ...] = ()
    official_source_hints: tuple[SubjectHint, ...] = ()


class LlmSubjectSheetBuilder:
    """Build a compact subject sheet for research acceptance using LLM-first semantics."""

    def __init__(self, synthesize_text: Callable[[str], object]) -> None:
        self.synthesize_text = synthesize_text

    def __call__(self, *, query: str, planning_analysis: PlanningAnalysis | None = None) -> SubjectSheet:
        fallback = _fallback_subject_sheet(query=query, planning_analysis=planning_analysis)
        prompt = _build_subject_sheet_prompt(query=query, planning_analysis=planning_analysis, fallback=fallback)
        try:
            result = self.synthesize_text(prompt)
            text = getattr(result, 'text', '') if result is not None else ''
            payload = json.loads(text)
            validated = _subject_sheet_from_llm_payload(payload, fallback=fallback)
            if validated is not None:
                return validated
        except Exception:
            return fallback
        return fallback

class DeterministicPlanningAnalyzer:
    """Deterministic fallback planning-analysis builder from current heuristics."""

    def __call__(self, query: str) -> PlanningAnalysis:
        return _build_fallback_planning_analysis(query)


class LlmPlanningAnalyzer:
    """LLM-assisted planning-analysis builder with strict validation and fallback."""

    def __init__(self, synthesize_text: Callable[[str], object], *, fallback: ResearchPlanningAnalyzer | None = None) -> None:
        self.synthesize_text = synthesize_text
        self.fallback = fallback or DeterministicPlanningAnalyzer()

    def __call__(self, query: str) -> PlanningAnalysis:
        fallback = self.fallback(query)
        prompt = _build_planning_analysis_prompt(query, fallback=fallback)
        try:
            result = self.synthesize_text(prompt)
            text = getattr(result, 'text', '') if result is not None else ''
            payload = json.loads(text)
            validated = _planning_analysis_from_llm_payload(payload, query=query)
            if validated is None:
                return fallback
            return _merge_llm_planning_with_fallback(validated, fallback=fallback)
        except Exception:
            return fallback


class StubResearchPlanner:
    """Deterministic planner stub for the bounded planner-v2 slice."""

    def __call__(
        self,
        query: str,
        *,
        problem_analysis: ProblemAnalysis,
        planning_analysis: PlanningAnalysis | None = None,
    ) -> ResearchExecutionPlan:
        objective = (
            planning_analysis.goal
            if planning_analysis is not None and planning_analysis.goal
            else problem_analysis.goal or query
        )
        query_class = planning_analysis.query_class if planning_analysis is not None else problem_analysis.query_class
        if planning_analysis is not None and planning_analysis.execution_mode is PlanningExecutionMode.DISAMBIGUATE:
            return ResearchExecutionPlan(
                strategy=ResearchPlanStrategy.DIRECT_ANSWER,
                objective=objective,
                steps=(
                    ResearchExecutionPlanStep(
                        step_id="step-1",
                        kind="analyze",
                        objective="Disambiguate short or overloaded acronyms before locking onto one interpretation.",
                    ),
                    ResearchExecutionPlanStep(
                        step_id="step-2",
                        kind="search",
                        objective="Collect evidence that distinguishes the most plausible meanings in context.",
                        depends_on=("step-1",),
                    ),
                    ResearchExecutionPlanStep(
                        step_id="step-3",
                        kind="write",
                        objective="Answer cautiously and surface unresolved ambiguity explicitly.",
                        depends_on=("step-2",),
                    ),
                ),
            )
        if query_class is ResearchQueryClass.PROCEDURAL_ADMIN:
            strategy = ResearchPlanStrategy.PROCEDURAL_RESEARCH
            steps = (
                ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Find direct procedural or official task guidance."),
                ResearchExecutionPlanStep(step_id="step-2", kind="read", objective="Extract exact supported controls, scopes, and validation steps.", depends_on=("step-1",)),
                ResearchExecutionPlanStep(step_id="step-3", kind="write", objective="Write a bounded operator answer with explicit uncertainty.", depends_on=("step-2",)),
            )
        elif query_class is ResearchQueryClass.BROAD_CONCEPT:
            strategy = ResearchPlanStrategy.BROAD_RESEARCH
            steps = (
                ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Collect high-signal conceptual and technical sources."),
                ResearchExecutionPlanStep(step_id="step-2", kind="analyze", objective="Identify system shape, boundaries, and tradeoffs.", depends_on=("step-1",)),
                ResearchExecutionPlanStep(step_id="step-3", kind="write", objective="Synthesize a clear conceptual answer with open questions.", depends_on=("step-2",)),
            )
        elif query_class is ResearchQueryClass.CURRENT_NEWS:
            strategy = ResearchPlanStrategy.NEWS_RESEARCH
            steps = (
                ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather recent attributed developments."),
                ResearchExecutionPlanStep(step_id="step-2", kind="analyze", objective="Separate confirmed updates from weak or stale reporting.", depends_on=("step-1",)),
                ResearchExecutionPlanStep(step_id="step-3", kind="write", objective="Write a recency-aware summary with timeline caveats.", depends_on=("step-2",)),
            )
        elif query_class is ResearchQueryClass.MARKET_SYMBOL:
            strategy = ResearchPlanStrategy.MARKET_SCAN
            steps = (
                ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather instrument-specific market evidence for the requested window."),
                ResearchExecutionPlanStep(step_id="step-2", kind="analyze", objective="Check signal consistency without mixing unlike instruments.", depends_on=("step-1",)),
                ResearchExecutionPlanStep(step_id="step-3", kind="write", objective="Report bounded market observations and missing checks.", depends_on=("step-2",)),
            )
        else:
            strategy = ResearchPlanStrategy.DIRECT_ANSWER
            steps = (
                ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather the strongest relevant evidence."),
                ResearchExecutionPlanStep(step_id="step-2", kind="write", objective="Answer directly and surface missing verification.", depends_on=("step-1",)),
            )
        return ResearchExecutionPlan(
            strategy=strategy,
            objective=objective,
            steps=steps,
        )


class StubQueryGenerator:
    """Deterministic query generator stub with light domain-aware shaping."""

    def __call__(
        self,
        plan: ResearchExecutionPlan,
        *,
        round_number: int,
        planning_analysis: PlanningAnalysis | None = None,
    ) -> tuple[str, ...]:
        objective = plan.objective.strip()
        normalized = objective.lower()
        if plan.strategy is ResearchPlanStrategy.MARKET_SCAN or _looks_like_market_query(normalized):
            symbol = _extract_market_symbol(objective) or objective
            if round_number == 1:
                return (
                    objective,
                    f"{symbol} price last 7 days",
                    f"{symbol} technical analysis tradingview",
                )
            return (
                f"{symbol} historical data",
                f"{symbol} exchange market",
                f"{symbol} analytics volume open interest",
            )
        planning_queries = _planning_aware_query_variants(
            objective=objective,
            round_number=round_number,
            planning_analysis=planning_analysis,
        )
        if planning_queries:
            return planning_queries
        if plan.strategy is ResearchPlanStrategy.PROCEDURAL_RESEARCH or _procedural_query_bias(normalized):
            if round_number == 1:
                return _procedural_query_variants(objective)
            return (
                f'site:learn.microsoft.com {objective}',
                f'{objective} Microsoft Learn official documentation',
                f'{objective} Configuration Manager documentation',
            )
        if plan.strategy is ResearchPlanStrategy.NEWS_RESEARCH and round_number > 1:
            return (
                f"{objective} latest developments",
                f"{objective} this week",
                f"{objective} official update",
            )
        if round_number == 1:
            return (objective,)
        if plan.strategy is ResearchPlanStrategy.DIRECT_ANSWER:
            if any(token in normalized for token in ('mental health', 'zdrowie psychiczne', 'wellbeing', 'dobrostan')) and any(token in normalized for token in ('remote', 'hybrid', 'praca zdalna', 'zdaln')):
                return (
                    f"{objective} longitudinal study after 2023",
                    f"{objective} survey report after 2023",
                    f"{objective} remote hybrid work mental health study",
                )
            return (
                f"{objective} report study",
                f"{objective} analysis findings",
                f"{objective} workplace health research",
            )
        return (objective,)


class LlmQueryGenerator:
    """LLM-assisted query refinement used only after weak/empty non-procedural search."""

    def __init__(self, synthesize_text: Callable[[str], object]) -> None:
        self.synthesize_text = synthesize_text

    def __call__(self, query: str) -> tuple[str, ...]:
        prompt = (
            "You generate web search queries for research. "
            "Return strict JSON with key 'queries' as an array of 2-4 concise search queries. "
            "Do not include explanations. "
            "Preserve the user's language. "
            "Prefer query variants suitable for web/community knowledge when the topic is not procedural/admin. "
            f"User query: {query}"
        )
        try:
            result = self.synthesize_text(prompt)
            text = getattr(result, 'text', '') if result is not None else ''
            payload = json.loads(text)
            queries = payload.get('queries') if isinstance(payload, dict) else None
            if isinstance(queries, list):
                cleaned = tuple(str(item).strip() for item in queries if str(item).strip())
                if cleaned:
                    return cleaned[:4]
        except Exception:
            return ()
        return ()


def _planning_aware_query_variants(
    *,
    objective: str,
    round_number: int,
    planning_analysis: PlanningAnalysis | None,
) -> tuple[str, ...]:
    if planning_analysis is None:
        return ()
    if planning_analysis.query_class not in {ResearchQueryClass.CURRENT_NEWS, ResearchQueryClass.GENERAL, ResearchQueryClass.PROCEDURAL_ADMIN}:
        return ()
    if (
        planning_analysis.query_class is ResearchQueryClass.GENERAL
        and not _planning_prefers_official_sources(planning_analysis)
    ):
        return ()
    if (
        planning_analysis.query_class is ResearchQueryClass.PROCEDURAL_ADMIN
        and not _planning_prefers_official_public_law_sources(planning_analysis, objective=objective)
    ):
        return ()

    primary_entity = _planning_primary_entity_name(planning_analysis) or objective
    tax_queries = _planning_tax_official_query_variants(
        objective=objective,
        primary_entity=primary_entity,
        planning_analysis=planning_analysis,
    )
    if tax_queries:
        return tax_queries
    institutional_queries = _planning_audit_institutional_query_variants(
        objective=objective,
        round_number=round_number,
        primary_entity=primary_entity,
        planning_analysis=planning_analysis,
    )
    if institutional_queries:
        return institutional_queries
    official_queries = _planning_official_query_variants(
        objective=objective,
        primary_entity=primary_entity,
        planning_analysis=planning_analysis,
    )
    focus_queries = _planning_focus_query_variants(
        objective=objective,
        primary_entity=primary_entity,
        planning_analysis=planning_analysis,
    )
    fallback_queries = _planning_fallback_query_variants(
        objective=objective,
        round_number=round_number,
        planning_analysis=planning_analysis,
    )

    entity_types = {
        (hypothesis.entity_type or "").strip().lower()
        for hypothesis in planning_analysis.entity_hypotheses
        if (hypothesis.canonical_name or hypothesis.surface_form).strip()
    }
    hospital_like = any(entity_type in {"hospital", "clinic", "healthcare"} for entity_type in entity_types)
    city_like = any(entity_type in {"city", "municipality", "local_government"} for entity_type in entity_types)
    regulator_like = any(entity_type in {"regulator", "audit_body", "watchdog"} for entity_type in entity_types)

    def _is_domain_query(query: str) -> bool:
        lowered = query.lower()
        return "site:" in lowered or "rzecznik" in lowered

    def _is_polish_official_phrase(query: str) -> bool:
        lowered = query.lower()
        return any(token in lowered for token in ("komunikat", "stanowisko", "informacja o wynikach kontroli"))

    def _bucketed_query_selection(*, limit: int, include_objective: bool) -> tuple[str, ...]:
        official_bucket: list[str] = []
        domain_bucket: list[str] = []
        phrase_bucket: list[str] = []
        focus_bucket: list[str] = []
        fallback_bucket: list[str] = []

        for query in official_queries:
            if _is_domain_query(query):
                domain_bucket.append(query)
            elif _is_polish_official_phrase(query):
                phrase_bucket.append(query)
            else:
                official_bucket.append(query)
        for query in focus_queries:
            if _is_domain_query(query):
                domain_bucket.append(query)
            elif _is_polish_official_phrase(query):
                phrase_bucket.append(query)
            elif "statement" in query.lower() or "update" in query.lower():
                official_bucket.append(query)
            else:
                focus_bucket.append(query)
        fallback_bucket.extend(fallback_queries)

        reserved_domain = 1 if (hospital_like or city_like or regulator_like) else 0
        reserved_phrase = 1 if (hospital_like or city_like or regulator_like or phrase_bucket) else 0
        reserved_official = 1 if official_bucket else 0

        selected: list[str] = []
        seen: set[str] = set()

        def take_one(bucket: list[str]) -> None:
            for item in bucket:
                key = item.strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                selected.append(item)
                return

        if include_objective:
            key = objective.strip().lower()
            if key:
                seen.add(key)
                selected.append(objective)

        if reserved_official:
            take_one(official_bucket)
        if reserved_domain:
            take_one(domain_bucket)
        if reserved_phrase:
            take_one(phrase_bucket)

        priority_order: list[list[str]] = []
        if regulator_like:
            priority_order = [official_bucket, domain_bucket, phrase_bucket, focus_bucket, fallback_bucket]
        elif hospital_like or city_like:
            priority_order = [official_bucket, domain_bucket, phrase_bucket, focus_bucket, fallback_bucket]
        else:
            priority_order = [official_bucket, phrase_bucket, domain_bucket, focus_bucket, fallback_bucket]

        for bucket in priority_order:
            for item in bucket:
                if len(selected) >= limit:
                    return tuple(selected[:limit])
                key = item.strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                selected.append(item)

        return tuple(selected[:limit])

    if round_number == 1:
        return _bucketed_query_selection(limit=8, include_objective=True)

    if planning_analysis.query_class is ResearchQueryClass.GENERAL and _planning_prefers_official_sources(planning_analysis) and (hospital_like or city_like or regulator_like):
        all_candidates = _dedupe_query_variants(tuple((*official_queries, *focus_queries, *fallback_queries)))
        domain_candidates = [query for query in all_candidates if 'site:nik.gov.pl' in query.lower() or 'site:gov.pl' in query.lower() or 'site:um.warszawa.pl' in query.lower() or 'site:bip.warszawa.pl' in query.lower()]
        findings_candidates = [query for query in all_candidates if any(token in query.lower() for token in ('informacja o wynikach kontroli', 'wyniki kontroli', 'official findings'))]
        report_candidates = [query for query in all_candidates if 'raport' in query.lower()]
        communications_candidates = [query for query in all_candidates if any(token in query.lower() for token in ('komunikat', 'stanowisko', 'official statement', 'official update'))]
        selected = _dedupe_query_variants(tuple(
            (*domain_candidates[:1], *findings_candidates[:1], *report_candidates[:1], *communications_candidates[:1], *all_candidates)
        ))
        if selected:
            return selected[:6]

    return _bucketed_query_selection(limit=6, include_objective=False)


def _planning_prefers_official_public_law_sources(planning_analysis: PlanningAnalysis, *, objective: str = '') -> bool:
    if not _planning_prefers_official_sources(planning_analysis):
        return False
    raw = ' '.join((objective, planning_analysis.goal, *planning_analysis.focus_areas, *planning_analysis.constraints)).lower()
    return any(token in raw for token in (
        'podat', 'podatk', 'mf', 'kas', 'ministerstwo finans', 'podatki.gov.pl', 'gov.pl', 'biznes.gov.pl', 'urzęd', 'urzed', 'najem', 'wynajem',
    ))


def _planning_prefers_official_sources(planning_analysis: PlanningAnalysis) -> bool:
    constraints = _normalized_planning_constraints(planning_analysis.constraints)
    focus_areas = _normalized_planning_focus_areas(planning_analysis.focus_areas)
    raw_constraints = tuple(str(item).lower() for item in planning_analysis.constraints)
    raw_focus_areas = tuple(str(item).lower() for item in planning_analysis.focus_areas)
    return (
        "prefer_official_sources_first" in constraints
        or any(token in item for item in focus_areas for token in ("official", "statement", "position", "findings", "recommend", "announcements"))
        or any(any(token in item for token in ("oficjal", "urzęd", "urzed", "nik", "dokument", "komunikat", "raport", "wynikach kontroli")) for item in raw_constraints)
        or any(any(token in item for token in ("oficjal", "komunikat", "raport", "wynikach kontroli", "ustalenia_nik", "pokontrol")) for item in raw_focus_areas)
    )


def _normalized_planning_focus_areas(focus_areas: tuple[str, ...]) -> tuple[str, ...]:
    canonical_map = {
        "official_findings": "official_findings",
        "official findings": "official_findings",
        "ustalenia": "official_findings",
        "ustalenia pokontrolne": "official_findings",
        "wyniki kontroli": "official_findings",
        "control findings": "official_findings",
        "hospital_position": "hospital_position",
        "hospital statement": "hospital_position",
        "stanowisko szpitala": "hospital_position",
        "oficjalne stanowisko szpitala": "hospital_position",
        "city_position": "city_position",
        "city statement": "city_position",
        "stanowisko miasta": "city_position",
        "oficjalne stanowisko miasta": "city_position",
        "regulator_position": "regulator_position",
        "regulator statement": "regulator_position",
        "stanowisko regulatora": "regulator_position",
        "official_position": "official_position",
        "official position": "official_position",
        "oficjalne stanowiska": "official_position",
        "official statements": "official_position",
        "timeline": "timeline",
        "chronologia": "timeline",
        "chronologia komunikatów": "timeline",
        "recommendations": "recommendations",
        "recommendation": "recommendations",
        "zalecenia": "recommendations",
        "zalecenia pokontrolne": "recommendations",
        "post inspection recommendations": "recommendations",
        "post-inspection recommendations": "recommendations",
        "announcements": "announcements",
        "announcement": "announcements",
        "official_announcements": "announcements",
        "communications": "announcements",
        "komunikaty": "announcements",
        "komunikat": "announcements",
        "chronology of announcements": "announcements",
        "investigation_status": "investigation_status",
        "status kontroli": "investigation_status",
        "status postępowania": "investigation_status",
        "recent_developments": "recent_developments",
        "latest developments": "recent_developments",
        "najnowsze informacje": "recent_developments",
        "source_recency": "source_recency",
        "this week": "source_recency",
        "recent sources": "source_recency",
    }
    normalized: list[str] = []
    seen: set[str] = set()
    for item in focus_areas:
        raw = str(item).strip()
        if not raw:
            continue
        lowered = raw.lower().replace("-", " ").replace("_", " ")
        lowered = " ".join(lowered.split())
        canonical = canonical_map.get(raw.lower(), canonical_map.get(lowered, raw.lower().replace(" ", "_")))
        if canonical in seen:
            continue
        seen.add(canonical)
        normalized.append(canonical)
    return tuple(normalized)


def _normalized_planning_constraints(constraints: tuple[str, ...]) -> tuple[str, ...]:
    canonical_map = {
        "prefer_official_sources_first": "prefer_official_sources_first",
        "prefer official sources first": "prefer_official_sources_first",
        "prefer official/institutional sources first": "prefer_official_sources_first",
        "prefer institutional sources first": "prefer_official_sources_first",
        "official sources first": "prefer_official_sources_first",
        "najpierw źródła oficjalne": "prefer_official_sources_first",
        "najpierw zrodla oficjalne": "prefer_official_sources_first",
        "prefer_primary_sources": "prefer_official_sources_first",
    }
    normalized: list[str] = []
    seen: set[str] = set()
    for item in constraints:
        raw = str(item).strip()
        if not raw:
            continue
        lowered = raw.lower().replace("-", " ").replace("_", " ")
        lowered = " ".join(lowered.split())
        canonical = canonical_map.get(raw.lower(), canonical_map.get(lowered, raw.lower().replace(" ", "_")))
        if canonical in seen:
            continue
        seen.add(canonical)
        normalized.append(canonical)
    return tuple(normalized)


def _planning_primary_entity_name(planning_analysis: PlanningAnalysis) -> str | None:
    for hypothesis in planning_analysis.entity_hypotheses:
        name = (hypothesis.canonical_name or hypothesis.surface_form).strip()
        if name:
            return name
    return None


def _planning_tax_official_query_variants(
    *,
    objective: str,
    primary_entity: str,
    planning_analysis: PlanningAnalysis,
) -> tuple[str, ...]:
    if planning_analysis.query_class not in {ResearchQueryClass.GENERAL, ResearchQueryClass.PROCEDURAL_ADMIN}:
        return ()
    if not _planning_prefers_official_public_law_sources(planning_analysis, objective=objective):
        return ()

    raw_context = " ".join(
        (
            objective,
            planning_analysis.goal,
            *tuple(str(item) for item in planning_analysis.focus_areas),
            *tuple(str(item) for item in planning_analysis.constraints),
            primary_entity,
        )
    ).lower()
    tax_like = any(token in raw_context for token in (
        'podat', 'podatk', 'ryczałt', 'ryczalt', 'najem', 'wynajem', 'pit', 'kas', 'mf', 'ministerstwo finans', 'podatki.gov.pl'
    ))
    if not tax_like:
        return ()

    subject = primary_entity or objective
    return _dedupe_query_variants((
        objective,
        f'site:podatki.gov.pl {subject}',
        f'site:podatki.gov.pl {subject} ryczałt',
        f'site:podatki.gov.pl {subject} najem prywatny',
        f'site:gov.pl {subject} Ministerstwo Finansów',
        f'site:biznes.gov.pl {subject}',
        f'Ministerstwo Finansów {subject}',
        f'KAS {subject}',
        f'{subject} ryczałt podatki.gov.pl',
    ))[:8]


def _planning_audit_institutional_query_variants(
    *,
    objective: str,
    round_number: int,
    primary_entity: str,
    planning_analysis: PlanningAnalysis,
) -> tuple[str, ...]:
    if planning_analysis.query_class is not ResearchQueryClass.GENERAL:
        return ()
    if not _planning_prefers_official_sources(planning_analysis):
        return ()

    entity_names = [
        (hypothesis.canonical_name or hypothesis.surface_form).strip()
        for hypothesis in planning_analysis.entity_hypotheses
        if (hypothesis.canonical_name or hypothesis.surface_form).strip()
    ]
    entity_types = {
        (hypothesis.entity_type or "").strip().lower()
        for hypothesis in planning_analysis.entity_hypotheses
        if (hypothesis.canonical_name or hypothesis.surface_form).strip()
    }
    audit_types = {"audit_body", "regulator", "watchdog"}

    raw_context = " ".join(
        (
            objective,
            planning_analysis.goal,
            *tuple(str(item) for item in planning_analysis.focus_areas),
            *tuple(str(item) for item in planning_analysis.constraints),
            *entity_names,
            *tuple(entity_types),
        )
    ).lower()
    audit_like = (
        any(entity_type in audit_types for entity_type in entity_types)
        or any(token in raw_context for token in ("nik", "izba kontroli", "wyniki kontroli", "informacja o wynikach kontroli", "pokontrol", "ustalenia_nik"))
    )
    if not audit_like:
        return ()

    def _is_nik_like(name: str) -> bool:
        lowered = name.lower()
        return "nik" in lowered or "izba kontroli" in lowered

    audit_name = next(
        (
            name
            for hypothesis in planning_analysis.entity_hypotheses
            for name in ((hypothesis.canonical_name or hypothesis.surface_form).strip(),)
            if name
            and (
                (hypothesis.entity_type or "").strip().lower() in audit_types
                or _is_nik_like(name)
            )
        ),
        primary_entity,
    )
    subject_name = next(
        (
            name
            for hypothesis in planning_analysis.entity_hypotheses
            for name in ((hypothesis.canonical_name or hypothesis.surface_form).strip(),)
            if name
            and not _is_nik_like(name)
            and (hypothesis.entity_type or "").strip().lower() in {
                "hospital",
                "clinic",
                "healthcare",
                "city",
                "municipality",
                "local_government",
                "institution",
            }
        ),
        "",
    )

    query_subject_parts: list[str] = []
    for part in (audit_name.strip(), subject_name.strip()):
        if part and part.lower() not in {item.lower() for item in query_subject_parts}:
            query_subject_parts.append(part)
    query_subject = " ".join(query_subject_parts) or primary_entity or objective
    subject_only = subject_name.strip() or primary_entity or objective
    report_like_terms = (
        'informacja o wynikach kontroli',
        'wyniki kontroli',
        'raport',
        'pdf',
        'plik pdf',
        'komunikat',
    )
    if round_number == 1:
        return _dedupe_query_variants(
            (
                objective,
                f'site:nik.gov.pl "{subject_only}"',
                f'site:nik.gov.pl "{subject_only}" "informacja o wynikach kontroli"',
                f'site:nik.gov.pl "{subject_only}" "wyniki kontroli"',
                f'site:nik.gov.pl "{subject_only}" raport',
                f'site:nik.gov.pl "{subject_only}" pdf',
                f'site:nik.gov.pl "{query_subject}"',
                *tuple(f'"{subject_only}" {term}' for term in report_like_terms[:2]),
            )
        )[:8]
    return _dedupe_query_variants(
        (
            f'site:nik.gov.pl "{subject_only}" "informacja o wynikach kontroli"',
            f'site:nik.gov.pl "{subject_only}" "wyniki kontroli"',
            f'site:nik.gov.pl "{subject_only}" raport',
            f'site:nik.gov.pl "{subject_only}" pdf',
            f'site:nik.gov.pl "{query_subject}"',
            f'"{subject_only}" raport NIK',
        )
    )[:6]


def _planning_official_query_variants(
    *,
    objective: str,
    primary_entity: str,
    planning_analysis: PlanningAnalysis,
) -> tuple[str, ...]:
    queries: list[str] = []
    entity_types = {
        (hypothesis.entity_type or "").strip().lower()
        for hypothesis in planning_analysis.entity_hypotheses
        if (hypothesis.canonical_name or hypothesis.surface_form).strip()
    }
    prefers_official = _planning_prefers_official_sources(planning_analysis)
    hospital_like = any(entity_type in {"hospital", "clinic", "healthcare"} for entity_type in entity_types)
    city_like = any(entity_type in {"city", "municipality", "local_government"} for entity_type in entity_types)
    regulator_like = any(entity_type in {"regulator", "audit_body", "watchdog", "institution"} for entity_type in entity_types) or any(token in primary_entity.lower() for token in ('nik', 'izba kontroli'))

    if prefers_official:
        queries.extend(
            (
                f"{primary_entity} official statement",
                f"{primary_entity} official findings",
            )
        )
    if hospital_like:
        queries.extend(
            (
                f"{primary_entity} site:gov.pl",
                f"{primary_entity} site:szpitale.mazovia.pl",
                f"{primary_entity} hospital statement",
                f"{primary_entity} rzecznik",
            )
        )
    if city_like:
        queries.extend(
            (
                f"{primary_entity} site:um.warszawa.pl",
                f"{primary_entity} site:bip.warszawa.pl",
                f"{primary_entity} city statement",
                f"{primary_entity} urząd miasta komunikat",
            )
        )
    if regulator_like:
        queries.extend(
            (
                f"{primary_entity} site:nik.gov.pl",
                f"{primary_entity} site:gov.pl",
                f"{primary_entity} informacja o wynikach kontroli",
                f"{primary_entity} regulator statement",
                f"{primary_entity} komunikat prasowy",
            )
        )
    if any(token in primary_entity.lower() for token in ('nik', 'izba kontroli')):
        queries.extend(
            (
                f"site:nik.gov.pl {objective}",
                f"site:gov.pl {primary_entity}",
                f"{primary_entity} raport",
                f"{primary_entity} wyniki kontroli",
            )
        )
    if prefers_official and not entity_types:
        queries.extend((f"{objective} site:gov.pl", f"{objective} site:bip.gov.pl"))
    if prefers_official:
        tail_queries: list[str] = []
        if regulator_like:
            tail_queries.extend(
                (
                    f"{primary_entity} stanowisko",
                    f"{primary_entity} oficjalne stanowisko",
                )
            )
        elif hospital_like or city_like:
            tail_queries.extend(
                (
                    f"{primary_entity} komunikat",
                    f"{primary_entity} stanowisko",
                )
            )
        else:
            tail_queries.extend(
                (
                    f"{primary_entity} komunikat",
                    f"{primary_entity} stanowisko",
                    f"{primary_entity} oficjalny komunikat",
                    f"{primary_entity} oficjalne stanowisko",
                )
            )
        tail_queries.append(f"{primary_entity} official update")
        queries.extend(tuple(tail_queries))
    return tuple(queries)


def _planning_focus_query_variants(
    *,
    objective: str,
    primary_entity: str,
    planning_analysis: PlanningAnalysis,
) -> tuple[str, ...]:
    queries: list[str] = []
    for focus_area in _normalized_planning_focus_areas(planning_analysis.focus_areas):
        lowered = focus_area.lower()
        if lowered == "recent_developments":
            queries.append(f"{objective} latest developments")
        elif lowered == "timeline":
            queries.extend((f"{objective} timeline", f"{primary_entity} chronology", f"{primary_entity} chronologia komunikatów"))
        elif lowered == "source_recency":
            queries.append(f"{objective} this week")
        elif lowered == "official_findings":
            queries.extend((f"{primary_entity} official findings", f"{primary_entity} report", f"{primary_entity} ustalenia", f"{primary_entity} wyniki kontroli"))
        elif lowered == "hospital_position":
            queries.extend((f"{primary_entity} hospital statement", f"{primary_entity} stanowisko szpitala"))
        elif lowered == "city_position":
            queries.extend((f"{primary_entity} city statement", f"{primary_entity} stanowisko miasta"))
        elif lowered == "regulator_position":
            queries.extend((f"{primary_entity} regulator statement", f"{primary_entity} stanowisko"))
        elif lowered == "official_position":
            queries.extend((f"{primary_entity} official statement", f"{primary_entity} oficjalne stanowisko"))
        elif lowered == "investigation_status":
            queries.extend((f"{objective} investigation update", f"{primary_entity} kontrola zalecenia"))
        elif lowered == "recommendations":
            queries.extend((f"{primary_entity} zalecenia pokontrolne", f"{primary_entity} recommendations", f"{primary_entity} rekomendacje"))
        elif lowered == "announcements":
            queries.extend((f"{primary_entity} komunikaty", f"{primary_entity} announcements", f"{primary_entity} komunikat prasowy"))
        else:
            queries.append(f"{objective} {focus_area.replace('_', ' ')}")
    return tuple(queries)


def _planning_fallback_query_variants(
    *,
    objective: str,
    round_number: int,
    planning_analysis: PlanningAnalysis,
) -> tuple[str, ...]:
    queries: list[str] = []
    entity_names = [
        (hypothesis.canonical_name or hypothesis.surface_form).strip()
        for hypothesis in planning_analysis.entity_hypotheses
        if (hypothesis.canonical_name or hypothesis.surface_form).strip()
    ]
    primary_entity = entity_names[0] if entity_names else objective
    entity_types = {
        (hypothesis.entity_type or '').strip().lower()
        for hypothesis in planning_analysis.entity_hypotheses
        if (hypothesis.canonical_name or hypothesis.surface_form).strip()
    }
    hospital_like = any(entity_type in {'hospital', 'clinic', 'healthcare'} for entity_type in entity_types)
    city_like = any(entity_type in {'city', 'municipality', 'local_government'} for entity_type in entity_types)
    regulator_like = any(entity_type in {'regulator', 'audit_body', 'watchdog', 'institution'} for entity_type in entity_types) or any(token in primary_entity.lower() for token in ('nik', 'izba kontroli'))
    prefers_official = _planning_prefers_official_sources(planning_analysis)

    if round_number > 1 and planning_analysis.query_class is ResearchQueryClass.GENERAL and prefers_official and (hospital_like or city_like or regulator_like):
        queries.extend(
            (
                f"{primary_entity} raport",
                f"{primary_entity} wyniki kontroli",
                f"site:nik.gov.pl {primary_entity}",
            )
        )
        if city_like:
            queries.append(f"site:um.warszawa.pl {primary_entity}")
        if hospital_like:
            queries.append(f"{primary_entity} komunikat")
        return tuple(queries)

    if round_number > 1:
        queries.extend(
            (
                f"{objective} latest developments",
                f"{objective} this week",
            )
        )
    elif planning_analysis.query_class is ResearchQueryClass.CURRENT_NEWS:
        queries.append(f"{objective} latest developments")
    return tuple(queries)


def _dedupe_query_variants(queries: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for query in queries:
        cleaned = query.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return tuple(deduped)


def _query_generation_trace(*, plan: ResearchExecutionPlan, planning_analysis: PlanningAnalysis | None, round_number: int) -> dict[str, object]:
    objective = plan.objective.strip()
    normalized = objective.lower()
    trace: dict[str, object] = {
        'strategy': plan.strategy.value,
        'round_number': round_number,
        'objective': objective,
    }
    if planning_analysis is None:
        trace['path'] = 'legacy_query_generator_no_planning_analysis'
        return trace
    prefers_official = _planning_prefers_official_sources(planning_analysis)
    procedural_bias = _procedural_query_bias(normalized)
    planning_queries = _planning_aware_query_variants(
        objective=objective,
        round_number=round_number,
        planning_analysis=planning_analysis,
    )
    trace.update({
        'query_class': planning_analysis.query_class.value,
        'prefers_official_sources': prefers_official,
        'procedural_bias': procedural_bias,
        'planning_aware_query_count': len(planning_queries),
        'planning_aware_preview': list(planning_queries[:3]),
    })
    if planning_queries:
        trace['path'] = 'planning_aware'
        return trace
    if plan.strategy is ResearchPlanStrategy.PROCEDURAL_RESEARCH or procedural_bias:
        trace['path'] = 'procedural_branch'
        return trace
    if plan.strategy is ResearchPlanStrategy.NEWS_RESEARCH and round_number > 1:
        trace['path'] = 'news_branch'
        return trace
    if round_number == 1:
        trace['path'] = 'round1_objective_only'
        return trace
    if plan.strategy is ResearchPlanStrategy.DIRECT_ANSWER:
        trace['path'] = 'direct_answer_branch'
        return trace
    trace['path'] = 'fallback_objective_only'
    return trace


def _generate_queries(
    query_generator: ResearchQueryGenerator,
    plan: ResearchExecutionPlan,
    *,
    round_number: int,
    planning_analysis: PlanningAnalysis | None,
) -> tuple[str, ...]:
    if planning_analysis is None:
        return query_generator(plan, round_number=round_number)
    try:
        return query_generator(
            plan,
            round_number=round_number,
            planning_analysis=planning_analysis,
        )
    except TypeError as exc:
        if "planning_analysis" not in str(exc):
            raise
        return query_generator(plan, round_number=round_number)


def _provider_candidate_diagnostics(*, hits: tuple[SearchHit, ...], query: str, subject_sheet: SubjectSheet | None = None, planning_analysis: PlanningAnalysis | None = None) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    for hit in hits:
        diagnostics.append(
            {
                'url': hit.url,
                'title': hit.title,
                'source_type': _source_type(hit.url, hit.title),
                'general_relevance': _general_relevance_score(query=query, hit=hit),
                'entity_match': _entity_match_score(query=query, hit=hit, subject_sheet=subject_sheet, planning_analysis=planning_analysis),
                'listing_page': _looks_like_listing_page(hit),
                'weak_general_source': _looks_like_weak_general_source(hit),
                'relevant_hit': _is_relevant_hit(query=query, hit=hit, subject_sheet=subject_sheet, planning_analysis=planning_analysis),
            }
        )
    return diagnostics


def _looks_like_pdf_artifact(hit: SearchHit) -> bool:
    lowered_url = hit.url.lower()
    lowered_title = hit.title.lower()
    return lowered_url.endswith('.pdf') or '/pobierz,' in lowered_url or 'pdf' in lowered_url or lowered_title.endswith('.pdf')


def _triage_official_pdf_candidate(*, query: str, hit: SearchHit) -> tuple[str, str]:
    lowered = _normalized_match_text(f"{hit.title} {hit.url} {hit.snippet}")
    if not lowered:
        return 'irrelevant', 'empty_pdf_signal'
    entity_match = _entity_match_score(query=query, hit=hit)
    anchors = _subject_anchor_variants(query)
    compact = lowered.replace(' ', '')
    anchor_match = any(anchor in lowered or anchor in compact for anchor in anchors)
    subject_like_phrases = [phrase for phrase in _query_surface_candidate_phrases(query) if len(phrase.split()) >= 2]
    phrase_match = any(phrase in lowered or phrase.replace(' ', '') in compact for phrase in subject_like_phrases)
    if not phrase_match:
        query_tokens = {token for phrase in subject_like_phrases for token in phrase.split() if len(token) >= 5}
        hit_tokens = {token for token in lowered.split() if len(token) >= 5}
        overlap = len(query_tokens & hit_tokens)
        phrase_match = overlap >= 2
    if anchor_match and entity_match >= 5:
        return 'relevant', 'subject_anchor_match'
    if phrase_match and entity_match >= 3:
        return 'relevant', 'subject_phrase_match'
    if entity_match >= 3 and (anchor_match or phrase_match):
        return 'uncertain', 'partial_subject_match'
    return 'irrelevant', 'no_subject_signal'


def _pdf_ingest_summary(result: PdfIngestResult) -> str:
    findings = '; '.join(result.key_findings[:3]) if result.key_findings else 'no_key_findings'
    pages = ','.join(str(page) for page in result.evidence_pages[:5]) if result.evidence_pages else 'n/a'
    return (
        f"scope={result.document_scope}; entity={result.entity_match_summary}; "
        f"confidence={result.confidence:.2f}; pages={pages}; findings={findings}"
    )


class StubPdfIngestor:
    """Deterministic placeholder backend for the PDF ingest seam."""

    def __call__(
        self,
        *,
        query: str,
        url: str,
        title: str,
        triage_verdict: str,
    ) -> PdfIngestResult:
        subject_hint = 'official pdf candidate'
        if 'nik.gov.pl' in url.lower():
            subject_hint = 'NIK official PDF candidate'
        relevant = triage_verdict in {'relevant', 'uncertain'}
        return PdfIngestResult(
            relevant=relevant,
            confidence=0.55 if triage_verdict == 'uncertain' else 0.75,
            document_scope=subject_hint,
            entity_match_summary=_normalized_match_text(query)[:120] or title,
            key_findings=(
                'stub_pdf_ingest_backend',
                'requires_real_pdf_backend_for_full_evidence',
            ),
            evidence_pages=(),
        )


class ExternalPdfAnalyzerAdapter:
    """Bridge a repo-external PDF analyzer into the research PDF ingest seam."""

    def __init__(self, analyzer: ExternalPdfAnalyzer) -> None:
        self.analyzer = analyzer

    def __call__(
        self,
        *,
        query: str,
        url: str,
        title: str,
        triage_verdict: str,
    ) -> PdfIngestResult:
        return self.analyzer(
            query=query,
            url=url,
            title=title,
            triage_verdict=triage_verdict,
        )


from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen




class ResearchSearchError(RuntimeError):
    """Raised when a provider-backed search adapter cannot return usable results."""


class SearxNGSearchAdapter:
    """HTTP-backed SearxNG adapter normalized to ResearchSearchAdapter output."""

    provider_name = "searxng"

    def __init__(
        self,
        *,
        base_url: str,
        count: int = 3,
        language: str = "en",
        timeout_seconds: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.count = count
        self.language = language
        self.timeout_seconds = timeout_seconds

    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        per_query_count = self.count if round_number <= 1 else max(self.count, 6)
        hits: list[SearchHit] = []
        seen: set[str] = set()
        try:
            for query in queries:
                for item in self._fetch(query, count=per_query_count):
                    url = str(item.get("url") or "").strip()
                    title = str(item.get("title") or query).strip() or query
                    snippet = str(item.get("content") or item.get("snippet") or "").strip()
                    if not url or url in seen:
                        continue
                    seen.add(url)
                    hits.append(SearchHit(url=url, title=title, snippet=snippet))
        except (OSError, TimeoutError, URLError, ValueError) as exc:
            self.last_provider_names = (self.provider_name,)
            raise ResearchSearchError(f"SearxNG search failed: {type(exc).__name__}: {exc}") from exc
        self.last_provider_names = (self.provider_name,)
        return tuple(hits)

    def _fetch(self, query: str, *, count: int | None = None) -> list[dict[str, object]]:
        params = urlencode({
            "q": query,
            "format": "json",
            "language": self.language,
        })
        request = Request(
            f"{self.base_url}/search?{params}",
            headers={"Accept": "application/json", "User-Agent": "SourceTrace/0.1"},
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = __import__("json").loads(response.read().decode("utf-8"))
        results = payload.get("results")
        if not isinstance(results, list):
            return []
        limit = count if count is not None else self.count
        return [item for item in results[: limit] if isinstance(item, dict)]

class WebSearchBackedSearchAdapter:
    """Small real search adapter using a caller-supplied web search function."""

    provider_name = "web_search"

    def __init__(
        self,
        search_web: Callable[..., list[dict[str, object]]],
        *,
        count: int = 3,
    ) -> None:
        self.search_web = search_web
        self.count = count

    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        per_query_count = self.count if round_number <= 1 else max(self.count, 6)
        hits: list[SearchHit] = []
        seen: set[str] = set()
        for query in queries:
            for item in self.search_web(query, count=self.count):
                url = str(item.get("url") or "").strip()
                title = str(item.get("title") or query).strip() or query
                snippet = str(item.get("snippet") or item.get("description") or "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                hits.append(SearchHit(url=url, title=title, snippet=snippet))
        self.last_provider_names = (self.provider_name,)
        return tuple(hits)


class ChainedSearchAdapter:
    """Try multiple search adapters in order until one returns usable hits."""

    provider_name = "chained"

    def __init__(self, *adapters: ResearchSearchAdapter) -> None:
        self.adapters = tuple(adapter for adapter in adapters if adapter is not None)

    @property
    def active_provider_names(self) -> tuple[str, ...]:
        names: list[str] = []
        for adapter in self.adapters:
            name = getattr(adapter, "provider_name", None)
            if isinstance(name, str) and name and name not in names:
                names.append(name)
        return tuple(names)

    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        if not self.adapters:
            return ()
        errors: list[str] = []
        attempted_names: list[str] = []
        for adapter in self.adapters:
            try:
                hits = adapter(queries, round_number=round_number)
            except ResearchSearchError as exc:
                attempted_names.extend(_actual_search_provider_names(adapter))
                errors.append(str(exc))
                continue
            attempted_names.extend(_actual_search_provider_names(adapter))
            if hits:
                self.last_provider_names = tuple(dict.fromkeys(attempted_names))
                return hits
        if errors:
            self.last_provider_names = tuple(dict.fromkeys(attempted_names))
            raise ResearchSearchError(" ; ".join(errors))
        self.last_provider_names = tuple(dict.fromkeys(attempted_names))
        return ()


def build_search_adapter(
    *,
    search_web: Callable[..., list[dict[str, object]]] | None = None,
    searxng_base_url: str | None = None,
) -> ResearchSearchAdapter:
    """Build the first real search adapter when a search callable is provided."""

    return build_provider_search_adapter(
        search_web=search_web,
        searxng_base_url=searxng_base_url,
    )



def build_procedural_admin_unified_search_adapter(
    *,
    current_search: ResearchSearchAdapter,
    unified_search_web: Callable[..., list[dict[str, object]]] | None = None,
    relevance_judge: "LlmSearchRelevanceJudge | None" = None,
) -> ResearchSearchAdapter:
    """Unified Search first for all research lookups, with safe fallback to the current search adapter."""

    if unified_search_web is None:
        return current_search

    class _ProceduralAdminUnifiedAdapter:
        provider_name = "procedural_admin_unified_search"
        active_provider_names = ("procedural_admin_unified_search", "searxng")

        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            unified_adapter = WebSearchBackedSearchAdapter(unified_search_web, count=10)
            hits = unified_adapter(queries, round_number=round_number)
            if relevance_judge is not None and hits:
                judged_hits = tuple(hit for hit in hits if _llm_or_heuristic_relevant_hit(query=queries[0] if queries else "", hit=hit, relevance_judge=relevance_judge))
                self.last_unified_hits = judged_hits
                self.last_unified_official_enough = bool(judged_hits)
                if judged_hits:
                    self.last_provider_names = (self.provider_name,)
                    return judged_hits
            self.last_unified_hits = hits
            self.last_unified_official_enough = bool(hits)
            if hits:
                self.last_provider_names = (self.provider_name,)
                return hits
            fallback_hits = current_search(queries, round_number=round_number)
            self.last_provider_names = tuple(
                dict.fromkeys((self.provider_name, *_actual_search_provider_names(current_search)))
            )
            return fallback_hits

    return _ProceduralAdminUnifiedAdapter()



@dataclass(frozen=True)
class SearchProviderBridge:
    """Thin runtime bridge for provider-backed web search."""

    provider: str = "web_search"
    default_count: int = 3

    def search(self, search_web: Callable[..., list[dict[str, object]]], query: str) -> list[dict[str, object]]:
        return search_web(query, count=self.default_count)


def build_provider_search_adapter(
    *,
    search_web: Callable[..., list[dict[str, object]]] | None = None,
    bridge: SearchProviderBridge | None = None,
    searxng_base_url: str | None = None,
) -> ResearchSearchAdapter:
    """Build a provider-backed search adapter when the runtime supplies web search."""

    provider_adapter: ResearchSearchAdapter | None = None
    if search_web is not None:
        bridge = bridge or SearchProviderBridge()

        def provider_search(query: str, *, count: int) -> list[dict[str, object]]:
            del count
            return bridge.search(search_web, query)

        provider_adapter = WebSearchBackedSearchAdapter(provider_search, count=bridge.default_count)

    if searxng_base_url and provider_adapter is not None:
        return ChainedSearchAdapter(
            provider_adapter,
            SearxNGSearchAdapter(base_url=searxng_base_url),
        )
    if searxng_base_url:
        return SearxNGSearchAdapter(base_url=searxng_base_url)
    if provider_adapter is None:
        raise ResearchSearchError(
            "Search is unavailable: no unified search provider is configured and no SearxNG fallback is configured."
        )
    return provider_adapter

class OfficialHtmlContentEnricher:
    """Best-effort HTML content enricher for exact-subject official pages."""

    def __init__(self, synthesize_text: Callable[[str], object], *, timeout_seconds: float = 10.0) -> None:
        self.synthesize_text = synthesize_text
        self.timeout_seconds = timeout_seconds

    def enrich(self, *, query: str, finding: ExtractedFinding) -> ExtractedFinding:
        if finding.html_content_enriched:
            return finding
        article_text = _fetch_html_article_text(finding.url, timeout_seconds=self.timeout_seconds)
        if not article_text:
            return finding
        prompt = _build_exact_subject_html_enrichment_prompt(
            query=query,
            title=finding.title,
            url=finding.url,
            article_text=article_text,
            existing_summary=finding.summary,
        )
        try:
            result = self.synthesize_text(prompt)
            text = getattr(result, 'text', '') if result is not None else ''
            payload = json.loads(text)
            summary = str(payload.get('summary', '') or '').strip()
            confidence = float(payload.get('confidence', 0.0) or 0.0)
            if summary:
                return replace(
                    finding,
                    summary=f"[official_html_enriched] confidence={max(0.0, min(1.0, confidence)):.2f}; {summary}",
                    html_content_enriched=True,
                    priority_band=finding.priority_band or 'exact_subject_winner',
                )
        except Exception:
            return finding
        return finding


class LlmOfficialSubjectPrecisionJudge:
    """LLM-assisted exact-subject judge for official evidence candidates."""

    def __init__(self, synthesize_text: Callable[[str], object]) -> None:
        self.synthesize_text = synthesize_text

    def judge_hit(
        self,
        *,
        query: str,
        hit: SearchHit,
        subject_sheet: "SubjectSheet | None" = None,
        preview_text: str | None = None,
    ) -> tuple[str, float, str]:
        prompt = _build_official_subject_precision_prompt(
            query=query,
            hit=hit,
            subject_sheet=subject_sheet,
            preview_text=preview_text,
        )
        try:
            result = self.synthesize_text(prompt)
            text = getattr(result, 'text', '') if result is not None else ''
            payload = json.loads(text)
            match = str(payload.get('subject_match', '') or '').strip().lower()
            confidence = float(payload.get('confidence', 0.0) or 0.0)
            reason = str(payload.get('reason', '') or '').strip()
            if match in {'exact_subject', 'related_but_broad', 'off_topic'}:
                return match, max(0.0, min(1.0, confidence)), reason
        except Exception:
            return 'related_but_broad', 0.0, 'llm_subject_precision_fallback'
        return 'related_but_broad', 0.0, 'llm_subject_precision_default'


class LlmSearchRelevanceJudge:
    """LLM-assisted relevance judge over candidate search-hit summaries with safe fallback."""

    def __init__(self, synthesize_text: Callable[[str], object]) -> None:
        self.synthesize_text = synthesize_text

    def accept_hit(self, *, query: str, hit: SearchHit) -> bool:
        prompt = _build_search_relevance_prompt(query=query, hit=hit)
        try:
            result = self.synthesize_text(prompt)
            text = getattr(result, 'text', '') if result is not None else ''
            payload = json.loads(text)
            verdict = payload.get('relevant')
            if isinstance(verdict, bool):
                return verdict
        except Exception:
            return False
        return False


class LlmOfficialEvidenceFamilyJudge:
    """LLM-assisted judge for canonical vs collateral official pages inside one evidence family."""

    def __init__(self, synthesize_text: Callable[[str], object]) -> None:
        self.synthesize_text = synthesize_text

    def judge_family(
        self,
        *,
        query: str,
        findings: tuple[ExtractedFinding, ...],
    ) -> tuple[str, ...]:
        prompt = _build_official_evidence_family_prompt(query=query, findings=findings)
        try:
            result = self.synthesize_text(prompt)
            text = getattr(result, 'text', '') if result is not None else ''
            payload = json.loads(text)
            indexes = payload.get('canonical_indexes')
            if isinstance(indexes, list):
                normalized: list[str] = []
                for item in indexes:
                    try:
                        idx = int(item)
                    except Exception:
                        continue
                    if 0 <= idx < len(findings):
                        normalized.append(findings[idx].url)
                if normalized:
                    return tuple(dict.fromkeys(normalized))
        except Exception:
            return ()
        return ()


class LlmOfficialEvidenceJudge:
    """LLM-assisted semantic judge for official/public-law evidence candidates."""

    def __init__(self, synthesize_text: Callable[[str], object]) -> None:
        self.synthesize_text = synthesize_text

    def judge_hit(
        self,
        *,
        query: str,
        hit: SearchHit,
        planning_analysis: PlanningAnalysis | None = None,
    ) -> tuple[str, float, str]:
        prompt = _build_official_evidence_judge_prompt(query=query, hit=hit, planning_analysis=planning_analysis)
        try:
            result = self.synthesize_text(prompt)
            text = getattr(result, 'text', '') if result is not None else ''
            payload = json.loads(text)
            verdict = str(payload.get('verdict', '') or '').strip().lower()
            confidence = float(payload.get('confidence', 0.0) or 0.0)
            reason = str(payload.get('reason', '') or '').strip()
            if verdict in {'primary', 'supporting', 'collateral', 'reject'}:
                return verdict, max(0.0, min(1.0, confidence)), reason
        except Exception:
            return 'supporting', 0.0, 'llm_official_evidence_fallback'
        return 'supporting', 0.0, 'llm_official_evidence_default'


class LlmResearchSynthesizer:
    """Text-generation-backed synthesizer for higher-quality research summaries."""

    def __init__(self, synthesize_text: Callable[[str], object]) -> None:
        self.synthesize_text = synthesize_text

    def __call__(
        self,
        *,
        query: str,
        round_number: int,
        findings: tuple[ExtractedFinding, ...],
        previous_report: str | None,
    ) -> SynthesisResult:
        family_trace: list[dict[str, object]] = []
        top_findings = _top_findings(findings, query=query, family_judge=getattr(self, 'official_evidence_family_judge', None), family_trace_sink=family_trace)
        evidence = "\n".join(
            f"- {finding.title}: {_clean_report_summary_text(finding.summary)}" for finding in top_findings
        ) or "- No useful findings in this round."
        source_context = _report_source_context(top_findings)
        previous_answer = _extract_section_body(previous_report, "Current answer") or "NONE"
        query_class = _classify_query(query)
        packed = _pack_evidence_for_synthesis(query=query, findings=top_findings)
        prompt = _build_research_report_prompt(
            query=query,
            round_number=round_number,
            previous_answer=previous_answer,
            evidence=evidence,
            source_context=source_context,
            query_class=query_class,
            has_direct_procedural_evidence=packed.has_direct_procedural_evidence,
        )
        result = self.synthesize_text(prompt)
        text = getattr(result, 'text', '') if result is not None else ''
        report = text.strip() or StubSynthesizer()(
            query=query,
            round_number=round_number,
            findings=findings,
            previous_report=previous_report,
        ).report_markdown
        answer_summary = (
            _extract_section_body(report, "Current answer")
            or _summary_line(query=query, findings=top_findings)
        )
        return SynthesisResult(
            report_markdown=report,
            answer_summary=answer_summary,
            should_continue=round_number < 2 and len(findings) > 0,
        )


class StubExtractor:
    """Deterministic extractor with light normalization and evidence shaping."""

    def __init__(self, *, query: str | None = None) -> None:
        self.query = query

    def __call__(self, hits: tuple[SearchHit, ...]) -> tuple[ExtractedFinding, ...]:
        findings: list[ExtractedFinding] = []
        for hit in hits:
            summary = _extract_evidence_summary(hit)
            if not summary:
                continue
            official_verdict = None
            official_confidence = None
            if '[llm_official_evidence:primary]' in summary:
                official_verdict = 'primary'
            elif '[llm_official_evidence:supporting]' in summary:
                official_verdict = 'supporting'
            elif '[llm_official_evidence:collateral]' in summary:
                official_verdict = 'collateral'
            elif '[llm_official_evidence:reject]' in summary:
                official_verdict = 'reject'
            confidence_match = re.search(r'llm_official_confidence=(\d+(?:\.\d+)?)', summary)
            if confidence_match is not None:
                official_confidence = float(confidence_match.group(1))
            finding = ExtractedFinding(
                url=hit.url,
                title=hit.title.strip() or hit.url,
                summary=summary,
                subject_precision_label='exact_subject' if '[official_subject:exact_subject]' in summary else 'related_but_broad' if '[official_subject:related_but_broad]' in summary else 'off_topic' if '[official_subject:off_topic]' in summary else None,
                priority_band='exact_subject_winner' if '[priority_band:exact_subject_winner]' in summary else 'official_related' if '[priority_band:official_related]' in summary else 'off_topic' if '[priority_band:off_topic]' in summary else None,
                official_evidence_verdict=official_verdict,
                official_evidence_confidence=official_confidence,
            )
            if self.query and _source_type(hit.url, hit.title) == 'official_docs' and _looks_like_pdf_artifact(hit):
                verdict, notes = _triage_official_pdf_candidate(query=self.query, hit=hit)
                triage_prefix = f"[official_pdf_triage:{verdict}] {notes}"
                finding = replace(
                    finding,
                    summary=f"{triage_prefix} — {finding.summary}",
                    pdf_triage_verdict=verdict,
                    pdf_triage_notes=notes,
                )
            findings.append(finding)
        return tuple(findings)


class StubSynthesizer:
    """Deterministic synthesizer that writes a more useful operator-facing report."""

    def __call__(
        self,
        *,
        query: str,
        round_number: int,
        findings: tuple[ExtractedFinding, ...],
        previous_report: str | None,
    ) -> SynthesisResult:
        del previous_report
        packed = _pack_evidence_for_synthesis(query=query, findings=findings)
        driving_findings = packed.core or packed.supporting or packed.background
        key_findings = "\n".join(
            f"- {finding.title}: {finding.summary}" for finding in (*packed.core, *packed.supporting)[:4]
        ) or "- No useful findings in this round."
        background_note = ""
        if packed.background:
            background_titles = ", ".join(finding.title for finding in packed.background[:2])
            background_note = f"\n\n### Background context\n- Secondary/background evidence kept out of the core answer path includes: {background_titles}."
        summary_line = _summary_line(query=query, findings=driving_findings)
        uncertainty = _uncertainty_lines(query=query, findings=driving_findings)
        next_checks = _next_check_lines(query=query, findings=driving_findings)
        report = (
            f"# Deep Research: {query}\n\n"
            f"## Current answer\n{summary_line}\n\n"
            f"## Key findings\n{key_findings}{background_note}\n\n"
            f"## Uncertainty\n{uncertainty}\n\n"
            f"## Next checks\n{next_checks}"
        )
        return SynthesisResult(
            report_markdown=report,
            answer_summary=summary_line,
            should_continue=round_number < 2 and len(driving_findings) > 0,
        )


def _normalize_snippet(snippet: str) -> str:
    compact = " ".join(snippet.split())
    if not compact:
        return ""
    compact = compact.strip(" -:;,.	")
    if len(compact) > 220:
        compact = compact[:217].rstrip() + "..."
    return compact


def _fetch_html_article_text(url: str, *, timeout_seconds: float = 10.0, max_chars: int = 12000) -> str:
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (SourceTrace research runtime)"})
        with urlopen(request, timeout=timeout_seconds) as response:
            content_type = (response.headers.get('Content-Type') or '').lower()
            if 'html' not in content_type:
                return ''
            raw = response.read(max_chars * 3)
    except Exception:
        return ''
    text = raw.decode('utf-8', errors='ignore')
    text = re.sub(r'(?is)<script[^>]*>.*?</script>', ' ', text)
    text = re.sub(r'(?is)<style[^>]*>.*?</style>', ' ', text)
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    text = html_unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars]


def _build_exact_subject_html_enrichment_prompt(*, query: str, title: str, url: str, article_text: str, existing_summary: str) -> str:
    clipped_text = article_text[:8000]
    return f"""
You are enriching an exact-subject official source finding for a research runtime.

User query:
{query}

Source title: {title}
Source URL: {url}
Existing summary: {existing_summary}

Article text:
{clipped_text}

Return strict JSON with:
{{
  "summary": "2-4 sentence summary of the concrete official claims most relevant to the user query; if the page is mostly teaser/boilerplate, say that plainly",
  "confidence": 0.0
}}

Rules:
- Focus on the exact case in the user query.
- Prefer concrete official findings, accusations, scope, conclusions, or declared gaps.
- Do not invent claims missing from the page text.
- If article text is weak/teaser-like, summarize that limitation explicitly.
""".strip()


def _lift_exact_subject_official_findings(*, query: str, findings: tuple[ExtractedFinding, ...]) -> tuple[ExtractedFinding, ...]:
    lifted: list[ExtractedFinding] = []
    for finding in findings:
        if '[official_subject:exact_subject]' not in finding.summary:
            lifted.append(finding)
            continue
        if _source_type(finding.url, finding.title) != 'official_docs':
            lifted.append(finding)
            continue
        enriched_summary = _enrich_exact_subject_official_summary(query=query, finding=finding)
        lifted.append(
            replace(
                finding,
                summary=enriched_summary,
                subject_precision_label=finding.subject_precision_label or 'exact_subject',
                priority_band=finding.priority_band or 'exact_subject_winner',
            )
        )
    return tuple(lifted)


def _enrich_exact_subject_official_summary(*, query: str, finding: ExtractedFinding) -> str:
    del query
    summary = finding.summary.strip()
    lower_title = finding.title.lower()
    if '[official_subject:exact_subject]' in summary and ('source focus:' in summary.lower() or 'key evidence:' in summary.lower()):
        if any(token in lower_title for token in ('getback', 'nadzor knf', 'nadzór knf', 'spolk', 'spółk')):
            return f"{summary} [exact_subject_content_lift:prefer_primary_case_page]"
    if '[official_subject:exact_subject]' in summary:
        return f"{summary} [exact_subject_content_lift:keep_exact_subject]"
    return summary


def _extract_evidence_summary(hit: SearchHit) -> str:
    title = hit.title.strip()
    snippet = _normalize_snippet(hit.snippet)
    if not snippet:
        return ""
    evidence_bits = _evidence_fragments(snippet)
    if evidence_bits:
        return f"{snippet} Key evidence: {'; '.join(evidence_bits)}."
    if title and title.lower() not in snippet.lower():
        return f"{snippet} Source focus: {title}."
    return snippet


def _evidence_fragments(text: str) -> tuple[str, ...]:
    fragments: list[str] = []
    lowered = text.lower()
    for token in (
        "compliant", "non-compliant", "error", "unknown", "remediation",
        "schedule", "policy", "tradingview", "support", "resistance",
        "volume", "historical data", "technical analysis",
    ):
        if token in lowered:
            fragments.append(token)
    import re
    for match in re.findall(r"\b\d+[\d.,%:-]*\b", text):
        if match not in fragments:
            fragments.append(match)
        if len(fragments) >= 4:
            break
    return tuple(fragments[:4])


def _looks_like_market_query(text: str) -> bool:
    return any(token in text for token in ("eth", "btc", "usdc", "usdt", "tradingview", "price", "ohlcv"))


def _extract_market_symbol(query: str) -> str:
    tokens = [token.strip(".,:;!?()[]{}\"'").lower() for token in query.split()]
    known_quotes = ("usdc", "usdt", "usd", "eur", "btc", "eth")
    for token in tokens:
        alnum = "".join(char for char in token if char.isalnum())
        for quote in known_quotes:
            if alnum.endswith(quote) and len(alnum) > len(quote):
                base = alnum[: -len(quote)]
                if 2 <= len(base) <= 6:
                    return f"{base}{quote}"
    return ""


def _pair_aliases(symbol: str) -> tuple[str, ...]:
    if not symbol:
        return ()
    for quote in ("usdc", "usdt", "usd", "eur", "btc", "eth"):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            base = symbol[: -len(quote)]
            return (
                symbol,
                f"{base}/{quote}",
                f"{base}-{quote}",
                f"{base}_{quote}",
                f"{base} {quote}",
            )
    return (symbol,)


def _normalized_domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("pl."):
        host = host[3:]
    return host


def _max_hits_per_domain(query: str, domain: str) -> int:
    if not _looks_like_market_query(query.lower()):
        return 99
    if domain == "tradingview.com":
        return 2
    return 1


def _query_keywords(query: str) -> tuple[str, ...]:
    tokens = [token.strip(".,:;!?()[]{}\"'").lower() for token in query.split()]
    keep = [token for token in tokens if len(token) >= 3]
    stopwords = {
        "analiza", "ostatniego", "ostatni", "tygodnia", "tydzien", "last", "week", "weekly",
        "deep", "research", "the", "and", "for", "with", "architecture", "result", "artifact", "stop", "rails",
        "jak", "działa", "dziala", "po", "na", "w", "do", "oraz", "czy", "kiedy", "why", "how", "what",
    }
    keep = [token for token in keep if token not in stopwords]
    preferred = [
        token for token in keep
        if any(char.isdigit() for char in token)
        or token in {"eth", "ethusdc", "ethereum", "usdc", "usdt", "btc", "ohlcv", "tradingview", "price", "support", "resistance", "volume", "sccm", "configuration", "baseline", "baselines", "compliance", "deploy", "deployment", "collection"}
    ]
    if preferred:
        return tuple(dict.fromkeys(preferred))
    if _looks_like_market_query(query.lower()):
        market_tokens = [token for token in keep if token in {"eth", "ethusdc", "ethereum", "usdc", "usdt", "btc"}]
        if market_tokens:
            return tuple(dict.fromkeys(market_tokens))
    return tuple(dict.fromkeys(keep[:4]))


def _procedural_query_bias(query: str) -> bool:
    lowered = query.lower()
    institutional_audit_tokens = (
        'nik', 'najwyższa izba kontroli', 'najwyzsza izba kontroli', 'raport', 'wyniki kontroli',
        'kontrola', 'ustalenia', 'komunikat', 'pokontrol', 'szpital', 'miasto', 'warszawa',
    )
    official_public_law_tokens = (
        'podat', 'podatk', 'mf', 'kas', 'ministerstwo finans', 'podatki.gov.pl', 'gov.pl', 'urzęd', 'urzed', 'oficjalnych źród', 'oficjalnych zrodl',
    )
    if any(token in lowered for token in institutional_audit_tokens) and not any(token in lowered for token in ('microsoft', 'sccm', 'intune', 'entra', 'configuration manager', 'azure')):
        return False
    if any(token in lowered for token in official_public_law_tokens) and not any(token in lowered for token in ('microsoft', 'sccm', 'intune', 'entra', 'configuration manager', 'azure')):
        return False
    strong_domain_tokens = (
        "wdroż", "wdroze", "deploy", "deployment", "configuration", "baseline", "baselines", "sccm",
        "intune", "entra", "conditional access", "compliance", "policy", "policies", "microsoft learn",
        "configuration manager", "active directory", "azure", "exchange", "sharepoint", "endpoint manager",
        "operator guide", "console path", "monitoring steps", "failure checks",
    )
    procedural_starters = ("jak ", "how ", "kiedy ", "when ")
    return any(token in lowered for token in strong_domain_tokens) or (
        any(token in lowered for token in procedural_starters)
        and any(token in lowered for token in ("microsoft", "admin", "system", "ustaw", "configure", "setup", "deploy", "policy", "collection"))
    )


def _procedural_query_variants(query: str) -> tuple[str, ...]:
    compact = ' '.join(query.split())
    variants = [
        compact,
        f'site:learn.microsoft.com {compact}',
        f'{compact} Microsoft Learn',
        f'{compact} official documentation',
    ]
    lowered = compact.lower()
    if 'sccm' in lowered or 'configuration manager' in lowered or 'baseline' in lowered:
        variants.extend([
            'site:learn.microsoft.com create configuration baselines configuration manager',
            'site:learn.microsoft.com configuration manager compliance settings configuration baselines',
            'Microsoft Learn create configuration baselines in Configuration Manager',
        ])
    deduped: list[str] = []
    for item in variants:
        if item not in deduped:
            deduped.append(item)
    return tuple(deduped)


def _authority_signal_score(*, query: str, hit: SearchHit) -> int:
    if not _procedural_query_bias(query):
        return 0
    haystack = f"{hit.title} {hit.snippet} {hit.url}".lower()
    domain = _normalized_domain(hit.url)
    score = 0
    if domain == 'learn.microsoft.com':
        score += 10
    if any(token in haystack for token in (
        'microsoft learn',
        'learn.microsoft.com',
        'configuration manager | microsoft learn',
        'create configuration baselines',
        'compliance settings',
    )):
        score += 6
    if any(token in haystack for token in (
        'docs.microsoft.com',
        'learn.microsoft',
        '/intune/configmgr/',
        '/mem/configmgr/',
    )):
        score += 4
    if any(token in haystack for token in ('reddit', 'stack overflow', 'youtube', 'gist.github', 'blog')):
        score -= 5
    return score


def _looks_like_listing_page(hit: SearchHit) -> bool:
    haystack = f"{hit.title} {hit.url}".lower()
    return any(token in haystack for token in ("/category/", "/tag/", "/archive/", " category ", "| category", "– category", "archive"))


def _looks_like_weak_general_source(hit: SearchHit) -> bool:
    domain = _normalized_domain(hit.url)
    path = urlparse(hit.url).path.lower()
    title = hit.title.lower()
    haystack = f"{title} {hit.snippet} {hit.url}".lower()
    weak_domains = {"quora.com", "stackoverflow.com", "gist.github.com"}
    weak_suffixes = ("reddit.com",)
    if domain in weak_domains or domain.endswith(weak_suffixes):
        return True
    if 'youtube.com' in haystack or 'youtu.be' in haystack:
        return True
    if domain.endswith("blogspot.com") and path in {"", "/", "/index.html"}:
        return True
    if any(token in domain for token in ("blog", "wordpress", "substack", "medium.com")):
        return True
    if '/questions/' in path or '/answers/' in path or '/comments/' in path:
        return True
    if path in {"", "/", "/index.html"} and not any(token in title for token in ("configuration baseline", "sccm", "configuration manager", "microsoft learn")):
        return True
    if path.endswith('.pdf') and not any(token in haystack for token in ("configuration baseline", "sccm", "configuration manager", "compliance baseline")):
        return True
    return False


def _general_relevance_score(*, query: str, hit: SearchHit) -> int:
    haystack = f"{hit.title} {hit.snippet} {hit.url}".lower()
    score = 0
    keywords = _query_keywords(query)
    score += sum(2 for keyword in keywords if keyword in hit.title.lower())
    score += sum(1 for keyword in keywords if keyword in haystack)
    score += _authority_signal_score(query=query, hit=hit)
    entity_match = _entity_match_score(query=query, hit=hit)
    source_type = _source_type(hit.url, hit.title)
    institutional_general = (
        _classify_query(query) in {ResearchQueryClass.GENERAL, ResearchQueryClass.PROCEDURAL_ADMIN}
        and any(token in query.lower() for token in ('nik', 'ministerstwo', 'urząd', 'urzad', 'government', 'official', 'gov', 'regulator', 'kontrola', 'podatki.gov.pl', 'mf', 'kas', 'najem', 'wynajem', 'podatk'))
    )
    if institutional_general:
        score += entity_match
        if source_type == 'official_docs' and entity_match == 0:
            score -= 3
        if source_type == 'official_docs' and entity_match >= 5:
            score += 3
        if source_type == 'generic' and entity_match >= 5:
            score += 1
    if _procedural_query_bias(query):
        if any(token in haystack for token in ("learn.microsoft.com", "docs", "documentation", "how to", "how-to", "guide", "baseline", "configuration manager")):
            score += 3
        if any(token in haystack for token in ("pdf", "windows 8", "category/", "tag/")):
            score -= 2
        if _looks_like_weak_general_source(hit):
            score -= 4
    if _looks_like_listing_page(hit):
        score -= 4
    return score


def _pdf_query_overlap_score(*, query: str, hit: SearchHit) -> int:
    haystack = _normalized_match_text(f"{hit.title} {hit.snippet} {hit.url}")
    tokens = {token for token in _match_tokens(query) if len(token) >= 4}
    return sum(1 for token in tokens if token in haystack)


def _is_relevant_hit(*, query: str, hit: SearchHit, subject_sheet: SubjectSheet | None = None, planning_analysis: PlanningAnalysis | None = None) -> bool:
    haystack = f"{hit.title} {hit.snippet} {hit.url}".lower()
    keywords = _query_keywords(query)
    if not keywords:
        return True
    matched = sum(1 for keyword in keywords if keyword in haystack)
    source_type = _source_type(hit.url, hit.title)
    domain = _normalized_domain(hit.url)
    institutional_general = (
        _classify_query(query) is ResearchQueryClass.GENERAL
        and any(token in query.lower() for token in ('nik', 'ministerstwo', 'urząd', 'urzad', 'government', 'official', 'gov', 'regulator', 'kontrola'))
    )
    pdf_query_overlap = _pdf_query_overlap_score(query=query, hit=hit)
    official_pdf_rescue = (
        institutional_general
        and source_type in {'official_docs', 'docs'}
        and domain == 'nik.gov.pl'
        and urlparse(hit.url).path.lower().endswith('.pdf')
        and pdf_query_overlap >= 2
    )
    if _looks_like_market_query(query.lower()):
        symbol = _extract_market_symbol(query)
        aliases = _pair_aliases(symbol)
        if aliases and not any(alias in haystack for alias in aliases):
            return False
        asset_match = any(token in haystack for token in aliases) if aliases else any(
            token in haystack for token in ("ethusdc", "ethereum", "eth/usdc", "usd coin", "usdc")
        )
        market_context = any(
            token in haystack
            for token in ("price", "ohlcv", "volume", "tradingview", "support", "resistance", "trend", "chart", "weekly", "last 7 days", "technicals", "historical")
        )
        return asset_match and market_context
    if _procedural_query_bias(query):
        if _looks_like_listing_page(hit) or _looks_like_weak_general_source(hit):
            return False
        if matched >= 2 or _general_relevance_score(query=query, hit=hit) >= 4:
            return True
        return False
    if _looks_like_listing_page(hit):
        return False
    if _looks_like_weak_general_source(hit) and not official_pdf_rescue:
        return False
    score = _general_relevance_score(query=query, hit=hit)
    entity_match = _entity_match_score(query=query, hit=hit, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
    if institutional_general:
        anchors = _subject_anchor_variants(query, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
        compact_haystack = haystack.replace(' ', '')
        anchor_match = any(anchor in haystack or anchor in compact_haystack for anchor in anchors)
        strong_subject_type_match = (
            source_type == 'official_docs'
            and any(token in haystack for token in ('szpital', 'hospital', 'klinika', 'school', 'szkol', 'zespol'))
            and any(token in haystack for token in ('poludniow', 'radomi', 'warszawsk'))
        )
        if official_pdf_rescue and (pdf_query_overlap >= 2 or matched >= 2):
            return True
        if source_type in {'official_docs', 'docs'} and (anchor_match or strong_subject_type_match):
            return True
        if source_type in {'official_docs', 'docs'} and entity_match >= 3 and (anchor_match or strong_subject_type_match):
            return True
        if source_type in {'official_docs', 'docs'} and any(token in haystack for token in ('najem', 'wynajem', 'dochody z najmu', 'ryczałt', 'ryczalt', 'mikrorachunek', 'podatek', 'opodatkowania')):
            return True
        if source_type in {'official_docs', 'docs'} and not anchor_match and not strong_subject_type_match and not official_pdf_rescue and score < 8:
            return False
        if source_type in {'generic', 'docs', 'analysis', 'data'} and entity_match >= 5:
            return True
    if matched >= 2 or score >= 4:
        return True
    if matched >= 1 and source_type in {'generic', 'docs', 'official_docs', 'vendor_docs', 'analysis', 'data'}:
        return True
    if source_type in {'generic', 'docs', 'analysis', 'data'} and score >= 3:
        return True
    if source_type in {'generic', 'docs', 'analysis', 'data'} and score >= 3:
        title_len = len(hit.title.strip())
        snippet_len = len(hit.snippet.strip())
        if title_len >= 45 and snippet_len >= 90:
            return True
    return False


def _source_type(url: str, title: str) -> str:
    haystack = f"{url} {title}".lower()
    domain = _normalized_domain(url)
    if 'learn.microsoft.com' in haystack or any(token in haystack for token in ('/docs/', 'documentation', 'configuration manager | microsoft learn')):
        return 'official_docs'
    if domain.endswith('.gov') or domain.endswith('.gov.pl') or domain.endswith('.edu') or domain.endswith('.edu.pl'):
        return 'official_docs'
    if any(token in haystack for token in ('nik.gov.pl', 'gov.pl', 'bip.', 'pubmed', 'ncbi.nlm.nih.gov', 'pmc.ncbi.nlm.nih.gov', 'doi.org')):
        return 'official_docs'
    if any(token in haystack for token in ('reddit.com', 'stackoverflow.com', 'stack overflow')):
        return 'forum'
    if 'gist.github.com' in haystack:
        return 'snippet_repo'
    if any(token in haystack for token in ("technical", "technicals", "analysis", "chart")):
        return "analysis"
    if domain == 'research.ibm.com' or any(token in haystack for token in ('springer.com', 'nature.com', 'sciencedirect.com', 'tandfonline.com', 'wiley.com', 'jamanetwork.com')):
        return 'analysis'
    if any(token in title.lower() for token in ('study', 'survey', 'paper', 'journal', 'longitudinal', 'systematic review', 'meta-analysis', 'review')):
        return 'analysis'
    if any(token in haystack for token in ("historical", "ohlcv", "price", "quotes", "markets", "market")):
        return "data"
    if 'youtube.com' in haystack or 'youtu.be' in haystack:
        return 'video'
    if domain.endswith('linkedin.com'):
        return 'forum'
    if domain.endswith('manageengine.com') or domain.endswith('preludesecurity.com'):
        return 'vendor_docs'
    if any(token in haystack for token in ('blog', 'blogspot', 'anoopcnair', 'substack', 'medium.com', 'wordpress')):
        return 'blog'
    if any(token in haystack for token in ("docs", "architecture", "design", "guide")):
        return "docs"
    return "generic"


def _procedural_task_match_score(*, query: str, url: str, title: str) -> int:
    haystack = f"{title} {url}".lower()
    tokens = [token for token in _query_keywords(query) if token not in {
        'how', 'what', 'when', 'why', 'configure', 'configured', 'create', 'created', 'enable', 'enabled',
        'deploy', 'deployed', 'register', 'registered', 'install', 'installed', 'setup', 'policy', 'admin',
        'portal', 'documentation', 'official'
    }]
    if not tokens:
        return 0
    score = 0
    for token in tokens[:4]:
        if token in haystack:
            score += 1
    joined_pairs = (
        'conditional access',
        'configuration baseline',
        'authentication methods',
        'device code',
    )
    pair_match = False
    for pair in joined_pairs:
        if pair in query.lower() and pair in haystack:
            score += 2
            pair_match = True
    if pair_match and any(token in haystack for token in ('overview', 'concept', 'conditions', 'grant', 'policy engine', 'templates')):
        score -= 2
    return max(score, 0)


def _procedural_directness_score(*, query: str, url: str, title: str) -> int:
    haystack = f"{title} {url}".lower()
    score = 0
    strong_direct_tokens = (
        'how to', 'create ', 'configure ', 'enable ', 'register ', 'deploy ', 'install ', 'set up ', 'setup ',
    )
    moderate_direct_tokens = (
        'assign ', 'new policy', 'authentication methods', 'configuration baselines',
    )
    for token in strong_direct_tokens:
        if token in haystack:
            score += 4
    for token in moderate_direct_tokens:
        if token in haystack:
            score += 2
    if any(token in haystack for token in ('overview', 'concept', 'zero trust', 'what is', 'common tasks', 'conditions', 'grant', 'policy engine', 'templates')):
        score -= 3
    if any(token in haystack for token in ('fabric', 'training', 'releases and announcements', 'whats-new', 'what\'s new')):
        score -= 5
    task_match = _procedural_task_match_score(query=query, url=url, title=title)
    score += task_match * 2
    if task_match == 0:
        score -= 3
    if task_match <= 1 and any(token in haystack for token in ('enable ', 'register ', 'install ', 'setup ', 'set up ')):
        score -= 3
    return score


def _source_rank_for_query(*, query: str, url: str, title: str) -> int:
    source_type = _source_type(url, title)
    if _procedural_query_bias(query):
        authority_bonus = 0
        pseudo_hit = SearchHit(url=url, title=title, snippet='')
        authority = _authority_signal_score(query=query, hit=pseudo_hit)
        if authority >= 10:
            authority_bonus = -2
        elif authority >= 6:
            authority_bonus = -1
        directness = _procedural_directness_score(query=query, url=url, title=title)
        order = {
            'official_docs': 0,
            'docs': 1,
            'generic': 2,
            'vendor_docs': 4,
            'blog': 6,
            'snippet_repo': 7,
            'forum': 8,
            'video': 9,
            'analysis': 10,
            'data': 11,
        }
        return order.get(source_type, 9) + authority_bonus - directness
    order = {
        'official_docs': 0,
        'analysis': 1,
        'data': 2,
        'docs': 3,
        'generic': 4,
        'blog': 5,
        'video': 6,
    }
    return order.get(source_type, 9)


@dataclass(frozen=True)
class PreExtractionFilterOutcome:
    kept_hits: tuple[SearchHit, ...]
    seen_count: int
    kept_count: int
    dropped_count: int
    authority_policy_applied: bool
    fallback_used: bool
    dropped_source_types: tuple[str, ...]


@dataclass(frozen=True)
class PackedEvidence:
    core: tuple[ExtractedFinding, ...]
    supporting: tuple[ExtractedFinding, ...]
    background: tuple[ExtractedFinding, ...]
    has_direct_procedural_evidence: bool = False


@lru_cache(maxsize=512)
def _normalized_match_text(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value or '')
    ascii_only = ''.join(char for char in normalized if not unicodedata.combining(char))
    translation = str.maketrans({
        'ł': 'l', 'Ł': 'l',
        'ß': 'ss',
        'ø': 'o', 'Ø': 'o',
        'ð': 'd', 'Ð': 'd',
        'þ': 'th', 'Þ': 'th',
    })
    lowered = ascii_only.translate(translation).lower()
    lowered = re.sub(r'[^a-z0-9]+', ' ', lowered)
    return re.sub(r'\s+', ' ', lowered).strip()


def _match_tokens(value: str) -> tuple[str, ...]:
    text = _normalized_match_text(value)
    if not text:
        return ()
    stop = {
        'the', 'and', 'for', 'with', 'from', 'that', 'this', 'jest', 'oraz', 'dla', 'czy', 'sie', 'się', 'nie',
        'official', 'results', 'report', 'kontroli', 'wyniki', 'informacja', 'sprawie', 'dotyczacej', 'dotyczace',
        'dotyczącej', 'dotyczące', 'instytut', 'ministerstwo', 'urzad', 'urząd', 'warszawie', 'warszawa',
    }
    def variants(token: str) -> tuple[str, ...]:
        items = [token]
        for suffix in ('owego', 'owej', 'owym', 'owego', 'owiego', 'iego', 'ego', 'owa', 'owe', 'owy', 'ami', 'ach', 'owi', 'owa', 'ego', 'iej', 'iem', 'ie', 'y', 'a', 'u'):
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                items.append(token[:-len(suffix)])
        deduped = []
        seen = set()
        for item in items:
            if item not in seen and len(item) >= 3:
                deduped.append(item)
                seen.add(item)
        return tuple(deduped)
    expanded: list[str] = []
    for token in text.split(' '):
        if len(token) < 3 or token in stop:
            continue
        expanded.extend(variants(token))
    seen: set[str] = set()
    deduped: list[str] = []
    for token in expanded:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return tuple(deduped)


def _query_surface_candidate_phrases(query: str) -> tuple[str, ...]:
    normalized_query = _normalized_match_text(query)
    if not normalized_query:
        return ()
    stop_tokens = {
        'co', 'czy', 'jak', 'kiedy', 'gdzie', 'ktory', 'która', 'ktore', 'które', 'wykazala', 'wykazała', 'ustalila', 'ustaliła',
        'kontrola', 'kontroli', 'ministerstwa', 'ministerstwo', 'nik', 'sprawie', 'dotyczacy', 'dotyczący', 'wyniki', 'raport',
        'official', 'statement', 'update', 'news', 'latest', 'with', 'from', 'about', 'what', 'which', 'did', 'does',
    }
    tokens = [token for token in normalized_query.split(' ') if len(token) >= 3 and token not in stop_tokens]
    phrases: list[str] = []
    for size in (5, 4, 3, 2):
        for index in range(0, max(0, len(tokens) - size + 1)):
            phrase_tokens = tokens[index:index + size]
            if len(phrase_tokens) < 2:
                continue
            phrases.append(' '.join(phrase_tokens))
    if tokens:
        phrases.extend(' '.join(pair) for pair in zip(tokens, tokens[1:]) if len(pair) == 2)
    deduped: list[str] = []
    seen: set[str] = set()
    for phrase in phrases:
        compact = phrase.replace(' ', '')
        if phrase in seen or compact in seen:
            continue
        seen.add(phrase)
        seen.add(compact)
        deduped.append(phrase)
        if compact != phrase:
            deduped.append(compact)
    return tuple(deduped[:16])


def _subject_anchor_variants(query: str, *, subject_sheet: SubjectSheet | None = None, planning_analysis: PlanningAnalysis | None = None) -> tuple[str, ...]:
    planning = planning_analysis or _build_fallback_planning_analysis(query)
    entity_names = [
        (hypothesis.canonical_name or hypothesis.surface_form).strip()
        for hypothesis in planning.entity_hypotheses
        if (hypothesis.canonical_name or hypothesis.surface_form).strip()
    ]
    anchors: list[str] = []
    type_tokens = {
        'szpital', 'szpitala', 'hospital', 'klinika', 'clinic', 'school', 'szkol', 'zespol',
        'ministerstwo', 'urzad', 'urząd', 'izba', 'nik', 'instytut', 'centrum'
    }
    if subject_sheet is not None:
        entity_names = [subject_sheet.primary_subject.name, *[item.name for item in subject_sheet.related_entities], *list(subject_sheet.aliases), *entity_names]
    for entity_name in entity_names:
        tokens = list(_match_tokens(entity_name))
        if len(tokens) < 2:
            continue
        type_like = [token for token in tokens if token in type_tokens]
        topic_like = [token for token in tokens if token not in type_tokens and len(token) >= 5]
        if type_like and topic_like:
            base = [type_like[0], topic_like[0]]
            anchors.append(' '.join(base))
            anchors.append(''.join(base))
            anchors.append(' '.join(token[: max(5, len(token) - 3)] for token in base))
            anchors.append(''.join(token[: max(5, len(token) - 3)] for token in base))
    for phrase in _query_surface_candidate_phrases(query):
        tokens = [token for token in phrase.split() if token in type_tokens or len(token) >= 5]
        if len(tokens) >= 2 and any(token in type_tokens for token in tokens):
            base = tokens[:2]
            anchors.append(' '.join(base))
            anchors.append(''.join(base))
    deduped: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        normalized = _normalized_match_text(anchor)
        compact = normalized.replace(' ', '')
        for candidate in (normalized, compact):
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            deduped.append(candidate)
    return tuple(deduped[:12])


def _entity_match_score(*, query: str, hit: SearchHit, subject_sheet: SubjectSheet | None = None, planning_analysis: PlanningAnalysis | None = None) -> int:
    haystack = _normalized_match_text(f"{hit.title} {hit.url} {hit.snippet}")
    compact_haystack = haystack.replace(' ', '')
    if not haystack:
        return 0

    score = 0
    planning = planning_analysis or _build_fallback_planning_analysis(query)
    entity_names = [
        (hypothesis.canonical_name or hypothesis.surface_form).strip()
        for hypothesis in planning.entity_hypotheses
        if (hypothesis.canonical_name or hypothesis.surface_form).strip()
    ]
    for anchor in _subject_anchor_variants(query, subject_sheet=subject_sheet, planning_analysis=planning):
        if not anchor:
            continue
        if anchor in haystack or anchor in compact_haystack:
            score = max(score, 8)
    candidate_phrases = list(entity_names) + (list(subject_sheet.aliases) if subject_sheet is not None else []) + list(_query_surface_candidate_phrases(query))
    seen_phrases: set[str] = set()
    for index, entity_name in enumerate(candidate_phrases):
        normalized_name = _normalized_match_text(entity_name)
        if not normalized_name or normalized_name in seen_phrases:
            continue
        seen_phrases.add(normalized_name)
        tokens = _match_tokens(entity_name)
        if len(tokens) < 2:
            continue
        matched = sum(1 for token in tokens if token in haystack)
        if matched == 0:
            continue
        ratio = matched / len(tokens)
        boost = 0
        if ratio >= 0.99 and len(tokens) >= 2:
            boost = 8
        elif ratio >= 0.74:
            boost = 5
        elif ratio >= 0.5:
            boost = 3
        if index == 0 and entity_names:
            boost += 2
        score = max(score, boost)
    return score


def _is_off_topic_institutional_official_hit(*, query: str, hit: SearchHit) -> bool:
    if _classify_query(query) is not ResearchQueryClass.GENERAL:
        return False
    if _source_type(hit.url, hit.title) != 'official_docs':
        return False
    lowered_query = query.lower()
    institutional_intent = any(token in lowered_query for token in ('nik', 'ministerstwo', 'urząd', 'urzad', 'government', 'official', 'gov', 'regulator', 'kontrola'))
    if not institutional_intent:
        return False
    relevance = _general_relevance_score(query=query, hit=hit)
    entity_match = _entity_match_score(query=query, hit=hit)
    normalized_url = _normalized_match_text(hit.url)
    if entity_match >= 3:
        return False
    if relevance >= 7:
        return False
    candidate_phrases = _query_surface_candidate_phrases(query)
    if any(phrase in normalized_url for phrase in candidate_phrases if len(phrase.split()) >= 2):
        return False
    broad_off_topic_markers = (
        'dzialania nik', 'wyniki kontroli nik', 'wyszukiwarka', 'zyciorys', 'obwodnica', 'gazowej sieci', 'ochrony zdrowia'
    )
    return any(marker in normalized_url for marker in broad_off_topic_markers)


def _filter_hits_for_extraction(*, query: str, hits: tuple[SearchHit, ...], relevance_judge: "LlmSearchRelevanceJudge | None" = None, official_evidence_judge: "LlmOfficialEvidenceJudge | None" = None, subject_sheet: SubjectSheet | None = None, planning_analysis: PlanningAnalysis | None = None) -> PreExtractionFilterOutcome:
    return _filter_hits_for_extraction_with_diagnostics(query=query, hits=hits, relevance_judge=relevance_judge, official_evidence_judge=official_evidence_judge, subject_sheet=subject_sheet, planning_analysis=planning_analysis)["outcome"]


def _filter_hits_for_extraction_with_diagnostics(*, query: str, hits: tuple[SearchHit, ...], relevance_judge: "LlmSearchRelevanceJudge | None" = None, official_evidence_judge: "LlmOfficialEvidenceJudge | None" = None, subject_sheet: SubjectSheet | None = None, planning_analysis: PlanningAnalysis | None = None) -> dict[str, object]:
    query_class = _classify_query(query)
    scientific_intent = any(token in query.lower() for token in ('study', 'studies', 'systematic review', 'meta-analysis', 'literature', 'journal', 'po 2023', 'after 2023', 'zdrowie psychiczne', 'mental health', 'peer-reviewed', 'pubmed'))
    preservation_classes = {ResearchQueryClass.GENERAL, ResearchQueryClass.BROAD_CONCEPT, ResearchQueryClass.CURRENT_NEWS}
    institutional_intent = any(token in query.lower() for token in ('nik', 'ministerstwo', 'urząd', 'urzad', 'government', 'official', 'gov', 'regulator', 'kontrola'))
    preservation_active = query_class in preservation_classes and (institutional_intent or scientific_intent)

    def _weighted_order(hit: SearchHit) -> tuple[int, int, int, int, str]:
        source_type = _source_type(hit.url, hit.title)
        relevance = _general_relevance_score(query=query, hit=hit)
        authority = _authority_signal_score(query=query, hit=hit)
        entity_match = _entity_match_score(query=query, hit=hit)
        if institutional_intent:
            order = {
                'official_docs': 0,
                'docs': 1,
                'analysis': 2,
                'data': 3,
                'generic': 4,
                'blog': 5,
                'vendor_docs': 6,
                'forum': 7,
                'video': 8,
                'snippet_repo': 9,
            }
        elif scientific_intent:
            order = {
                'analysis': 0,
                'data': 1,
                'official_docs': 2,
                'docs': 3,
                'generic': 4,
                'blog': 5,
                'vendor_docs': 6,
                'forum': 7,
                'video': 8,
                'snippet_repo': 9,
            }
        else:
            order = {
                'official_docs': 0,
                'analysis': 1,
                'data': 2,
                'docs': 3,
                'generic': 4,
                'blog': 5,
                'vendor_docs': 6,
                'forum': 7,
                'video': 8,
                'snippet_repo': 9,
            }
        return (order.get(source_type, 9), -entity_match, -authority, -relevance, hit.url)

    if not _procedural_query_bias(query):
        if not preservation_active:
            outcome = PreExtractionFilterOutcome(
                kept_hits=hits,
                seen_count=len(hits),
                kept_count=len(hits),
                dropped_count=0,
                authority_policy_applied=False,
                fallback_used=False,
                dropped_source_types=(),
            )
            return {
                'outcome': outcome,
                'diagnostics': [
                    {
                        'url': hit.url,
                        'title': hit.title,
                        'source_type': _source_type(hit.url, hit.title),
                        'general_relevance': _general_relevance_score(query=query, hit=hit),
                        'authority_signal': _authority_signal_score(query=query, hit=hit),
                        'entity_match': _entity_match_score(query=query, hit=hit, subject_sheet=subject_sheet, planning_analysis=planning_analysis),
                        'bucket': 'kept',
                        'reason': 'preservation_inactive_pass_through',
                        'final_disposition': 'kept',
                    }
                    for hit in hits
                ],
                'kept_urls': [hit.url for hit in hits],
                'dropped_urls': [],
            }
        strong: list[SearchHit] = []
        secondary: list[SearchHit] = []
        dropped: list[SearchHit] = []
        diagnostics: list[dict[str, object]] = []
        for hit in hits:
            source_type = _source_type(hit.url, hit.title)
            relevance = _general_relevance_score(query=query, hit=hit)
            authority = _authority_signal_score(query=query, hit=hit)
            entity_match = _entity_match_score(query=query, hit=hit, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
            order_key = _weighted_order(hit)
            diag = {
                'url': hit.url,
                'title': hit.title,
                'source_type': source_type,
                'general_relevance': relevance,
                'authority_signal': authority,
                'entity_match': entity_match,
                'weighted_order': list(order_key[:-1]),
                'weighted_tiebreak_url': order_key[-1],
            }
            if source_type in {'forum', 'video', 'snippet_repo'}:
                diagnostics.append({**diag, 'bucket': 'dropped', 'reason': 'source_type_excluded'})
                dropped.append(hit)
                continue
            if _is_off_topic_institutional_official_hit(query=query, hit=hit):
                if relevance_judge is not None and relevance_judge.accept_hit(query=query, hit=hit):
                    diagnostics.append({**diag, 'bucket': 'secondary', 'reason': 'llm_rescued_institutional_off_topic_gate'})
                    secondary.append(hit)
                    continue
                diagnostics.append({**diag, 'bucket': 'dropped', 'reason': 'institutional_off_topic_gate'})
                dropped.append(hit)
                continue
            if source_type == 'official_docs' and (relevance >= 4 or 'nik' in query.lower() or 'gov' in hit.url.lower()):
                llm_verdict = None
                if official_evidence_judge is not None and any(token in query.lower() for token in ('ministerstwo', 'urzęd', 'urzad', 'official', 'gov', 'podatki.gov.pl', 'mf', 'kas', 'najem', 'wynajem', 'podatk')):
                    llm_verdict, llm_confidence, llm_reason = official_evidence_judge.judge_hit(query=query, hit=hit, planning_analysis=planning_analysis)
                    diag = {**diag, 'llm_official_evidence_verdict': llm_verdict, 'llm_official_evidence_confidence': llm_confidence, 'llm_official_evidence_reason': llm_reason}
                    if llm_verdict == 'reject':
                        diagnostics.append({**diag, 'bucket': 'dropped', 'reason': 'llm_official_reject'})
                        dropped.append(hit)
                        continue
                    if llm_verdict == 'collateral':
                        diagnostics.append({**diag, 'bucket': 'secondary', 'reason': 'llm_official_collateral'})
                        secondary.append(hit)
                        continue
                    if llm_verdict == 'supporting':
                        diagnostics.append({**diag, 'bucket': 'secondary', 'reason': 'llm_official_supporting'})
                        secondary.append(hit)
                        continue
                    if llm_verdict == 'primary':
                        diagnostics.append({**diag, 'bucket': 'strong', 'reason': 'llm_official_primary'})
                        strong.append(hit)
                        continue
                diagnostics.append({**diag, 'bucket': 'strong', 'reason': 'official_docs_priority'})
                strong.append(hit)
                continue
            if source_type in {'analysis', 'data'} and (relevance >= 3 or scientific_intent):
                diagnostics.append({**diag, 'bucket': 'strong', 'reason': 'analysis_or_data_priority'})
                strong.append(hit)
                continue
            if relevance >= 5:
                diagnostics.append({**diag, 'bucket': 'secondary', 'reason': 'secondary_relevance'})
                secondary.append(hit)
                continue
            diagnostics.append({**diag, 'bucket': 'dropped', 'reason': 'low_relevance_after_preservation'})
            dropped.append(hit)

        fallback_used = False
        kept: list[SearchHit] = []
        strong_official = [hit for hit in strong if _source_type(hit.url, hit.title) == 'official_docs']
        strong_scientific = [hit for hit in strong if _source_type(hit.url, hit.title) in {'analysis', 'data'}]
        if strong:
            if strong_official:
                kept.append(sorted(strong_official, key=_weighted_order)[0])
            if scientific_intent and strong_scientific and all(item.url != sorted(strong_scientific, key=_weighted_order)[0].url for item in kept):
                kept.append(sorted(strong_scientific, key=_weighted_order)[0])
            seen_urls = {item.url for item in kept}
            for hit in sorted(strong, key=_weighted_order):
                if hit.url not in seen_urls:
                    kept.append(hit)
                    seen_urls.add(hit.url)
            for hit in sorted(secondary, key=_weighted_order):
                if len(kept) >= 3:
                    break
                if hit.url not in seen_urls:
                    kept.append(hit)
                    seen_urls.add(hit.url)
        else:
            fallback_used = True
            kept.extend(secondary[:2])
        if not kept and hits:
            fallback_used = True
            kept.append(hits[0])

        counter = Counter(_source_type(hit.url, hit.title) for hit in dropped)
        dropped_source_types = tuple(f"{source_type}:{count}" for source_type, count in sorted(counter.items()))
        outcome = PreExtractionFilterOutcome(
            kept_hits=tuple(kept),
            seen_count=len(hits),
            kept_count=len(kept),
            dropped_count=max(0, len(hits) - len(kept)),
            authority_policy_applied=True,
            fallback_used=fallback_used,
            dropped_source_types=dropped_source_types,
        )
        kept_urls = {hit.url for hit in kept}
        for item in diagnostics:
            item['final_disposition'] = 'kept' if item['url'] in kept_urls else 'dropped'
        return {
            'outcome': outcome,
            'diagnostics': diagnostics,
            'kept_urls': [hit.url for hit in kept],
            'dropped_urls': [hit.url for hit in dropped if hit.url not in kept_urls],
        }

    strong: list[SearchHit] = []
    secondary: list[SearchHit] = []
    dropped: list[SearchHit] = []
    for hit in hits:
        source_type = _source_type(hit.url, hit.title)
        authority = _authority_signal_score(query=query, hit=hit)
        relevance = _general_relevance_score(query=query, hit=hit)
        if source_type in {'forum', 'video', 'snippet_repo'}:
            dropped.append(hit)
            continue
        if source_type == 'vendor_docs' and any(_source_type(item.url, item.title) == 'official_docs' for item in strong):
            dropped.append(hit)
            continue
        if source_type == 'official_docs' or authority >= 10:
            strong.append(hit)
            continue
        if source_type in {'analysis', 'data'} and (relevance >= 3 or scientific_intent):
            strong.append(hit)
            continue
        if source_type in {'docs', 'generic'} and authority >= 4 and relevance >= 6:
            strong.append(hit)
            continue
        if source_type == 'blog' and authority < 0:
            dropped.append(hit)
            continue
        if relevance >= 5:
            secondary.append(hit)
            continue
        dropped.append(hit)

    fallback_used = False
    kept: list[SearchHit] = []
    strong_official = [hit for hit in strong if _source_type(hit.url, hit.title) == 'official_docs']
    strong_scientific = [hit for hit in strong if _source_type(hit.url, hit.title) in {'analysis', 'data'}]
    if strong:
        if strong_official:
            kept.append(sorted(strong_official, key=_weighted_order)[0])
        if scientific_intent and strong_scientific:
            best_scientific = sorted(strong_scientific, key=_weighted_order)[0]
            if all(item.url != best_scientific.url for item in kept):
                kept.append(best_scientific)
        seen_urls = {item.url for item in kept}
        for hit in sorted(strong, key=_weighted_order):
            if hit.url not in seen_urls:
                kept.append(hit)
                seen_urls.add(hit.url)
        if len(kept) < 3:
            for hit in sorted(secondary, key=_weighted_order):
                if hit.url not in seen_urls:
                    kept.append(hit)
                    seen_urls.add(hit.url)
                if len(kept) >= 3:
                    break
    else:
        fallback_used = True
        kept.extend(secondary[:2])
    if not kept and hits:
        fallback_used = True
        kept.append(hits[0])

    counter = Counter(_source_type(hit.url, hit.title) for hit in dropped)
    dropped_source_types = tuple(f"{source_type}:{count}" for source_type, count in sorted(counter.items()))
    outcome = PreExtractionFilterOutcome(
        kept_hits=tuple(kept),
        seen_count=len(hits),
        kept_count=len(kept),
        dropped_count=max(0, len(hits) - len(kept)),
        authority_policy_applied=True,
        fallback_used=fallback_used,
        dropped_source_types=dropped_source_types,
    )
    strong_urls = {hit.url for hit in strong}
    secondary_urls = {hit.url for hit in secondary}
    kept_urls = {hit.url for hit in kept}
    diagnostics = []
    for hit in hits:
        source_type = _source_type(hit.url, hit.title)
        diagnostics.append(
            {
                'url': hit.url,
                'title': hit.title,
                'source_type': source_type,
                'general_relevance': _general_relevance_score(query=query, hit=hit),
                'authority_signal': _authority_signal_score(query=query, hit=hit),
                'entity_match': _entity_match_score(query=query, hit=hit, subject_sheet=subject_sheet, planning_analysis=planning_analysis),
                'bucket': 'strong' if hit.url in strong_urls else ('secondary' if hit.url in secondary_urls else 'dropped'),
                'reason': 'procedural_or_general_authority_filter',
                'final_disposition': 'kept' if hit.url in kept_urls else 'dropped',
            }
        )
    return {
        'outcome': outcome,
        'diagnostics': diagnostics,
        'kept_urls': [hit.url for hit in kept],
        'dropped_urls': [hit.url for hit in hits if hit.url not in kept_urls],
    }


def _should_promote_official_general_finding_to_core(*, query: str, finding: ExtractedFinding) -> bool:
    if _classify_query(query) is not ResearchQueryClass.GENERAL:
        return False
    if _source_type(finding.url, finding.title) != 'official_docs':
        return False
    if _is_off_topic_institutional_official_hit(
        query=query,
        hit=SearchHit(url=finding.url, title=finding.title, snippet=finding.summary),
    ):
        return False
    hit = SearchHit(url=finding.url, title=finding.title, snippet=finding.summary)
    entity_match = _entity_match_score(
        query=query,
        hit=hit,
    )
    summary_haystack = _normalized_match_text(f"{finding.title} {finding.summary}")
    anchor_haystack = _normalized_match_text(f"{finding.title} {finding.summary} {finding.url}")
    anchor_variants = _subject_anchor_variants(query)
    anchor_match = any(anchor and anchor in anchor_haystack for anchor in anchor_variants)
    if not anchor_match:
        subject_like_phrases = [phrase for phrase in _query_surface_candidate_phrases(query) if len(phrase.split()) >= 2]
        anchor_match = any(phrase in anchor_haystack for phrase in subject_like_phrases)
    has_depth_signal = any(
        token in summary_haystack
        for token in (
            'official pdf ingest verified',
            'scope=',
            'findings',
            'ustalen',
            'recommend',
            'zalec',
            'decyz',
            'raport',
            'kontrol',
            'postepowan',
        )
    )
    return entity_match >= 3 and anchor_match and has_depth_signal



def _query_prefers_official_supporting(query: str) -> bool:
    lowered = query.lower()
    return any(token in lowered for token in (
        'oficjal', 'urzęd', 'urzed', 'instytucj', 'government', 'gov', 'publiczny', 'public law', 'mf', 'kas', 'ministerstwo',
    ))


def _supporting_bucket_rank(*, query: str, finding: ExtractedFinding) -> int:
    source_type = _source_type(finding.url, finding.title)
    if not _query_prefers_official_supporting(query):
        order = {
            'official_docs': 0,
            'docs': 1,
            'vendor_docs': 2,
            'analysis': 3,
            'data': 4,
            'generic': 5,
            'blog': 6,
        }
        return order.get(source_type, 9)
    order = {
        'official_docs': 0,
        'docs': 1,
        'vendor_docs': 2,
        'analysis': 5,
        'data': 5,
        'generic': 6,
        'blog': 7,
    }
    return order.get(source_type, 9)


def _pack_evidence_for_synthesis(*, query: str, findings: tuple[ExtractedFinding, ...]) -> PackedEvidence:
    ranked = _top_findings(findings, limit=max(6, len(findings)), query=query, family_judge=None)
    ranked = sorted(
        ranked,
        key=lambda finding: (
            0 if (finding.official_evidence_verdict == 'primary') else 1 if (finding.official_evidence_verdict == 'supporting') else 2 if (finding.official_evidence_verdict == 'collateral') else 3,
            0 if _source_type(finding.url, finding.title) == 'official_docs' else 1,
            -_enriched_exact_subject_priority_score(finding),
            -_exact_subject_content_quality_score(finding),
            0 if '[exact_subject_content_lift:prefer_primary_case_page]' in finding.summary else 1,
            0 if '[official_subject:exact_subject]' in finding.summary or finding.subject_precision_label == 'exact_subject' else 1 if '[official_subject:related_but_broad]' in finding.summary else 2,
            -len(finding.summary or ''),
        ),
    )
    query_class = _classify_query(query)
    core_limit = 2
    supporting_limit = 2 if query_class is ResearchQueryClass.PROCEDURAL_ADMIN else (3 if query_class is ResearchQueryClass.GENERAL else 2)
    core: list[ExtractedFinding] = []
    supporting: list[ExtractedFinding] = []
    background: list[ExtractedFinding] = []
    has_direct_procedural_evidence = False

    for finding in ranked:
        source_type = _source_type(finding.url, finding.title)
        if query_class is ResearchQueryClass.PROCEDURAL_ADMIN:
            if finding.official_evidence_verdict == 'reject':
                background.append(finding)
                continue
            direct = _procedural_directness_score(query=query, url=finding.url, title=finding.title) >= 3
            if direct:
                has_direct_procedural_evidence = True
            official_core_present = any(_source_type(item.url, item.title) == 'official_docs' for item in core)
            if finding.official_evidence_verdict == 'collateral' and source_type == 'official_docs':
                background.append(finding)
                continue
            if finding.official_evidence_verdict == 'primary' and source_type == 'official_docs' and len(core) < core_limit:
                core.append(finding)
                continue
            if direct and source_type == 'official_docs' and len(core) < core_limit and finding.official_evidence_verdict != 'collateral':
                core.append(finding)
                continue
            if source_type == 'official_docs' and len(core) < core_limit and not direct:
                supporting.append(finding) if len(supporting) < supporting_limit else background.append(finding)
                continue
            if source_type in {'docs', 'generic'} and len(supporting) < supporting_limit and not official_core_present:
                supporting.append(finding)
                continue
            if source_type == 'vendor_docs':
                background.append(finding)
                continue
            background.append(finding)
            continue
        if query_class is ResearchQueryClass.MARKET_SYMBOL:
            haystack = f"{finding.url} {finding.title} {finding.summary}".lower()
            if any(token in haystack for token in ('ethusdc', 'ohlcv', 'price', 'technical')) and len(core) < core_limit:
                core.append(finding)
                continue
            if len(supporting) < supporting_limit:
                supporting.append(finding)
                continue
            background.append(finding)
            continue
        if query_class is ResearchQueryClass.GENERAL:
            if finding.official_evidence_verdict == 'reject':
                background.append(finding)
                continue
            if finding.official_evidence_verdict == 'collateral' and source_type == 'official_docs':
                background.append(finding)
                continue
            general_haystack = f"{finding.title} {finding.summary}".lower()
            research_like_general = any(token in general_haystack for token in ('study', 'research', 'analysis', 'report', 'evidence'))
            prefers_official_supporting = _query_prefers_official_supporting(query)
            if finding.official_evidence_verdict == 'primary' and source_type == 'official_docs' and len(core) < core_limit:
                core.append(finding)
                continue
            if _enriched_exact_subject_priority_score(finding) >= 5 and source_type == 'official_docs' and len(core) < core_limit:
                core.append(finding)
                continue
            if '[exact_subject_content_lift:prefer_primary_case_page]' in finding.summary and source_type == 'official_docs' and len(core) < core_limit:
                core.append(finding)
                continue
            if '[official_subject:exact_subject]' in finding.summary and source_type == 'official_docs' and len(core) < core_limit:
                core.append(finding)
                continue
            if _should_promote_official_general_finding_to_core(query=query, finding=finding) and len(core) < core_limit:
                core.append(finding)
                continue
            if finding.pdf_triage_notes == 'pdf_ingest_verified' and source_type == 'official_docs' and len(core) < core_limit:
                core.append(finding)
                continue
            if not core and source_type in {'analysis', 'data'} and research_like_general and not prefers_official_supporting:
                core.append(finding)
                continue
            if len(supporting) < supporting_limit:
                rank = _supporting_bucket_rank(query=query, finding=finding)
                if finding.pdf_triage_notes == 'pdf_ingest_verified' and source_type == 'official_docs':
                    supporting.append(finding)
                    continue
                if source_type in {'official_docs', 'docs', 'generic', 'vendor_docs', 'blog', 'analysis', 'data'}:
                    if finding.official_evidence_verdict == 'collateral':
                        background.append(finding)
                        continue
                    if prefers_official_supporting and rank >= 5 and any(_supporting_bucket_rank(query=query, finding=item) < rank for item in ranked if item is not finding):
                        background.append(finding)
                        continue
                    supporting.append(finding)
                    continue
            background.append(finding)
            continue
        if len(core) < core_limit:
            core.append(finding)
        elif len(supporting) < supporting_limit:
            supporting.append(finding)
        else:
            background.append(finding)

    if query_class is not ResearchQueryClass.GENERAL and not core and supporting:
        core.append(supporting.pop(0))
    if query_class is not ResearchQueryClass.GENERAL and not core and background:
        core.append(background.pop(0))
    return PackedEvidence(
        core=tuple(core),
        supporting=tuple(supporting),
        background=tuple(background),
        has_direct_procedural_evidence=has_direct_procedural_evidence,
    )


def _evaluate_branch_proposals(
    *,
    problem_analysis: ProblemAnalysis | None,
    execution_plan: ResearchExecutionPlan | None,
    evidence_pack: ResearchEvidencePack | None,
    branch_proposals: ResearchBranchProposalSet | None,
) -> ResearchBranchEvaluation:
    if branch_proposals is None or not branch_proposals.eligible or not branch_proposals.branches:
        return ResearchBranchEvaluation()

    focus = set(problem_analysis.focus_areas if problem_analysis is not None else ())
    step_kinds = {step.kind for step in execution_plan.steps} if execution_plan is not None else set()
    evidence_core = len(evidence_pack.core) if evidence_pack is not None else 0
    evidence_supporting = len(evidence_pack.supporting) if evidence_pack is not None else 0

    scores: list[ResearchBranchScore] = []
    for branch in branch_proposals.branches:
        label = branch.label.lower()
        coverage = 0.6
        if label == "system_shape" and ({"definition", "system_shape"} & focus):
            coverage = 0.95
        elif label == "tradeoffs" and ({"key_tradeoffs"} & focus or "analyze" in step_kinds):
            coverage = 0.9
        elif label == "open_questions":
            coverage = 0.85

        evidence_fit = 0.5
        if evidence_core >= 2:
            evidence_fit += 0.25
        if evidence_supporting >= 1:
            evidence_fit += 0.15
        if label == "open_questions" and evidence_supporting == 0:
            evidence_fit -= 0.1
        evidence_fit = max(0.0, min(1.0, evidence_fit))

        priority = 0.6
        if label == "system_shape":
            priority = 0.9
        elif label == "tradeoffs":
            priority = 0.82
        elif label == "open_questions":
            priority = 0.78

        combined = round((coverage * 0.4) + (evidence_fit * 0.3) + (priority * 0.3), 3)
        scores.append(
            ResearchBranchScore(
                branch_id=branch.branch_id,
                coverage_score=round(coverage, 3),
                evidence_fit_score=round(evidence_fit, 3),
                priority_score=round(priority, 3),
                combined_score=combined,
            )
        )

    ranked = tuple(sorted(scores, key=lambda item: item.combined_score, reverse=True))
    selected = tuple(item.branch_id for item in ranked[:2])
    return ResearchBranchEvaluation(selected_branch_ids=selected, scores=ranked)


def _derive_reflection(
    *,
    problem_analysis: ProblemAnalysis | None,
    execution_plan: ResearchExecutionPlan | None,
    evidence_pack: ResearchEvidencePack | None,
    branch_evaluation: ResearchBranchEvaluation | None,
    evaluation: ResearchEvaluationArtifact | None,
) -> ResearchReflection:
    missing_topics: list[str] = []
    weak_evidence_areas: list[str] = []

    if problem_analysis is None:
        return ResearchReflection(
            goal_coverage="weak",
            missing_topics=("problem_analysis_missing",),
            weak_evidence_areas=("result_framing_missing",),
            should_follow_up=True,
            recommended_follow_up="Re-run after restoring problem analysis framing.",
        )

    focus_areas = set(problem_analysis.focus_areas)
    if "key_tradeoffs" in focus_areas and branch_evaluation is not None:
        selected = set(branch_evaluation.selected_branch_ids)
        if "branch-2" not in selected:
            missing_topics.append("tradeoffs")
    if evidence_pack is None:
        weak_evidence_areas.append("evidence_pack_missing")
    else:
        if len(evidence_pack.core) == 0:
            weak_evidence_areas.append("no_core_evidence")
        if len(evidence_pack.core) < 2 and problem_analysis.complexity is ResearchComplexity.HIGH:
            weak_evidence_areas.append("thin_core_evidence")
        if problem_analysis.query_class is ResearchQueryClass.BROAD_CONCEPT and len(evidence_pack.supporting) == 0:
            weak_evidence_areas.append("missing_supporting_context")

    if evaluation is not None and evaluation.relevance_verdict is ResearchEvaluationVerdict.WEAK:
        missing_topics.append("relevance_alignment")
    if execution_plan is not None and len(execution_plan.steps) < 2:
        weak_evidence_areas.append("shallow_execution_plan")

    if not missing_topics and not weak_evidence_areas:
        coverage = "full"
    elif len(missing_topics) <= 1 and len(weak_evidence_areas) <= 1:
        coverage = "partial"
    else:
        coverage = "weak"

    should_follow_up = bool(missing_topics or weak_evidence_areas)
    recommended_follow_up = None
    if should_follow_up:
        if missing_topics:
            recommended_follow_up = f"Investigate missing topic: {missing_topics[0]}."
        elif weak_evidence_areas:
            recommended_follow_up = f"Strengthen evidence around: {weak_evidence_areas[0]}."

    return ResearchReflection(
        goal_coverage=coverage,
        missing_topics=tuple(missing_topics[:3]),
        weak_evidence_areas=tuple(weak_evidence_areas[:3]),
        should_follow_up=should_follow_up,
        recommended_follow_up=recommended_follow_up,
    )


def _derive_branch_proposals(*, problem_analysis: ProblemAnalysis | None, execution_plan: ResearchExecutionPlan | None) -> ResearchBranchProposalSet:
    if problem_analysis is None:
        return ResearchBranchProposalSet(reason="missing_problem_analysis")
    if problem_analysis.query_class is not ResearchQueryClass.BROAD_CONCEPT and problem_analysis.complexity is not ResearchComplexity.HIGH:
        return ResearchBranchProposalSet(eligible=False, reason="query_not_eligible")

    objective = (execution_plan.objective if execution_plan is not None and execution_plan.objective else problem_analysis.goal).strip()
    branches = (
        ResearchBranchProposal(
            branch_id="branch-1",
            label="system_shape",
            objective=f"Describe the current system shape and boundaries for: {objective}",
        ),
        ResearchBranchProposal(
            branch_id="branch-2",
            label="tradeoffs",
            objective=f"Identify key tradeoffs, risks, and constraints for: {objective}",
        ),
        ResearchBranchProposal(
            branch_id="branch-3",
            label="open_questions",
            objective=f"Identify unresolved questions and evidence gaps for: {objective}",
        ),
    )
    return ResearchBranchProposalSet(
        eligible=True,
        reason="broad_or_high_complexity_query",
        branches=branches,
    )


def _to_research_evidence_pack(*, query: str, packed: PackedEvidence) -> ResearchEvidencePack:
    def convert(items: tuple[ExtractedFinding, ...]) -> tuple[ResearchFinding, ...]:
        return tuple(
            ResearchFinding(url=item.url, title=item.title, summary=item.summary)
            for item in items
        )

    return ResearchEvidencePack(
        query_class=_classify_query(query),
        core=convert(packed.core),
        supporting=convert(packed.supporting),
        background=convert(packed.background),
        has_direct_procedural_evidence=packed.has_direct_procedural_evidence,
    )


def _enriched_exact_subject_priority_score(finding: ExtractedFinding) -> int:
    source_type = _source_type(finding.url, finding.title)
    if source_type != 'official_docs':
        return 0
    score = 0
    if finding.subject_precision_label == 'exact_subject':
        score += 3
    elif '[official_subject:exact_subject]' in finding.summary:
        score += 2
    if finding.priority_band == 'exact_subject_winner':
        score += 4
    elif '[priority_band:exact_subject_winner]' in finding.summary:
        score += 2
    if finding.html_content_enriched:
        score += 3
    if '[official_html_enriched]' in finding.summary:
        score += 2
    if '[exact_subject_content_lift:prefer_primary_case_page]' in finding.summary:
        score += 2
    return score


def _exact_subject_content_quality_score(finding: ExtractedFinding) -> int:
    if _source_type(finding.url, finding.title) != 'official_docs':
        return 0
    if finding.subject_precision_label != 'exact_subject' and '[official_subject:exact_subject]' not in finding.summary:
        return 0
    score = 0
    summary = (finding.summary or '').lower()
    title = (finding.title or '').lower()
    url = (finding.url or '').lower()
    strong_content_markers = (
        'nierzetelny', 'nieprawidłowy', 'nieprawidlowy', 'zaniechan', 'zarzuci', 'ustaliła', 'ustalila',
        'nadzór był', 'nadzor byl', 'nie skorzystał', 'nie skorzystal', 'metodologi', 'wycen', 'obligatariusz',
        'pokrzywdzon', 'portfeli wierzytelności', 'sprawozdań finansowych', 'sprawozdan finansowych',
        '3,5 mld', '3.5 mld', '3,14 mld', 'postępowania układowego', 'postepowania ukladowego',
    )
    weak_page_markers = (
        'sam przytoczony tekst ma jednak charakter niemal wyłącznie nawigacyjno-teaserowy',
        'sam tekst jest jednak głównie komunikatem o przekazaniu zawiadomienia',
        'strona wskazuje numer kontroli',
        'odsyła do',
        'wynik dokładnie odnoszący się do sprawy',
    )
    landing_like_markers = (
        '/kontrole/', '/tagi/', 'find=', 'pobierz,', 'wystąpienie pokontrolne', 'wystapienie pokontrolne',
    )
    score += min(6, sum(1 for marker in strong_content_markers if marker in summary))
    if 'official_html_enriched' in summary:
        score += 1
    if len(summary) >= 700:
        score += 2
    elif len(summary) >= 450:
        score += 1
    if any(marker in summary for marker in weak_page_markers):
        score -= 4
    if any(marker in url for marker in landing_like_markers):
        score -= 2
    if '/aktualnosci/' in url or '/transkrypcje/' in url:
        score += 2
    if 'getback' in title and ('nierzetelny' in title or 'nieprawidłowy' in title or 'nieprawidlowy' in title):
        score += 2
    return score


def _exact_subject_winner_sort_key(finding: ExtractedFinding) -> tuple[int, int, int, int, int]:
    return (
        _enriched_exact_subject_priority_score(finding),
        _exact_subject_content_quality_score(finding),
        _pdf_promotion_score(finding),
        len(finding.summary or ''),
        len(finding.title or ''),
    )


def _pdf_promotion_score(finding: ExtractedFinding) -> int:
    if finding.pdf_triage_notes == 'pdf_ingest_verified':
        return 3
    if finding.pdf_triage_verdict == 'relevant':
        return 2
    if finding.pdf_triage_verdict == 'uncertain':
        return 1
    return 0


def _summary_markers(summary: str) -> tuple[str, ...]:
    return tuple(re.findall(r'\[([^\]]+)\]', summary or ''))


def _finding_trace_payload(
    finding: ExtractedFinding,
    *,
    bucket: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        'url': finding.url,
        'title': finding.title,
        'summary': finding.summary,
        'summary_markers': list(_summary_markers(finding.summary)),
        'source_type': _source_type(finding.url, finding.title),
        'subject_precision_label': finding.subject_precision_label,
        'priority_band': finding.priority_band,
        'official_evidence_verdict': finding.official_evidence_verdict,
        'official_evidence_confidence': finding.official_evidence_confidence,
        'html_content_enriched': finding.html_content_enriched,
        'pdf_triage_verdict': finding.pdf_triage_verdict,
        'pdf_triage_notes': finding.pdf_triage_notes,
        'exact_subject_priority_score': _enriched_exact_subject_priority_score(finding),
        'exact_subject_content_quality_score': _exact_subject_content_quality_score(finding),
        'pdf_promotion_score': _pdf_promotion_score(finding),
    }
    if bucket is not None:
        payload['bucket'] = bucket
    return payload


def _consolidate_official_finding_families(
    findings: tuple[ExtractedFinding, ...],
    *,
    query: str,
    family_judge: LlmOfficialEvidenceFamilyJudge | None = None,
) -> tuple[tuple[ExtractedFinding, ...], tuple[dict[str, object], ...]]:
    if family_judge is None:
        return findings, ()
    official = [finding for finding in findings if _source_type(finding.url, finding.title) == 'official_docs']
    if len(official) < 2:
        return findings, ()
    by_domain: dict[str, list[ExtractedFinding]] = {}
    for finding in official:
        by_domain.setdefault(_normalized_domain(finding.url), []).append(finding)
    canonical_urls: set[str] = set()
    family_trace: list[dict[str, object]] = []
    for domain, family in by_domain.items():
        if len(family) < 2:
            canonical_urls.add(family[0].url)
            continue
        chosen = family_judge.judge_family(query=query, findings=tuple(family))
        kept = tuple(chosen or (family[0].url,))
        canonical_urls.update(kept)
        family_trace.append({
            'domain': domain,
            'candidate_urls': [item.url for item in family],
            'canonical_urls': list(kept),
            'collateral_urls': [item.url for item in family if item.url not in kept],
        })
    consolidated: list[ExtractedFinding] = []
    for finding in findings:
        if _source_type(finding.url, finding.title) != 'official_docs':
            consolidated.append(finding)
            continue
        if finding.url in canonical_urls:
            consolidated.append(finding)
            continue
        if finding.official_evidence_verdict == 'primary':
            consolidated.append(finding)
            continue
        consolidated.append(replace(
            finding,
            official_evidence_verdict='collateral',
            summary=f"[llm_official_family:collateral] [llm_official_evidence:collateral] {finding.summary}",
        ))
    return tuple(consolidated), tuple(family_trace)


def _top_findings(findings: tuple[ExtractedFinding, ...], limit: int = 5, query: str | None = None, family_judge: LlmOfficialEvidenceFamilyJudge | None = None, family_trace_sink: list[dict[str, object]] | None = None, family_activation_trace_sink: dict[str, object] | None = None) -> tuple[ExtractedFinding, ...]:
    normalized_query = query or ''
    official = [finding for finding in findings if _source_type(finding.url, finding.title) == 'official_docs']
    official_domains_with_multiples = sorted({
        _normalized_domain(finding.url)
        for finding in official
        if sum(1 for item in official if _normalized_domain(item.url) == _normalized_domain(finding.url)) >= 2
    })
    if family_activation_trace_sink is not None:
        family_activation_trace_sink.update({
            'family_judge_present': family_judge is not None,
            'official_findings_count_before_family': len(official),
            'official_domains_with_multiples': official_domains_with_multiples,
            'family_consolidation_invoked': family_judge is not None and bool(official_domains_with_multiples),
        })
    findings, family_trace = _consolidate_official_finding_families(findings, query=normalized_query, family_judge=family_judge)
    if family_trace_sink is not None:
        family_trace_sink.extend(family_trace)
    if family_activation_trace_sink is not None:
        family_activation_trace_sink['family_trace_count'] = len(family_trace)
    prefers_official = _query_prefers_official_supporting(normalized_query)
    ranked = sorted(
        findings,
        key=lambda finding: (
            1 if prefers_official and finding.official_evidence_verdict == 'primary' else 0,
            1 if prefers_official and _source_type(finding.url, finding.title) == 'official_docs' and finding.official_evidence_verdict != 'collateral' else 0,
            -1 if prefers_official and finding.official_evidence_verdict == 'collateral' else 0,
            _enriched_exact_subject_priority_score(finding),
            _exact_subject_content_quality_score(finding),
            _pdf_promotion_score(finding),
            -_source_rank_for_query(query=normalized_query, url=finding.url, title=finding.title),
            -len(finding.summary),
            -len(finding.title),
        ),
        reverse=True,
    )
    selected: list[ExtractedFinding] = []
    seen_types: set[str] = set()
    blocked_types = {'forum', 'video', 'snippet_repo'} if _procedural_query_bias(normalized_query) else set()
    official_present = any(_source_type(finding.url, finding.title) == 'official_docs' for finding in ranked)
    for finding in ranked:
        source_type = _source_type(finding.url, finding.title)
        if source_type in blocked_types:
            continue
        if official_present and source_type == 'vendor_docs':
            continue
        if official_present and source_type == 'vendor_docs':
            continue
        if source_type in seen_types:
            continue
        selected.append(finding)
        seen_types.add(source_type)
        if len(selected) >= limit:
            return tuple(selected)
    for finding in ranked:
        if finding in selected:
            continue
        source_type = _source_type(finding.url, finding.title)
        if source_type in blocked_types:
            continue
        selected.append(finding)
        if len(selected) >= limit:
            break
    return tuple(selected)


def _resolve_search_provider_names(search: ResearchSearchAdapter, configured_provider: str | None) -> tuple[str, ...]:
    if configured_provider:
        return (configured_provider,)
    active = getattr(search, "active_provider_names", None)
    if isinstance(active, tuple) and active:
        return active
    provider_name = getattr(search, "provider_name", None)
    if isinstance(provider_name, str) and provider_name and provider_name != "chained":
        return (provider_name,)
    return ()


def _actual_search_provider_names(search: ResearchSearchAdapter) -> tuple[str, ...]:
    last = getattr(search, "last_provider_names", None)
    if isinstance(last, tuple) and last:
        return tuple(str(name) for name in last if str(name))
    return _resolve_search_provider_names(search, configured_provider=None)


def _clean_report_summary_text(summary: str) -> str:
    cleaned = re.sub(r'\[[^\]]+\]', '', summary or '')
    cleaned = re.sub(r'\bconfidence=\d+(?:\.\d+)?;?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bscope=[^;]+;?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bentity=[^;]+;?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bpages=[^;]+;?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bfindings=[^;]+;?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\breason=[^;]+;?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ;')
    return cleaned.strip()


def _report_source_context(findings: tuple[ExtractedFinding, ...]) -> str:
    if not findings:
        return '- No selected sources.'
    lines: list[str] = []
    for idx, finding in enumerate(findings[:8], start=1):
        source_type = _source_type(finding.url, finding.title)
        role = 'core_candidate' if idx <= 2 else 'supporting_candidate'
        cleaned_summary = _clean_report_summary_text(finding.summary)
        lines.append(
            f"- Source {idx}\n"
            f"  - role: {role}\n"
            f"  - type: {source_type}\n"
            f"  - title: {finding.title}\n"
            f"  - url: {finding.url}\n"
            f"  - content: {cleaned_summary or 'No useful extracted content.'}"
        )
    return '\n'.join(lines)


def _generate_short_report_title(*, query: str, findings: tuple[ExtractedFinding, ...]) -> str:
    trimmed_query = ' '.join((query or '').split())
    if not trimmed_query and findings:
        trimmed_query = findings[0].title
    base = trimmed_query.rstrip(' ?.!')
    separators = (' Skup się ', ' Skoncentruj się ', ' Użyj ', ' Nie ', ' Bez ')
    for separator in separators:
        if separator in base:
            base = base.split(separator, 1)[0].rstrip(' ,;:-')
            break
    if ':' in base and len(base) > 72:
        base = base.split(':', 1)[0].rstrip(' ,;:-')
    title = base or 'SourceTrace report'
    title = re.sub(r'\s+', ' ', title).strip(' —')
    if len(title) > 72:
        title = title[:69].rstrip(' ,;:-') + '…'
    return title or 'SourceTrace report'


def _build_research_report_prompt(*, query: str, round_number: int, previous_answer: str, evidence: str, source_context: str, query_class: ResearchQueryClass, has_direct_procedural_evidence: bool) -> str:
    base_rules = (
        "You are writing an operator-facing Deep Research report.\n"
        "Be concrete, compact, evidence-first, and useful to a technical operator.\n"
        "Do not narrate your process, confidence theater, or generic caveats.\n"
        "Only include claims supported by the evidence block.\n"
        "Do not invent facts, steps, prerequisites, labels, paths, or recommendations.\n"
        "If the evidence does not support a detail, say explicitly that you do not know or that the current evidence is insufficient.\n"
        "If evidence is missing for an exact step, say so in Uncertainty instead of inventing it.\n"
        "Prefer exact product names, exact admin paths, and explicit constraints when supported.\n"
        "Keep the answer tight and high-signal.\n\n"
    )
    section_contract = (
        "Return plain markdown with exactly these sections in this order:\n"
        "## Current answer\n"
        "- 2 to 5 sentences answering the query directly\n\n"
        "## Key findings\n"
        "- 3 to 6 bullet points using only the strongest findings\n\n"
        "## Uncertainty\n"
        "- 1 to 4 bullet points describing what is still weak, ambiguous, or missing\n\n"
        "## Next checks\n"
        "- 1 to 4 bullet points for the next most useful verification steps\n"
    )
    class_overlay = _research_report_prompt_overlay(query_class, has_direct_procedural_evidence=has_direct_procedural_evidence)
    return (
        f"{base_rules}"
        f"Query class: {query_class.value}\n"
        f"Query: {query}\n"
        f"Round: {round_number}\n"
        f"Previous answer: {previous_answer}\n\n"
        f"Class-specific shaping rules:\n{class_overlay}\n\n"
        f"Evidence:\n{evidence}\n\n"
        f"Selected source context (use this to write natural report text; do not expose internal extraction markers, bracket tags, or raw diagnostic fields):\n{source_context}\n\n"
        f"{section_contract}"
    )


def _research_report_prompt_overlay(query_class: ResearchQueryClass, *, has_direct_procedural_evidence: bool) -> str:
    if query_class is ResearchQueryClass.PROCEDURAL_ADMIN:
        exactness_rule = (
            "- Direct procedural evidence is present, so exact entry points, menu paths, and settings may be stated only when they are supported by the evidence.\n"
            if has_direct_procedural_evidence else
            "- Direct procedural evidence is not confirmed in the current evidence set. Do not state exact click-paths, menu chains, field labels, or exact setup steps. Give a high-level procedural answer and say explicitly which exact steps are not confirmed.\n"
        )
        return (
            "- Optimize for an admin/operator who wants the practical path, not a conceptual essay.\n"
            f"{exactness_rule}"
            "- In Current answer, prefer this order when evidence supports it: exact admin path or entry point, main action, important option/scope, and validation outcome.\n"
            "- In Key findings, prioritize: official product path, prerequisites/licensing, rollout-safe guidance, exact controls/settings, and validation/report-only guidance.\n"
            "- Distinguish clearly between confirmed steps and recommended safeguards.\n"
            "- If official docs are present, anchor the answer to them rather than secondary blogs.\n"
            "- Do not invent wizard clicks, field names, or prerequisites that are not evidenced.\n"
            "- If the evidence is procedural but incomplete, say exactly what step details are still missing in Uncertainty."
        )
    if query_class is ResearchQueryClass.BROAD_CONCEPT:
        return (
            "- Optimize for a clear conceptual explanation.\n"
            "- Define the thing first, then contrast it with nearby concepts if helpful.\n"
            "- Preserve ambiguity where the evidence does not support one clean definition."
        )
    if query_class is ResearchQueryClass.CURRENT_NEWS:
        return (
            "- Optimize for recency, attribution, and restraint.\n"
            "- Separate confirmed developments from tentative claims.\n"
            "- Surface conflicts or timeline uncertainty explicitly."
        )
    if query_class is ResearchQueryClass.MARKET_SYMBOL:
        return (
            "- Optimize for exact instrument matching and time-window discipline.\n"
            "- Avoid mixing spot and derivatives unless the evidence explicitly requires it.\n"
            "- Prefer concrete market observations over generic commentary."
        )
    return (
        "- Give the clearest direct answer supported by the evidence.\n"
        "- Prefer precise statements over broad summaries.\n"
        "- If an official exact-subject case page is present, prioritize it over broader official collateral.\n"
        "- Surface missing verification explicitly."
    )


def _classify_query(query: str) -> ResearchQueryClass:
    lowered = query.lower().strip()
    if _looks_like_market_query(lowered):
        return ResearchQueryClass.MARKET_SYMBOL
    if _procedural_query_bias(lowered):
        return ResearchQueryClass.PROCEDURAL_ADMIN
    if any(token in lowered for token in ("latest", "breaking", "today", "this week", "news", "developments", "rollout")):
        return ResearchQueryClass.CURRENT_NEWS
    if any(token in lowered for token in ("architecture", "design", "how it works", "workflow", "system shape")):
        return ResearchQueryClass.BROAD_CONCEPT
    return ResearchQueryClass.GENERAL


def _planning_complexity(query: str, *, query_class: ResearchQueryClass) -> ResearchComplexity:
    lowered = query.lower()
    if query_class in {ResearchQueryClass.PROCEDURAL_ADMIN, ResearchQueryClass.MARKET_SYMBOL}:
        return ResearchComplexity.LOW
    if query_class is ResearchQueryClass.BROAD_CONCEPT:
        return ResearchComplexity.HIGH
    if query_class is ResearchQueryClass.CURRENT_NEWS:
        return ResearchComplexity.MEDIUM
    if any(token in lowered for token in ("compare", "vs", "tradeoff", "decision", "plan", "strategy")):
        return ResearchComplexity.HIGH
    return ResearchComplexity.MEDIUM


def _planning_focus_areas(query_class: ResearchQueryClass) -> tuple[str, ...]:
    focus_areas_map: dict[ResearchQueryClass, tuple[str, ...]] = {
        ResearchQueryClass.PROCEDURAL_ADMIN: ("task_path", "required_controls", "validation"),
        ResearchQueryClass.BROAD_CONCEPT: ("definition", "system_shape", "key_tradeoffs"),
        ResearchQueryClass.CURRENT_NEWS: ("recent_developments", "timeline", "source_recency"),
        ResearchQueryClass.MARKET_SYMBOL: ("instrument_scope", "time_window", "market_signal"),
        ResearchQueryClass.GENERAL: ("main_question",),
    }
    return focus_areas_map[query_class]


def _planning_constraints(query_class: ResearchQueryClass) -> tuple[str, ...]:
    constraints: list[str] = []
    if query_class is ResearchQueryClass.PROCEDURAL_ADMIN:
        constraints.append("state_exact_steps_only_when_supported_by_evidence")
    if query_class is ResearchQueryClass.CURRENT_NEWS:
        constraints.append("prefer_recent_attributed_evidence")
    if query_class is ResearchQueryClass.MARKET_SYMBOL:
        constraints.append("keep_instrument_and_time_window_consistent")
    return tuple(constraints)


def _detect_entity_hypotheses(query: str) -> tuple[EntityHypothesis, ...]:
    short_form_groups = re.findall(r"\b([A-Z]{2,3}(?:/[A-Z]{2,3})+)\b", query)
    if not short_form_groups:
        return ()
    candidate_meanings = {
        "PO": ("product owner", "purchase order"),
        "KO": ("kickoff", "knockout"),
    }
    hypotheses: list[EntityHypothesis] = []
    seen: set[str] = set()
    for group in short_form_groups:
        for token in group.split("/"):
            if token in seen:
                continue
            seen.add(token)
            hypotheses.append(
                EntityHypothesis(
                    surface_form=token,
                    entity_type="acronym",
                    candidate_meanings=candidate_meanings.get(token, ()),
                    confidence="low",
                    reasoning="Short acronym appears without enough context to resolve safely.",
                )
            )
    return tuple(hypotheses)


def _planning_ambiguity_notes(entity_hypotheses: tuple[EntityHypothesis, ...]) -> tuple[str, ...]:
    return tuple(
        f"Ambiguous acronym '{hypothesis.surface_form}' appears without enough context to resolve safely."
        for hypothesis in entity_hypotheses
    )


def _planning_execution_mode(
    *,
    query_class: ResearchQueryClass,
    complexity: ResearchComplexity,
    ambiguity_notes: tuple[str, ...],
) -> PlanningExecutionMode:
    if ambiguity_notes:
        return PlanningExecutionMode.DISAMBIGUATE
    if query_class in {ResearchQueryClass.BROAD_CONCEPT, ResearchQueryClass.CURRENT_NEWS}:
        return PlanningExecutionMode.MULTI_STEP
    if complexity is ResearchComplexity.HIGH:
        return PlanningExecutionMode.MULTI_STEP
    return PlanningExecutionMode.DIRECT


def _build_fallback_planning_analysis(query: str) -> PlanningAnalysis:
    normalized = query.strip()
    query_class = _classify_query(normalized)
    complexity = _planning_complexity(normalized, query_class=query_class)
    entity_hypotheses = _detect_entity_hypotheses(normalized)
    ambiguity_notes = _planning_ambiguity_notes(entity_hypotheses)
    return PlanningAnalysis(
        query_class=query_class,
        complexity=complexity,
        execution_mode=_planning_execution_mode(
            query_class=query_class,
            complexity=complexity,
            ambiguity_notes=ambiguity_notes,
        ),
        goal=normalized,
        focus_areas=_planning_focus_areas(query_class),
        constraints=_planning_constraints(query_class),
        entity_hypotheses=entity_hypotheses,
        ambiguity_notes=ambiguity_notes,
        analysis_version="planning_analysis_v1_fallback",
    )


def _planning_analysis_to_problem_analysis(planning_analysis: PlanningAnalysis) -> ProblemAnalysis:
    return ProblemAnalysis(
        query_class=planning_analysis.query_class,
        complexity=planning_analysis.complexity,
        goal=planning_analysis.goal,
        focus_areas=planning_analysis.focus_areas,
        constraints=planning_analysis.constraints,
        analysis_version="problem_analyzer_v1",
    )




def _dedupe_text_items(items: list[str], *, limit: int = 12) -> tuple[str, ...]:
    kept: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = ' '.join(str(item).split()).strip()
        if not value:
            continue
        key = _normalized_match_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(value)
        if len(kept) >= limit:
            break
    return tuple(kept)


def _fallback_subject_sheet(*, query: str, planning_analysis: PlanningAnalysis | None = None) -> SubjectSheet:
    planning = planning_analysis or _build_fallback_planning_analysis(query)
    primary_name = next(((item.canonical_name or item.surface_form).strip() for item in planning.entity_hypotheses if (item.canonical_name or item.surface_form).strip()), query.strip())
    aliases = _dedupe_text_items([primary_name, query.strip(), *[(item.surface_form or '').strip() for item in planning.entity_hypotheses]], limit=10)
    anchor_terms = _dedupe_text_items(list(_subject_anchor_variants(query, subject_sheet=None, planning_analysis=planning)) + list(aliases), limit=12)
    related = tuple(
        SubjectEntity(
            name=(item.canonical_name or item.surface_form).strip(),
            type=item.entity_type or 'unknown',
            role='other',
            confidence=0.5,
        )
        for item in planning.entity_hypotheses
        if (item.canonical_name or item.surface_form).strip() and (item.canonical_name or item.surface_form).strip() != primary_name
    )
    return SubjectSheet(
        query_summary=query.strip(),
        primary_subject=SubjectEntity(name=primary_name, type='unknown', confidence=0.5),
        related_entities=related,
        aliases=aliases,
        anchor_terms=anchor_terms,
        proceeding_terms=_dedupe_text_items(['kontrola', 'ustalenia', 'decyzje', 'zalecenia', 'komunikat', 'postępowanie'], limit=8),
        must_have_signals=_dedupe_text_items(['official source or institutional source', 'subject match', 'control or findings or decision context'], limit=6),
        acceptable_adjacent_signals=_dedupe_text_items(['stanowisko miasta', 'stanowisko szpitala', 'komunikat urzędowy', 'śledztwo lub czynności'], limit=6),
        disqualifying_signals=_dedupe_text_items(['general report unrelated to subject', 'other hospital', 'generic health system report'], limit=6),
        official_source_hints=(SubjectHint(kind='source_type', value='official_docs'), SubjectHint(kind='domain', value='gov.pl'), SubjectHint(kind='domain', value='nik.gov.pl')),
    )


def _build_subject_sheet_prompt(*, query: str, planning_analysis: PlanningAnalysis | None, fallback: SubjectSheet) -> str:
    planning_context = ''
    if planning_analysis is not None:
        planning_context = json.dumps({
            'goal': planning_analysis.goal,
            'focus_areas': list(planning_analysis.focus_areas),
            'constraints': list(planning_analysis.constraints),
            'entity_hypotheses': [
                {
                    'surface_form': item.surface_form,
                    'entity_type': item.entity_type,
                    'canonical_name': item.canonical_name,
                    'candidate_meanings': list(item.candidate_meanings),
                    'confidence': item.confidence,
                }
                for item in planning_analysis.entity_hypotheses
            ],
        }, ensure_ascii=False)
    fallback_payload = json.dumps({
        'query_summary': fallback.query_summary,
        'primary_subject': {'name': fallback.primary_subject.name, 'type': fallback.primary_subject.type, 'confidence': fallback.primary_subject.confidence},
        'related_entities': [vars(item) for item in fallback.related_entities],
        'aliases': list(fallback.aliases),
        'anchor_terms': list(fallback.anchor_terms),
        'proceeding_terms': list(fallback.proceeding_terms),
        'must_have_signals': list(fallback.must_have_signals),
        'acceptable_adjacent_signals': list(fallback.acceptable_adjacent_signals),
        'disqualifying_signals': list(fallback.disqualifying_signals),
        'official_source_hints': [vars(item) for item in fallback.official_source_hints],
    }, ensure_ascii=False)
    return (
        'Return strict JSON only. Build a compact subject sheet for research-hit acceptance. '
        'Prefer precise subject/entity framing over broad summaries. '
        'Do not invent extra institutions unless strongly implied by the query or planning context.\n'
        'Schema keys: query_summary, primary_subject, related_entities, aliases, anchor_terms, proceeding_terms, must_have_signals, acceptable_adjacent_signals, disqualifying_signals, official_source_hints.\n'
        'primary_subject keys: name, type, confidence. related_entities keys: name, type, role, confidence. official_source_hints keys: kind, value.\n'
        f'Query: {query}\n'
        f'Planning context: {planning_context or "NONE"}\n'
        f'Fallback subject sheet: {fallback_payload}\n'
    )


def _subject_entity_from_payload(item: Any) -> SubjectEntity | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get('name', '')).strip()
    if not name:
        return None
    try:
        confidence = float(item.get('confidence', 0.0))
    except Exception:
        confidence = 0.0
    return SubjectEntity(name=name, type=str(item.get('type', 'unknown')).strip() or 'unknown', role=str(item.get('role', 'other')).strip() or 'other', confidence=max(0.0, min(1.0, confidence)))


def _subject_sheet_from_llm_payload(payload: Any, *, fallback: SubjectSheet) -> SubjectSheet | None:
    if not isinstance(payload, dict):
        return None
    primary = _subject_entity_from_payload(payload.get('primary_subject'))
    if primary is None:
        primary = fallback.primary_subject
    related = tuple(item for item in (_subject_entity_from_payload(entry) for entry in payload.get('related_entities', [])) if item is not None)
    hints = []
    for entry in payload.get('official_source_hints', []):
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get('kind', '')).strip()
        value = str(entry.get('value', '')).strip()
        if kind and value:
            hints.append(SubjectHint(kind=kind, value=value))
    sheet = SubjectSheet(
        query_summary=str(payload.get('query_summary', '')).strip() or fallback.query_summary,
        primary_subject=primary,
        related_entities=related or fallback.related_entities,
        aliases=_dedupe_text_items(list(payload.get('aliases', [])) + list(fallback.aliases), limit=12),
        anchor_terms=_dedupe_text_items(list(payload.get('anchor_terms', [])) + list(fallback.anchor_terms), limit=12),
        proceeding_terms=_dedupe_text_items(list(payload.get('proceeding_terms', [])) + list(fallback.proceeding_terms), limit=10),
        must_have_signals=_dedupe_text_items(list(payload.get('must_have_signals', [])) + list(fallback.must_have_signals), limit=8),
        acceptable_adjacent_signals=_dedupe_text_items(list(payload.get('acceptable_adjacent_signals', [])) + list(fallback.acceptable_adjacent_signals), limit=8),
        disqualifying_signals=_dedupe_text_items(list(payload.get('disqualifying_signals', [])) + list(fallback.disqualifying_signals), limit=8),
        official_source_hints=tuple(hints) or fallback.official_source_hints,
    )
    if not sheet.primary_subject.name.strip():
        return None
    return sheet

def _build_planning_analysis_prompt(query: str, *, fallback: PlanningAnalysis) -> str:
    return (
        "You are a research planning analyzer. Return strict JSON only. "
        "Decide the best bounded planning analysis for the user's research query. "
        "Allowed query_class values: market_symbol, procedural_admin, broad_concept, current_news, general. "
        "Allowed complexity values: low, medium, high. "
        "Allowed execution_mode values: direct, multi_step, disambiguate. "
        "Return object keys: query_class, complexity, execution_mode, goal, focus_areas, constraints, entity_hypotheses, ambiguity_notes. "
        "entity_hypotheses must be an array of objects with keys: surface_form, entity_type, canonical_name, candidate_meanings, confidence, reasoning. "
        "Keep arrays short and concrete. Preserve the user's language in goal/notes when possible. "
        "If the query suggests an institution, public controversy, official review, audit, control, hospital, city office, regulator, or public-service failure, prefer planning that helps target official sources first. "
        f"User query: {query}\n"
        f"Deterministic fallback: {json.dumps(_planning_analysis_payload_for_prompt(fallback), ensure_ascii=False)}"
    )


def _planning_analysis_payload_for_prompt(analysis: PlanningAnalysis) -> dict[str, object]:
    return {
        "query_class": analysis.query_class.value,
        "complexity": analysis.complexity.value,
        "execution_mode": analysis.execution_mode.value,
        "goal": analysis.goal,
        "focus_areas": list(analysis.focus_areas),
        "constraints": list(analysis.constraints),
        "entity_hypotheses": [
            {
                "surface_form": item.surface_form,
                "entity_type": item.entity_type,
                "canonical_name": item.canonical_name,
                "candidate_meanings": list(item.candidate_meanings),
                "confidence": item.confidence,
                "reasoning": item.reasoning,
            }
            for item in analysis.entity_hypotheses
        ],
        "ambiguity_notes": list(analysis.ambiguity_notes),
    }


def _planning_analysis_from_llm_payload(payload: object, *, query: str) -> PlanningAnalysis | None:
    if not isinstance(payload, dict):
        return None
    try:
        query_class = ResearchQueryClass(str(payload.get("query_class", ResearchQueryClass.GENERAL.value)))
        complexity = ResearchComplexity(str(payload.get("complexity", ResearchComplexity.MEDIUM.value)))
        execution_mode = PlanningExecutionMode(str(payload.get("execution_mode", PlanningExecutionMode.MULTI_STEP.value)))
    except ValueError:
        return None
    lowered_query = query.lower().strip()
    institutional_audit_shape = any(token in lowered_query for token in (
        'nik', 'najwyższa izba kontroli', 'najwyzsza izba kontroli', 'raport', 'wyniki kontroli',
        'kontrola', 'ustalenia', 'komunikat', 'pokontrol', 'szpital', 'warszawa',
    )) and not any(token in lowered_query for token in ('microsoft', 'sccm', 'intune', 'entra', 'configuration manager', 'azure'))
    if institutional_audit_shape and query_class is ResearchQueryClass.PROCEDURAL_ADMIN:
        query_class = ResearchQueryClass.GENERAL
    goal = str(payload.get("goal", "")).strip() or query.strip()
    focus_areas = _normalized_planning_focus_areas(tuple(str(item).strip() for item in payload.get("focus_areas", []) if str(item).strip()))
    constraints = _normalized_planning_constraints(tuple(str(item).strip() for item in payload.get("constraints", []) if str(item).strip()))
    ambiguity_notes = tuple(str(item).strip() for item in payload.get("ambiguity_notes", []) if str(item).strip())
    entity_hypotheses = tuple(
        EntityHypothesis(
            surface_form=str(item.get("surface_form", "")).strip(),
            entity_type=str(item.get("entity_type", "unknown")).strip() or "unknown",
            canonical_name=(str(item.get("canonical_name", "")).strip() or None),
            candidate_meanings=tuple(str(candidate).strip() for candidate in item.get("candidate_meanings", []) if str(candidate).strip()),
            confidence=str(item.get("confidence", "low")).strip() or "low",
            reasoning=str(item.get("reasoning", "")).strip(),
        )
        for item in payload.get("entity_hypotheses", []) if isinstance(item, dict) and str(item.get("surface_form", "")).strip()
    )
    return PlanningAnalysis(
        query_class=query_class,
        complexity=complexity,
        execution_mode=execution_mode,
        goal=goal,
        focus_areas=focus_areas,
        constraints=constraints,
        entity_hypotheses=entity_hypotheses,
        ambiguity_notes=ambiguity_notes,
        analysis_version="planning_analysis_v1_llm",
    )


def _merge_llm_planning_with_fallback(planning: PlanningAnalysis, *, fallback: PlanningAnalysis) -> PlanningAnalysis:
    return PlanningAnalysis(
        query_class=planning.query_class,
        complexity=planning.complexity,
        execution_mode=planning.execution_mode,
        goal=planning.goal or fallback.goal,
        focus_areas=planning.focus_areas or fallback.focus_areas,
        constraints=planning.constraints or fallback.constraints,
        entity_hypotheses=planning.entity_hypotheses or fallback.entity_hypotheses,
        ambiguity_notes=planning.ambiguity_notes or fallback.ambiguity_notes,
        analysis_version=planning.analysis_version,
    )


def _derive_problem_analysis(query: str) -> ProblemAnalysis:
    return _planning_analysis_to_problem_analysis(_build_fallback_planning_analysis(query))


def _evaluate_research_result(*, query: str, findings: tuple[ResearchFinding, ...], report: str, stats: ResearchStats) -> ResearchEvaluationArtifact:
    query_class = _classify_query(query)
    urls = tuple(finding.url for finding in findings)
    source_types = tuple(_source_type(finding.url, finding.title) for finding in findings)
    source_quality_reasons: list[str] = []
    relevance_risks: list[str] = []
    overclaim_risks: list[str] = []
    missing_checks: list[str] = []

    official_count = sum(1 for source_type in source_types if source_type == 'official_docs')
    weak_count = sum(1 for source_type in source_types if source_type in {'blog', 'video', 'forum', 'snippet_repo'})
    direct_procedural_count = sum(
        1 for finding in findings
        if _procedural_directness_score(query=query, url=finding.url, title=finding.title) >= 3
    ) if query_class is ResearchQueryClass.PROCEDURAL_ADMIN else 0
    indirect_official_count = max(0, official_count - direct_procedural_count) if query_class is ResearchQueryClass.PROCEDURAL_ADMIN else 0
    report_lower = report.lower()

    if query_class is ResearchQueryClass.PROCEDURAL_ADMIN:
        if official_count < 1:
            source_quality_verdict = ResearchEvaluationVerdict.WEAK
            source_quality_reasons.append('No official procedural documentation was found in the evidence set.')
        elif direct_procedural_count < 1:
            source_quality_verdict = ResearchEvaluationVerdict.MIXED
            source_quality_reasons.append('Official documentation is present, but direct task/setup evidence is not confirmed.')
            missing_checks.append('Find at least one direct task or setup page before trusting exact procedural details.')
        elif weak_count:
            source_quality_verdict = ResearchEvaluationVerdict.MIXED
            source_quality_reasons.append('Direct procedural documentation is present, but weaker community-style sources are still mixed into the result set.')
        else:
            source_quality_verdict = ResearchEvaluationVerdict.STRONG
            source_quality_reasons.append('Direct procedural documentation is present in the evidence set.')
        if indirect_official_count > 0:
            source_quality_reasons.append('Some official sources are indirect context pages rather than direct task instructions.')
        if stats.authority_policy_applied:
            source_quality_reasons.append('Authority-first filtering was applied before extraction.')
        if stats.authority_filter_fallback_used:
            source_quality_reasons.append('Fallback admitted secondary sources because too few strong procedural sources survived filtering.')
        if weak_count:
            relevance_risks.append('Some findings still come from community, forum, video, or snippet-style sources.')
        if direct_procedural_count < 1:
            relevance_risks.append('The answer may rely on indirect procedural context rather than direct task instructions.')
        if 'microsoft learn' not in report_lower and official_count < 1:
            missing_checks.append('Verify the answer directly against current official documentation.')
    elif query_class is ResearchQueryClass.MARKET_SYMBOL:
        source_quality_verdict = ResearchEvaluationVerdict.STRONG if all(source_type in {'analysis', 'data', 'generic'} for source_type in source_types[:4]) else ResearchEvaluationVerdict.MIXED
        if any('perpetual' in (finding.title + ' ' + finding.summary).lower() for finding in findings) and any('spot' in (finding.title + ' ' + finding.summary).lower() for finding in findings):
            overclaim_risks.append('The evidence may mix spot and derivatives markets.')
        if 'ohlcv' not in report.lower() and '7-dniowe ohlcv' not in report.lower() and '7-day ohlcv' not in report.lower():
            missing_checks.append('Add one exact-market OHLCV check for the requested time window.')
        source_quality_reasons.append('Top findings are mostly market or chart-oriented sources.')
    elif query_class is ResearchQueryClass.BROAD_CONCEPT:
        source_quality_verdict = ResearchEvaluationVerdict.MIXED if weak_count else ResearchEvaluationVerdict.STRONG
        if weak_count:
            source_quality_reasons.append('The source mix includes blog-like or secondary commentary.')
        else:
            source_quality_reasons.append('The source mix is reasonably documentation/research oriented.')
        if any('irrelevant' in (finding.summary).lower() for finding in findings):
            relevance_risks.append('Some findings may be semantically noisy.')
        if 'uncertainty' not in report.lower():
            overclaim_risks.append('Broad concept answer may be too confident for a mixed evidence set.')
    elif query_class is ResearchQueryClass.CURRENT_NEWS:
        source_quality_verdict = ResearchEvaluationVerdict.MIXED
        source_quality_reasons.append('Current-news queries need stronger recency and attribution handling.')
        missing_checks.append('Verify recency and attribution across at least two attributable sources.')
    else:
        source_quality_verdict = ResearchEvaluationVerdict.MIXED
        source_quality_reasons.append('Query class is unknown, so source-quality expectations are broad.')

    if not findings:
        source_quality_verdict = ResearchEvaluationVerdict.WEAK
        relevance_verdict = ResearchEvaluationVerdict.WEAK
        truthfulness_verdict = ResearchEvaluationVerdict.MIXED
        relevance_risks.append('No findings were persisted for this result.')
        missing_checks.append('Collect at least one attributable source before trusting the result.')
    else:
        relevance_verdict = ResearchEvaluationVerdict.WEAK if any('irs.gov' in url for url in urls) and query_class is ResearchQueryClass.PROCEDURAL_ADMIN else ResearchEvaluationVerdict.MIXED
        if query_class is ResearchQueryClass.PROCEDURAL_ADMIN:
            if direct_procedural_count >= 1 and not any('irs.gov' in url for url in urls[:2]):
                relevance_verdict = ResearchEvaluationVerdict.STRONG
            elif official_count >= 1:
                relevance_verdict = ResearchEvaluationVerdict.MIXED
        elif query_class is ResearchQueryClass.MARKET_SYMBOL:
            relevance_verdict = ResearchEvaluationVerdict.STRONG if any('ethusdc' in url.lower() or 'eth/usdc' in url.lower() for url in urls) else ResearchEvaluationVerdict.MIXED
        elif query_class is ResearchQueryClass.BROAD_CONCEPT:
            relevance_verdict = ResearchEvaluationVerdict.MIXED

        uncertainty_present = '## uncertainty' in report_lower
        next_checks_present = '## next checks' in report_lower
        if not uncertainty_present:
            overclaim_risks.append('The report does not expose an explicit uncertainty section.')
        if not next_checks_present:
            missing_checks.append('Add explicit next checks for follow-up verification.')
        truthfulness_verdict = ResearchEvaluationVerdict.STRONG if uncertainty_present and next_checks_present else ResearchEvaluationVerdict.MIXED
        if query_class is ResearchQueryClass.PROCEDURAL_ADMIN and weak_count >= official_count and weak_count > 0:
            truthfulness_verdict = ResearchEvaluationVerdict.MIXED
            overclaim_risks.append('The answer may lean on community material more than procedural authority warrants.')
        if query_class is ResearchQueryClass.PROCEDURAL_ADMIN and direct_procedural_count < 1:
            if source_quality_verdict is ResearchEvaluationVerdict.STRONG:
                source_quality_verdict = ResearchEvaluationVerdict.MIXED
            if relevance_verdict is ResearchEvaluationVerdict.STRONG:
                relevance_verdict = ResearchEvaluationVerdict.MIXED
            truthfulness_verdict = ResearchEvaluationVerdict.MIXED
            overclaim_risks.append('Exact procedural details may exceed the directness of the current evidence set.')

    recommended_next_check = missing_checks[0] if missing_checks else (
        'Tighten source authority and rerun the same query for comparison.' if weak_count else 'No immediate corrective check required.'
    )
    should_revise_report = (
        source_quality_verdict is ResearchEvaluationVerdict.WEAK
        or relevance_verdict is ResearchEvaluationVerdict.WEAK
        or truthfulness_verdict is ResearchEvaluationVerdict.WEAK
    )

    return ResearchEvaluationArtifact(
        query_class=query_class,
        source_quality_verdict=source_quality_verdict,
        source_quality_reasons=tuple(dict.fromkeys(source_quality_reasons)),
        relevance_verdict=relevance_verdict,
        relevance_risks=tuple(dict.fromkeys(relevance_risks)),
        truthfulness_verdict=truthfulness_verdict,
        overclaim_risks=tuple(dict.fromkeys(overclaim_risks)),
        missing_checks=tuple(dict.fromkeys(missing_checks)),
        recommended_next_check=recommended_next_check,
        should_revise_report=should_revise_report,
    )


def _summary_line(*, query: str, findings: tuple[ExtractedFinding, ...]) -> str:
    if not findings:
        return f"No strong evidence gathered yet for: {query}."
    lead = findings[0]
    if len(findings) == 1:
        return f"Current evidence points to {lead.title} as the clearest answer path for '{query}'."
    supporting_titles = ", ".join(finding.title for finding in findings[1:3])
    return (
        f"Current evidence suggests {lead.title} is the strongest answer frame for '{query}', "
        f"supported by {supporting_titles}."
    )


def _uncertainty_lines(*, query: str, findings: tuple[ExtractedFinding, ...]) -> str:
    if not findings:
        return f"- Evidence is still too thin to answer '{query}' confidently."
    if len(findings) == 1:
        return "- The answer currently depends on a narrow evidence base and needs cross-checking."
    return (
        "- The current answer is based on a bounded set of sources and may miss contradictory material.\n"
        "- Some findings are still descriptive rather than directly decisive for the query."
    )


def _next_check_lines(*, query: str, findings: tuple[ExtractedFinding, ...]) -> str:
    if not findings:
        return f"- Gather at least two strong sources directly addressing '{query}'."
    return (
        f"- Verify the current answer against a fresh source class for '{query}'.\n"
        "- Check whether any recent source materially contradicts the top finding."
    )


def _extract_section_body(markdown: str | None, heading: str) -> str:
    if not markdown:
        return ""
    lines = markdown.splitlines()
    capture = False
    body: list[str] = []
    target = f"## {heading}".strip()
    for line in lines:
        stripped = line.strip()
        if stripped == target:
            capture = True
            continue
        if capture and stripped.startswith("## "):
            break
        if capture:
            body.append(line)
    text = " ".join(part.strip() for part in body if part.strip()).strip()
    return text



def _extract_section_lines(markdown: str | None, heading: str) -> tuple[str, ...]:
    body = _extract_section_body(markdown, heading)
    if not body:
        return ()
    parts = [part.strip(' -') for part in body.split('- ') if part.strip()]
    if len(parts) > 1:
        return tuple(part.strip() for part in parts if part.strip())
    return tuple(line.strip(' -') for line in body.splitlines() if line.strip())



def _unique_text_items(items: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized = ' '.join(item.split()).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return tuple(output)



def _project_supporting_evidence(result: ResearchResultArtifact, *, limit: int = 5) -> tuple[CompiledResearchEvidenceRef, ...]:
    refs: list[CompiledResearchEvidenceRef] = []
    seen_urls: set[str] = set()
    for finding in result.raw_findings:
        url = finding.url.strip()
        if not url or url in seen_urls:
            continue
        summary = ' '.join(finding.summary.split()).strip()
        title = finding.title.strip() or url
        if not summary:
            summary = title
        refs.append(CompiledResearchEvidenceRef(url=url, title=title, summary=summary))
        seen_urls.add(url)
        if len(refs) >= limit:
            break
    if refs:
        return tuple(refs)
    for source in result.sources:
        url = source.url.strip()
        if not url or url in seen_urls:
            continue
        title = source.title.strip() or url
        refs.append(CompiledResearchEvidenceRef(url=url, title=title, summary=title))
        seen_urls.add(url)
        if len(refs) >= limit:
            break
    if refs:
        return tuple(refs)
    key_findings = _extract_section_lines(result.result, 'Key findings')
    for index, item in enumerate(key_findings, start=1):
        summary = ' '.join(item.split()).strip()
        if not summary:
            continue
        url = f"about:report/{result.job_id}#key-findings-{index}"
        refs.append(
            CompiledResearchEvidenceRef(
                url=url,
                title=f"Report-derived key finding {index}",
                summary=summary,
            )
        )
        if len(refs) >= limit:
            return tuple(refs)
    current_answer = _extract_section_body(result.result, 'Current answer').strip()
    if current_answer and len(refs) < limit:
        refs.append(
            CompiledResearchEvidenceRef(
                url=f"about:report/{result.job_id}#current-answer",
                title="Report-derived current answer",
                summary=current_answer[:280],
            )
        )
    return tuple(refs)



def _project_source_refs(
    result: ResearchResultArtifact,
    supporting_evidence: tuple[CompiledResearchEvidenceRef, ...],
    *,
    limit: int = 8,
) -> tuple[ResearchSource, ...]:
    refs: list[ResearchSource] = []
    seen_urls: set[str] = set()
    projected_sources = result.sources
    if _query_prefers_official_supporting(result.query):
        finding_map = {}
        core_urls = {item.url for item in (result.evidence_pack.core if result.evidence_pack is not None else ())}
        supporting_urls = {item.url for item in (result.evidence_pack.supporting if result.evidence_pack is not None else ())}
        background_urls = {item.url for item in (result.evidence_pack.background if result.evidence_pack is not None else ())}
        for finding in result.raw_findings:
            official_verdict = None
            if '[llm_official_evidence:primary]' in finding.summary:
                official_verdict = 'primary'
            elif '[llm_official_evidence:supporting]' in finding.summary:
                official_verdict = 'supporting'
            elif '[llm_official_evidence:collateral]' in finding.summary:
                official_verdict = 'collateral'
            finding_map[finding.url] = type('FindingProxy', (), {'official_evidence_verdict': official_verdict})()
        def _source_projection_rank(source: ResearchSource) -> tuple[int, int, int, int, str]:
            url = source.url
            source_type = _source_type(source.url, source.title)
            verdict = getattr(finding_map.get(url, None), 'official_evidence_verdict', None)
            lowered = url.lower()
            is_pdf_like = lowered.endswith('.pdf') or '/plik/' in lowered or '/pobierz,' in lowered
            bucket = 6
            if url in core_urls and source_type == 'official_docs' and verdict != 'collateral' and not is_pdf_like:
                bucket = 0
            elif url in supporting_urls and source_type == 'official_docs' and verdict != 'collateral' and not is_pdf_like:
                bucket = 1
            elif source_type == 'official_docs' and verdict == 'primary' and not is_pdf_like:
                bucket = 2
            elif source_type == 'official_docs' and verdict != 'collateral' and not is_pdf_like:
                bucket = 3
            elif source_type == 'official_docs' and not is_pdf_like:
                bucket = 4
            elif source_type in {'docs', 'vendor_docs'}:
                bucket = 5
            pdf_penalty = 1 if is_pdf_like else 0
            background_penalty = 1 if url in background_urls else 0
            collateral_penalty = 1 if verdict == 'collateral' else 0
            primary_penalty = 0 if verdict == 'primary' else 1
            return (bucket, primary_penalty, pdf_penalty, background_penalty, collateral_penalty, source.title.lower())
        projected_sources = tuple(sorted(result.sources, key=_source_projection_rank))
    elif _classify_query(result.query) is ResearchQueryClass.PROCEDURAL_ADMIN:
        official_sources = [
            source for source in result.sources
            if _source_type(source.url, source.title) == 'official_docs'
        ]
        if official_sources:
            filtered_sources: list[ResearchSource] = []
            for source in result.sources:
                source_type = _source_type(source.url, source.title)
                if source_type in {'forum', 'video', 'snippet_repo'}:
                    continue
                if source_type in {'vendor_docs', 'blog'}:
                    continue
                filtered_sources.append(source)
            projected_sources = tuple(filtered_sources) if filtered_sources else tuple(official_sources)
    for source in projected_sources:
        url = source.url.strip()
        if not url or url in seen_urls:
            continue
        refs.append(ResearchSource(url=url, title=source.title.strip() or url, image=source.image))
        seen_urls.add(url)
        if len(refs) >= limit:
            return tuple(refs)
    for evidence in supporting_evidence:
        url = evidence.url.strip()
        if not url or url in seen_urls:
            continue
        refs.append(ResearchSource(url=url, title=evidence.title.strip() or url))
        seen_urls.add(url)
        if len(refs) >= limit:
            return tuple(refs)
    fallback_title = result.query.strip() or 'Compiled research artifact source'
    if not refs:
        refs.append(ResearchSource(url=f"about:compiled/{result.job_id}", title=fallback_title))
    return tuple(refs)



def _project_claims(
    result: ResearchResultArtifact,
    supporting_evidence: tuple[CompiledResearchEvidenceRef, ...],
    *,
    limit: int = 4,
) -> tuple[CompiledResearchClaim, ...]:
    claims: list[CompiledResearchClaim] = []
    seen_texts: set[str] = set()
    evidence_by_url = {ref.url: ref for ref in supporting_evidence}
    for finding in result.raw_findings:
        text = ' '.join(finding.summary.split()).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen_texts:
            continue
        seen_texts.add(key)
        evidence_refs = (finding.url,) if finding.url in evidence_by_url else ()
        claims.append(CompiledResearchClaim(text=text, evidence_refs=evidence_refs))
        if len(claims) >= limit:
            break
    if claims:
        return tuple(claims)
    current_answer = _extract_section_body(result.result, 'Current answer').strip()
    if current_answer:
        return (CompiledResearchClaim(text=current_answer[:280], evidence_refs=tuple(ref.url for ref in supporting_evidence[:1])),)
    return ()



def _project_followup(result: ResearchResultArtifact) -> tuple[tuple[str, ...], tuple[str, ...]]:
    open_questions = list(result.evaluation.missing_checks if result.evaluation is not None else ())
    open_questions.extend(_extract_section_lines(result.result, 'Uncertainty'))
    next_checks = list(_extract_section_lines(result.result, 'Next checks'))
    if result.evaluation is not None and result.evaluation.recommended_next_check:
        next_checks.append(result.evaluation.recommended_next_check)
    return _unique_text_items(open_questions), _unique_text_items(next_checks)



def _compiled_artifact_projection_diagnostics(result: ResearchResultArtifact) -> dict[str, object]:
    return {
        'job_id': result.job_id,
        'raw_findings_count': len(result.raw_findings),
        'sources_count': len(result.sources),
        'result_excerpt': result.result[:240],
        'raw_report_excerpt': result.raw_report[:240],
        'current_answer': _extract_section_body(result.result, 'Current answer'),
        'key_findings': _extract_section_lines(result.result, 'Key findings'),
        'next_checks': _extract_section_lines(result.result, 'Next checks'),
    }



def _compile_research_artifact(result: ResearchResultArtifact) -> CompiledResearchArtifact:
    query_class = result.evaluation.query_class if result.evaluation is not None else _classify_query(result.query)
    current_answer = _extract_section_body(result.result, 'Current answer') or result.result[:400]
    summary = current_answer[:320].strip()
    supporting_evidence = _project_supporting_evidence(result)
    source_refs = _project_source_refs(result, supporting_evidence)
    key_claims = _project_claims(result, supporting_evidence)
    open_questions, next_checks = _project_followup(result)
    title = _generate_short_report_title(query=result.query, findings=tuple(ExtractedFinding(url=f.url, title=f.title, summary=f.summary) for f in result.raw_findings))
    return CompiledResearchArtifact(
        artifact_id=f"cra-{result.job_id}",
        source_job_id=result.job_id,
        owner_id=result.owner_id,
        query=result.query,
        query_class=query_class,
        title=title,
        summary=summary,
        current_answer=current_answer,
        key_claims=key_claims,
        supporting_evidence=supporting_evidence,
        open_questions=open_questions,
        next_checks=next_checks,
        source_refs=source_refs,
        planning_analysis_snapshot=result.planning_analysis,
        problem_analysis_snapshot=result.problem_analysis,
        execution_plan_snapshot=result.execution_plan,
        reflection_snapshot=result.reflection,
        evaluation_snapshot=result.evaluation,
        created_at=result.completed_at or result.created_at,
    )



def _lint_compiled_research_artifact(artifact: CompiledResearchArtifact) -> CompiledResearchArtifactLint:
    missing_sections: list[str] = []
    risk_flags: list[str] = []
    recommended_repairs: list[str] = []

    if not artifact.title.strip():
        missing_sections.append('title')
        risk_flags.append('missing_title')
    if not artifact.summary.strip():
        missing_sections.append('summary')
        risk_flags.append('missing_summary')
    if not artifact.current_answer.strip():
        missing_sections.append('current_answer')
        risk_flags.append('missing_current_answer')
    if not artifact.key_claims and not artifact.supporting_evidence:
        missing_sections.append('evidence')
        risk_flags.append('missing_evidence')
    if not artifact.source_refs:
        missing_sections.append('source_refs')
        risk_flags.append('missing_sources')
    if artifact.evaluation_snapshot is None:
        missing_sections.append('evaluation_snapshot')
        risk_flags.append('missing_evaluation_snapshot')
    if artifact.execution_plan_snapshot is None:
        missing_sections.append('execution_plan_snapshot')
        risk_flags.append('missing_execution_plan_snapshot')
    if artifact.reflection_snapshot is None:
        missing_sections.append('reflection_snapshot')
        risk_flags.append('missing_reflection_snapshot')

    completeness_verdict = ResearchEvaluationVerdict.STRONG
    if len(missing_sections) >= 2:
        completeness_verdict = ResearchEvaluationVerdict.WEAK
    elif missing_sections:
        completeness_verdict = ResearchEvaluationVerdict.MIXED

    evidence_verdict = ResearchEvaluationVerdict.STRONG
    if not artifact.supporting_evidence:
        risk_flags.append('missing_evidence') if 'missing_evidence' not in risk_flags else None
        recommended_repairs.append('Add at least one supporting evidence reference.')
        evidence_verdict = ResearchEvaluationVerdict.MIXED
    if not artifact.source_refs:
        recommended_repairs.append('Attach source references to the compiled artifact.')
        evidence_verdict = ResearchEvaluationVerdict.WEAK if evidence_verdict is ResearchEvaluationVerdict.MIXED else ResearchEvaluationVerdict.MIXED
    if artifact.evaluation_snapshot is not None:
        if artifact.evaluation_snapshot.source_quality_verdict is ResearchEvaluationVerdict.WEAK:
            risk_flags.append('weak_source_quality')
            evidence_verdict = ResearchEvaluationVerdict.WEAK
        elif artifact.evaluation_snapshot.source_quality_verdict is ResearchEvaluationVerdict.MIXED and evidence_verdict is ResearchEvaluationVerdict.STRONG:
            evidence_verdict = ResearchEvaluationVerdict.MIXED
        if artifact.evaluation_snapshot.truthfulness_verdict is ResearchEvaluationVerdict.WEAK:
            risk_flags.append('weak_truthfulness')
            evidence_verdict = ResearchEvaluationVerdict.WEAK
        if artifact.evaluation_snapshot.should_revise_report:
            risk_flags.append('needs_revision')
            recommended_repairs.append('Review and tighten the compiled artifact against evaluator findings.')
            if evidence_verdict is ResearchEvaluationVerdict.STRONG:
                evidence_verdict = ResearchEvaluationVerdict.MIXED

    followup_verdict = ResearchEvaluationVerdict.STRONG
    if artifact.open_questions and not artifact.next_checks:
        risk_flags.append('open_questions_without_next_checks')
        recommended_repairs.append('Add next checks for the open questions.')
        followup_verdict = ResearchEvaluationVerdict.WEAK
    elif not artifact.open_questions and not artifact.next_checks:
        followup_verdict = ResearchEvaluationVerdict.WEAK
        recommended_repairs.append('Add at least one next check or open question.')
    elif not artifact.open_questions or not artifact.next_checks:
        followup_verdict = ResearchEvaluationVerdict.MIXED

    if artifact.execution_plan_snapshot is None:
        missing_sections.append('execution_plan_snapshot')
        recommended_repairs.append('Attach an execution plan snapshot to the compiled artifact.')
        completeness_verdict = ResearchEvaluationVerdict.WEAK
    elif len(artifact.execution_plan_snapshot.steps) < 2:
        risk_flags.append('shallow_execution_plan_snapshot')
        recommended_repairs.append('Expand the execution plan snapshot to include at least two meaningful steps.')
        if completeness_verdict is ResearchEvaluationVerdict.STRONG:
            completeness_verdict = ResearchEvaluationVerdict.MIXED

    if artifact.reflection_snapshot is not None:
        if artifact.reflection_snapshot.should_follow_up and not artifact.next_checks:
            risk_flags.append('reflection_followup_without_next_checks')
            recommended_repairs.append('Add next checks that answer the reflection follow-up recommendation.')
            followup_verdict = ResearchEvaluationVerdict.WEAK
        if artifact.reflection_snapshot.goal_coverage == 'weak' and not artifact.reflection_snapshot.recommended_follow_up:
            risk_flags.append('weak_reflection_without_guidance')
            recommended_repairs.append('Add one explicit follow-up recommendation for weak reflection coverage.')
            if followup_verdict is ResearchEvaluationVerdict.STRONG:
                followup_verdict = ResearchEvaluationVerdict.MIXED
        if 'no_core_evidence' in artifact.reflection_snapshot.weak_evidence_areas:
            risk_flags.append('thin_evidence_base')
            recommended_repairs.append('Gather stronger evidence before treating the artifact as decision-ready.')
            evidence_verdict = ResearchEvaluationVerdict.WEAK

    if artifact.key_claims and not artifact.supporting_evidence:
        risk_flags.append('claims_without_supporting_evidence')
        recommended_repairs.append('Attach supporting evidence refs or reduce unsupported claim emphasis.')
        evidence_verdict = ResearchEvaluationVerdict.WEAK

    if artifact.evaluation_snapshot is not None and artifact.reflection_snapshot is not None:
        if (
            artifact.reflection_snapshot.goal_coverage == 'weak'
            and artifact.evaluation_snapshot.should_revise_report is False
            and not artifact.next_checks
        ):
            risk_flags.append('reflection_evaluation_mismatch')
            recommended_repairs.append('Align artifact follow-up guidance with weak reflection coverage.')
            followup_verdict = ResearchEvaluationVerdict.WEAK

    status = CompiledResearchArtifactLintStatus.HEALTHY
    if (
        completeness_verdict is ResearchEvaluationVerdict.WEAK
        or evidence_verdict is ResearchEvaluationVerdict.WEAK
        or followup_verdict is ResearchEvaluationVerdict.WEAK
    ):
        status = CompiledResearchArtifactLintStatus.WEAK
    elif (
        completeness_verdict is ResearchEvaluationVerdict.MIXED
        or evidence_verdict is ResearchEvaluationVerdict.MIXED
        or followup_verdict is ResearchEvaluationVerdict.MIXED
        or risk_flags
    ):
        status = CompiledResearchArtifactLintStatus.NEEDS_REVIEW

    recommended_next_action = 'artifact_ready'
    if status is CompiledResearchArtifactLintStatus.WEAK:
        recommended_next_action = 'revise_artifact'
    elif status is CompiledResearchArtifactLintStatus.NEEDS_REVIEW:
        recommended_next_action = 'review_artifact'

    return CompiledResearchArtifactLint(
        lint_id=f"crl-{artifact.artifact_id}",
        artifact_id=artifact.artifact_id,
        owner_id=artifact.owner_id,
        status=status,
        completeness_verdict=completeness_verdict,
        evidence_verdict=evidence_verdict,
        followup_verdict=followup_verdict,
        risk_flags=tuple(dict.fromkeys(risk_flags)),
        missing_sections=tuple(dict.fromkeys(missing_sections)),
        recommended_repairs=tuple(dict.fromkeys(recommended_repairs)),
        recommended_next_action=recommended_next_action,
        created_at=artifact.created_at,
    )


class DeterministicStopRails:
    """Bounded stop-rail evaluator for the first engine-loop slice."""

    def __init__(
        self,
        *,
        min_rounds: int = 2,
        max_rounds: int = 6,
        max_urls_total: int = 8,
        max_consecutive_empty_rounds: int = 2,
    ) -> None:
        self.min_rounds = min_rounds
        self.max_rounds = max_rounds
        self.max_urls_total = max_urls_total
        self.max_consecutive_empty_rounds = max_consecutive_empty_rounds

    def should_stop(
        self,
        *,
        round_number: int,
        total_urls: int,
        consecutive_empty_rounds: int,
        llm_says_continue: bool,
    ) -> bool:
        if round_number >= self.max_rounds:
            return True
        if total_urls >= self.max_urls_total:
            return True
        if consecutive_empty_rounds >= self.max_consecutive_empty_rounds:
            return True
        if round_number < self.min_rounds:
            return False
        return not llm_says_continue


class ResearchJobManager:
    """Small in-process lifecycle manager for the Deep Research slice."""

    def __init__(self, persistence: ResearchPersistence, *, planning_analyzer: ResearchPlanningAnalyzer | None = None) -> None:
        self.persistence = persistence
        self.planning_analyzer = planning_analyzer or DeterministicPlanningAnalyzer()

    def start_job(self, request: ResearchJobStartRequest) -> ResearchJobStartOutcome:
        now = _utcnow()
        planning_analysis = self.planning_analyzer(request.query)
        problem_analysis = _planning_analysis_to_problem_analysis(planning_analysis)
        execution_plan = StubResearchPlanner()(
            request.query,
            problem_analysis=problem_analysis,
            planning_analysis=planning_analysis,
        )
        job = ResearchJob(
            job_id=f"rj-{uuid4().hex[:12]}",
            owner_id=request.owner_id,
            query=request.query,
            status=ResearchJobStatus.QUEUED,
            created_at=now,
            settings=request.settings,
            planning_analysis=planning_analysis,
            problem_analysis=problem_analysis,
            execution_plan=execution_plan,
        )
        self.persistence.jobs.save_job(job)
        return ResearchJobStartOutcome(request=request, job=job)

    def get_job_status(self, job_id: str) -> ResearchJobStatusOutcome | None:
        job = self.persistence.jobs.get_job(job_id)
        if job is None:
            return None
        return ResearchJobStatusOutcome(job=job, progress=self.persistence.progress.list_events(job_id))

    def cancel_job(self, job_id: str) -> ResearchJob | None:
        job = self.persistence.jobs.get_job(job_id)
        if job is None:
            return None
        if job.status in {ResearchJobStatus.DONE, ResearchJobStatus.ERROR, ResearchJobStatus.CANCELLED}:
            return job
        cancelled = replace(job, status=ResearchJobStatus.CANCELLED, completed_at=_utcnow())
        self.persistence.jobs.save_job(cancelled)
        self.persistence.progress.append_event(
            ResearchProgressEvent(
                job_id=job_id,
                status=ResearchJobStatus.CANCELLED,
                phase=ResearchPhase.WARNING,
                message="Research job cancelled.",
                final=True,
            )
        )
        return cancelled

    def get_job_result(self, job_id: str) -> ResearchJobResultOutcome | None:
        job = self.persistence.jobs.get_job(job_id)
        if job is None:
            return None
        return ResearchJobResultOutcome(job=job, result=self.persistence.results.get_result(job_id))

    def list_jobs(self, owner_id: str) -> ResearchJobListOutcome:
        return ResearchJobListOutcome(owner_id=owner_id, jobs=self.persistence.jobs.list_jobs_for_owner(owner_id))


class FakeResearchWorker:
    """Deterministic worker with a bounded iterative engine loop."""

    def __init__(
        self,
        persistence: ResearchPersistence,
        *,
        planner: ResearchPlanner | None = None,
        query_generator: ResearchQueryGenerator | None = None,
        llm_query_generator: LlmQueryGenerator | None = None,
        search: ResearchSearchAdapter | None = None,
        extract: ResearchExtractor | None = None,
        synthesize: ResearchSynthesizer | None = None,
        pdf_ingest: ResearchPdfIngestor | None = None,
        stop_rails: DeterministicStopRails | None = None,
        relevance_judge: "LlmSearchRelevanceJudge | None" = None,
        subject_sheet_builder: "LlmSubjectSheetBuilder | None" = None,
        official_subject_precision_judge: "LlmOfficialSubjectPrecisionJudge | None" = None,
        official_evidence_judge: "LlmOfficialEvidenceJudge | None" = None,
        official_evidence_family_judge: "LlmOfficialEvidenceFamilyJudge | None" = None,
        official_html_content_enricher: "OfficialHtmlContentEnricher | None" = None,
    ) -> None:
        self.persistence = persistence
        self.planner = planner or StubResearchPlanner()
        self.planning_analyzer = DeterministicPlanningAnalyzer()
        self.query_generator = query_generator or StubQueryGenerator()
        self.llm_query_generator = llm_query_generator
        self.search = search or build_search_adapter()
        self.extract = extract or StubExtractor()
        self.synthesize = synthesize or StubSynthesizer()
        self.pdf_ingest = pdf_ingest
        self.stop_rails = stop_rails or DeterministicStopRails()
        self.relevance_judge = relevance_judge
        self.subject_sheet_builder = subject_sheet_builder
        self.official_subject_precision_judge = official_subject_precision_judge
        self.official_evidence_judge = official_evidence_judge
        self.official_evidence_family_judge = official_evidence_family_judge
        self.official_html_content_enricher = official_html_content_enricher

    def __call__(self, job_id: str) -> ResearchResultArtifact | None:
        started_at_monotonic = perf_counter()
        job = self.persistence.jobs.get_job(job_id)
        if job is None:
            return None
        if job.status == ResearchJobStatus.CANCELLED:
            return self.persistence.results.get_result(job_id)
        if job.status == ResearchJobStatus.DONE:
            return self.persistence.results.get_result(job_id)

        started = replace(job, status=ResearchJobStatus.PROBING, started_at=_utcnow())
        self.persistence.jobs.save_job(started)
        _emit_progress(self.persistence, job_id, ResearchJobStatus.PROBING, ResearchPhase.PROBING, message="Probing runtime configuration.")

        running = replace(started, status=ResearchJobStatus.RUNNING)
        self.persistence.jobs.save_job(running)

        planning_analysis = running.planning_analysis or self.planning_analyzer(running.query)
        problem_analysis = running.problem_analysis or _planning_analysis_to_problem_analysis(planning_analysis)
        plan = self.planner(
            running.query,
            problem_analysis=problem_analysis,
            planning_analysis=planning_analysis,
        )
        subject_sheet = self.subject_sheet_builder(query=running.query, planning_analysis=planning_analysis) if self.subject_sheet_builder is not None else _fallback_subject_sheet(query=running.query, planning_analysis=planning_analysis)
        running = replace(running, planning_analysis=planning_analysis, problem_analysis=problem_analysis, execution_plan=plan)
        self.persistence.jobs.save_job(running)
        _emit_progress(self.persistence, job_id, ResearchJobStatus.RUNNING, ResearchPhase.PLANNING, round=1, message=f"Planning around {len(plan.steps)} step(s) with strategy {plan.strategy.value}.")

        round_number = 0
        executed_query_count = 0
        total_urls = 0
        consecutive_empty_rounds = 0
        executed_provider_names: list[str] = []
        all_hits: list[SearchHit] = []
        all_findings: list[ExtractedFinding] = []
        evolving_report: str | None = None
        pre_extraction_seen = 0
        pre_extraction_kept = 0
        pre_extraction_dropped = 0
        authority_policy_applied = False
        authority_filter_fallback_used = False
        dropped_source_types_seen: list[str] = []
        packed_core_count = 0
        packed_supporting_count = 0
        packed_background_count = 0
        evidence_pack: ResearchEvidencePack | None = None
        branch_proposals: ResearchBranchProposalSet | None = _derive_branch_proposals(
            problem_analysis=running.problem_analysis,
            execution_plan=running.execution_plan,
        )
        branch_evaluation: ResearchBranchEvaluation | None = None
        reflection: ResearchReflection | None = None

        while True:
            round_number += 1
            current = self.persistence.jobs.get_job(job_id)
            if current is not None and current.status == ResearchJobStatus.CANCELLED:
                return self.persistence.results.get_result(job_id)

            queries = _generate_queries(
                self.query_generator,
                plan,
                round_number=round_number,
                planning_analysis=planning_analysis,
            )
            provider_names = _resolve_search_provider_names(self.search, configured_provider=None)
            query_path_trace = _query_generation_trace(
                plan=plan,
                planning_analysis=planning_analysis,
                round_number=round_number,
            )
            _emit_progress(self.persistence, 
                job_id,
                ResearchJobStatus.RUNNING,
                ResearchPhase.SEARCHING,
                round=round_number,
                queries=len(queries),
                query_preview=queries[0] if queries else None,
                query_list=tuple(queries),
                providers_attempted=provider_names,
                message=f"Running {len(queries)} search querie(s).",
                details={
                    'stage': 'query_generation',
                    'queries': list(queries),
                    'providers_attempted': list(provider_names),
                    'query_path_trace': query_path_trace,
                },
            )
            executed_query_count += len(queries)
            try:
                hits = self.search(queries, round_number=round_number)
                executed_provider_names.extend(_actual_search_provider_names(self.search))
            except ResearchSearchError as exc:
                executed_provider_names.extend(_actual_search_provider_names(self.search))
                _emit_progress(self.persistence, 
                    job_id,
                    ResearchJobStatus.RUNNING,
                    ResearchPhase.WARNING,
                    round=round_number,
                    total_sources=len(all_hits),
                    total_findings=len(all_findings),
                    message=str(exc),
                )
                if evolving_report or all_findings:
                    return self.save_partial_result(
                        job_id,
                        mode=ResearchCompletionMode.PARTIAL_ERROR,
                        duration_seconds=max(0, int(perf_counter() - started_at_monotonic)),
                        rounds=round_number,
                        queries=executed_query_count,
                        urls=len(all_hits),
                        search_providers=tuple(dict.fromkeys(executed_provider_names)),
                        pre_extraction_sources_seen=pre_extraction_seen,
                        pre_extraction_sources_kept=pre_extraction_kept,
                        pre_extraction_sources_dropped=pre_extraction_dropped,
                        authority_policy_applied=authority_policy_applied,
                        authority_filter_fallback_used=authority_filter_fallback_used,
                        dropped_source_types=tuple(sorted(set(dropped_source_types_seen))),
                        packed_core_count=packed_core_count,
                        packed_supporting_count=packed_supporting_count,
                        packed_background_count=packed_background_count,
                    )
                _emit_progress(self.persistence, 
                    job_id,
                    ResearchJobStatus.ERROR,
                    ResearchPhase.ERROR,
                    round=round_number,
                    message=(
                        "Search is unavailable: unified search returned no usable official evidence and the fallback search path did not return usable results."
                        if _procedural_query_bias(running.query)
                        else "Search is unavailable: neither unified web search nor the fallback search path returned usable results for this query."
                    ),
                    final=True,
                )
                errored = replace(
                    running,
                    status=ResearchJobStatus.ERROR,
                    completed_at=_utcnow(),
                    error=(
                        "Search is unavailable: unified search returned no usable official evidence and the fallback search path did not return usable results."
                        if _procedural_query_bias(running.query)
                        else "Search is unavailable: neither unified web search nor the fallback search path returned usable results for this query."
                    ),
                )
                self.persistence.jobs.save_job(errored)
                return None
            provider_candidates = _provider_candidate_diagnostics(hits=hits, query=running.query, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
            unified_raw_hits = getattr(self.search, 'last_unified_hits', ()) if self.search is not None else ()
            unified_official_enough = getattr(self.search, 'last_unified_official_enough', None) if self.search is not None else None
            rejection_details = _search_rejection_details(query=running.query, existing_hits=all_hits, candidate_hits=hits, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
            rejection_summary = _search_rejection_summary(query=running.query, existing_hits=all_hits, candidate_hits=hits, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
            new_hits = _dedupe_hits(all_hits, hits, query=running.query, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
            all_hits.extend(new_hits)
            total_urls = len(all_hits)
            _emit_progress(self.persistence, 
                job_id,
                ResearchJobStatus.RUNNING,
                ResearchPhase.WARNING,
                round=round_number,
                queries=len(queries),
                total_sources=total_urls,
                new_sources=len(new_hits),
                message=f"Search narrowing: raw_hits={len(hits)}, {rejection_summary}",
                details={
                    'stage': 'search_dedupe',
                    'raw_hits': len(hits),
                    'accepted_new_hits': len(new_hits),
                    'provider_candidates': provider_candidates,
                    'unified_raw_candidates': _provider_candidate_diagnostics(hits=tuple(unified_raw_hits), query=running.query, subject_sheet=subject_sheet, planning_analysis=planning_analysis),
                    'unified_official_enough': unified_official_enough,
                    'search_rejection': rejection_details,
                },
            )
            if new_hits:
                consecutive_empty_rounds = 0
            else:
                consecutive_empty_rounds += 1
                if len(all_hits) == 0 and round_number == 1 and not _procedural_query_bias(running.query) and self.llm_query_generator is not None:
                    refined_queries = self.llm_query_generator(running.query)
                    if refined_queries:
                        _emit_progress(self.persistence, 
                            job_id,
                            ResearchJobStatus.RUNNING,
                            ResearchPhase.SEARCHING,
                            round=round_number,
                            queries=len(refined_queries),
                            query_preview=refined_queries[0],
                            query_list=tuple(refined_queries),
                            providers_attempted=_resolve_search_provider_names(self.search, configured_provider=None),
                            message="No usable hits from the original query. Retrying search with LLM-refined queries.",
                        )
                        executed_query_count += len(refined_queries)
                        retry_hits = self.search(tuple(refined_queries), round_number=round_number)
                        executed_provider_names.extend(_actual_search_provider_names(self.search))
                        retry_summary = _search_rejection_summary(query=running.query, existing_hits=all_hits, candidate_hits=retry_hits, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
                        retry_new_hits = _dedupe_hits(all_hits, retry_hits, query=running.query, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
                        all_hits.extend(retry_new_hits)
                        total_urls = len(all_hits)
                        _emit_progress(self.persistence, 
                            job_id,
                            ResearchJobStatus.RUNNING,
                            ResearchPhase.WARNING,
                            round=round_number,
                            queries=len(refined_queries),
                            total_sources=total_urls,
                            new_sources=len(retry_new_hits),
                            message=f"Search narrowing after retry: raw_hits={len(retry_hits)}, {retry_summary}",
                        )
                        if retry_new_hits:
                            consecutive_empty_rounds = 0
                            new_hits = retry_new_hits
                        else:
                            _emit_progress(self.persistence, 
                                job_id,
                                ResearchJobStatus.ERROR,
                                ResearchPhase.ERROR,
                                round=round_number,
                                message="Search is unavailable: neither the original query nor the LLM-refined web queries returned usable results.",
                                final=True,
                            )
                            errored = replace(
                                running,
                                status=ResearchJobStatus.ERROR,
                                completed_at=_utcnow(),
                                error="Search is unavailable: neither the original query nor the LLM-refined web queries returned usable results.",
                            )
                            self.persistence.jobs.save_job(errored)
                            return None
                    else:
                        _emit_progress(self.persistence, 
                            job_id,
                            ResearchJobStatus.ERROR,
                            ResearchPhase.ERROR,
                            round=round_number,
                            message="Search is unavailable: the original query returned no usable results and LLM query refinement produced no retry queries.",
                            final=True,
                        )
                        errored = replace(
                            running,
                            status=ResearchJobStatus.ERROR,
                            completed_at=_utcnow(),
                            error="Search is unavailable: the original query returned no usable results and LLM query refinement produced no retry queries.",
                        )
                        self.persistence.jobs.save_job(errored)
                        return None
                elif len(all_hits) == 0 and round_number == 1:
                    _emit_progress(self.persistence, 
                        job_id,
                        ResearchJobStatus.ERROR,
                        ResearchPhase.ERROR,
                        round=round_number,
                        message=(
                            "Search is unavailable: unified search returned no usable official evidence and the fallback search path did not return usable results."
                            if _procedural_query_bias(running.query)
                            else "Search is unavailable: neither unified web search nor the fallback search path returned usable results for this query."
                        ),
                        final=True,
                    )
                    errored = replace(
                        running,
                        status=ResearchJobStatus.ERROR,
                        completed_at=_utcnow(),
                        error=(
                            "Search is unavailable: unified search returned no usable official evidence and the fallback search path did not return usable results."
                            if _procedural_query_bias(running.query)
                            else "Search is unavailable: neither unified web search nor the fallback search path returned usable results for this query."
                        ),
                    )
                    self.persistence.jobs.save_job(errored)
                    return None

            filter_analysis = _filter_hits_for_extraction_with_diagnostics(query=running.query, hits=tuple(new_hits), relevance_judge=self.relevance_judge, official_evidence_judge=self.official_evidence_judge if hasattr(self, 'official_evidence_judge') else None, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
            filter_diag_map = {item['url']: item for item in filter_analysis.get('diagnostics', [])}
            filter_outcome = filter_analysis['outcome']
            filtered_hits = list(filter_outcome.kept_hits)
            subject_precision_trace: list[dict[str, object]] = []
            judge_activation_trace = {
                'judge_present': self.official_subject_precision_judge is not None,
                'filtered_hit_count': len(filtered_hits),
                'official_candidate_count': sum(1 for hit in filtered_hits if _source_type(hit.url, hit.title) == 'official_docs'),
                'candidate_source_types': [
                    {
                        'url': hit.url,
                        'title': hit.title,
                        'source_type': _source_type(hit.url, hit.title),
                    }
                    for hit in filtered_hits[:12]
                ],
                'worker_class': self.__class__.__name__,
                'module_file': __file__,
            }
            if self.official_subject_precision_judge is not None and filtered_hits:
                promoted_hits: list[SearchHit] = []
                untouched_hits: list[SearchHit] = []
                demoted_hits: list[SearchHit] = []
                for hit in filtered_hits:
                    source_type = _source_type(hit.url, hit.title)
                    if source_type != 'official_docs':
                        untouched_hits.append(hit)
                        continue
                    match, confidence, reason = self.official_subject_precision_judge.judge_hit(
                        query=running.query,
                        hit=hit,
                        subject_sheet=subject_sheet,
                    )
                    llm_official_prefix = ''
                    if filter_diag_map.get(hit.url, {}).get('llm_official_evidence_verdict'):
                        llm_verdict = filter_diag_map[hit.url]['llm_official_evidence_verdict']
                        llm_conf = float(filter_diag_map[hit.url].get('llm_official_evidence_confidence') or 0.0)
                        llm_official_prefix = f"[llm_official_evidence:{llm_verdict}] llm_official_confidence={llm_conf:.2f}; "
                    tagged_hit = SearchHit(
                        url=hit.url,
                        title=hit.title,
                        snippet=f"{llm_official_prefix}[official_subject:{match}] [priority_band:{'exact_subject_winner' if match == 'exact_subject' else 'official_related' if match == 'related_but_broad' else 'off_topic'}] confidence={confidence:.2f}; reason={reason} — {hit.snippet}",
                    )
                    subject_precision_trace.append({
                        'url': hit.url,
                        'title': hit.title,
                        'source_type': source_type,
                        'match': match,
                        'confidence': round(confidence, 4),
                        'reason': reason,
                    })
                    if match == 'exact_subject':
                        promoted_hits.append(tagged_hit)
                    elif match == 'off_topic':
                        demoted_hits.append(tagged_hit)
                    else:
                        untouched_hits.append(tagged_hit)
                filtered_hits = [*promoted_hits, *untouched_hits, *demoted_hits]
            if not filtered_hits and new_hits:
                filtered_hits = list(new_hits)
            pre_extraction_seen += filter_outcome.seen_count
            pre_extraction_kept += filter_outcome.kept_count
            pre_extraction_dropped += filter_outcome.dropped_count
            authority_policy_applied = authority_policy_applied or filter_outcome.authority_policy_applied
            authority_filter_fallback_used = authority_filter_fallback_used or filter_outcome.fallback_used
            dropped_source_types_seen.extend(filter_outcome.dropped_source_types)

            _emit_progress(self.persistence, 
                job_id,
                ResearchJobStatus.RUNNING,
                ResearchPhase.READING,
                round=round_number,
                total_sources=total_urls,
                new_sources=len(filtered_hits),
                url=filtered_hits[0].url if filtered_hits else (new_hits[0].url if new_hits else None),
                title=filtered_hits[0].title if filtered_hits else (new_hits[0].title if new_hits else None),
                message=f"Normalized {len(new_hits)} new source(s); kept {len(filtered_hits)} after authority filtering.",
                details={
                    'stage': 'pre_extraction_filter',
                    'seen': len(new_hits),
                    'kept': len(filtered_hits),
                    'dropped': max(0, len(new_hits) - len(filtered_hits)),
                    'fallback_used': filter_outcome.fallback_used,
                    'authority_policy_applied': filter_outcome.authority_policy_applied,
                    'diagnostics': filter_analysis['diagnostics'],
                    'kept_urls': filter_analysis['kept_urls'],
                    'dropped_urls': filter_analysis['dropped_urls'],
                    'subject_precision_trace': subject_precision_trace,
                    'judge_activation_trace': judge_activation_trace,
                    'trace_schema_version': 'judge_activation_v1',
                },
            )

            extractor = self.extract
            if isinstance(extractor, StubExtractor):
                extractor = StubExtractor(query=running.query)
            findings = extractor(tuple(filtered_hits))
            findings = _lift_exact_subject_official_findings(
                query=running.query,
                findings=findings,
            )
            if self.official_html_content_enricher is not None:
                findings = tuple(
                    self.official_html_content_enricher.enrich(query=running.query, finding=finding)
                    if '[official_subject:exact_subject]' in finding.summary and _source_type(finding.url, finding.title) == 'official_docs' and not _looks_like_pdf_artifact(SearchHit(url=finding.url, title=finding.title, snippet=finding.summary))
                    else finding
                    for finding in findings
                )
            if self.pdf_ingest is not None:
                enriched_findings: list[ExtractedFinding] = []
                for finding in findings:
                    if finding.pdf_triage_verdict not in {'relevant', 'uncertain'}:
                        enriched_findings.append(finding)
                        continue
                    if _source_type(finding.url, finding.title) != 'official_docs':
                        enriched_findings.append(finding)
                        continue
                    triage_verdict = finding.pdf_triage_verdict or 'uncertain'
                    ingest_result = self.pdf_ingest(
                        query=running.query,
                        url=finding.url,
                        title=finding.title,
                        triage_verdict=triage_verdict,
                    )
                    if not ingest_result.relevant:
                        enriched_findings.append(
                            replace(
                                finding,
                                pdf_triage_verdict='irrelevant',
                                pdf_triage_notes='pdf_ingest_rejected',
                                summary=f"[official_pdf_ingest:irrelevant] {_pdf_ingest_summary(ingest_result)}",
                            )
                        )
                        continue
                    enriched_findings.append(
                        replace(
                            finding,
                            pdf_triage_notes='pdf_ingest_verified',
                            summary=f"[official_pdf_ingest:verified] {_pdf_ingest_summary(ingest_result)}",
                        )
                    )
                findings = tuple(enriched_findings)
            all_findings.extend(findings)
            _emit_progress(self.persistence, 
                job_id,
                ResearchJobStatus.RUNNING,
                ResearchPhase.ANALYZING,
                round=round_number,
                total_sources=total_urls,
                total_findings=len(all_findings),
                message=f"Extracted {len(findings)} finding(s) this round.",
                details={
                    'stage': 'extraction',
                    'input_urls': [hit.url for hit in filtered_hits],
                    'findings': [_finding_trace_payload(finding) for finding in findings],
                },
            )

            cumulative_findings = tuple(all_findings)
            family_trace: list[dict[str, object]] = []
            family_activation_trace = {
                'family_judge_present': getattr(self, 'official_evidence_family_judge', None) is not None,
                'worker_class': self.__class__.__name__,
                'module_file': __file__,
            }
            ranked_for_pack = _top_findings(cumulative_findings, limit=max(6, len(cumulative_findings)), query=running.query, family_judge=getattr(self, 'official_evidence_family_judge', None), family_trace_sink=family_trace, family_activation_trace_sink=family_activation_trace)
            packed = _pack_evidence_for_synthesis(query=running.query, findings=ranked_for_pack)
            evidence_pack = _to_research_evidence_pack(query=running.query, packed=packed)
            packed_core_count = len(packed.core)
            packed_supporting_count = len(packed.supporting)
            packed_background_count = len(packed.background)
            _emit_progress(self.persistence, 
                job_id,
                ResearchJobStatus.RUNNING,
                ResearchPhase.ANALYZING,
                round=round_number,
                total_sources=total_urls,
                total_findings=len(all_findings),
                message='Packed evidence for synthesis.',
                details={
                    'stage': 'evidence_pack',
                    'family_activation_trace': family_activation_trace,
                    'official_family_trace': family_trace,
                    'core': [_finding_trace_payload(item, bucket='core') for item in packed.core],
                    'supporting': [_finding_trace_payload(item, bucket='supporting') for item in packed.supporting],
                    'background': [_finding_trace_payload(item, bucket='background') for item in packed.background],
                },
            )
            branch_evaluation = _evaluate_branch_proposals(
                problem_analysis=running.problem_analysis,
                execution_plan=running.execution_plan,
                evidence_pack=evidence_pack,
                branch_proposals=branch_proposals,
            )
            synthesis = self.synthesize(
                query=running.query,
                round_number=round_number,
                findings=findings,
                previous_report=evolving_report,
            )
            evolving_report = synthesis.report_markdown
            _emit_progress(self.persistence, 
                job_id,
                ResearchJobStatus.RUNNING,
                ResearchPhase.WRITING,
                round=round_number,
                total_sources=total_urls,
                total_findings=len(all_findings),
                message=synthesis.answer_summary,
            )

            if self.stop_rails.should_stop(
                round_number=round_number,
                total_urls=total_urls,
                consecutive_empty_rounds=consecutive_empty_rounds,
                llm_says_continue=synthesis.should_continue,
            ):
                break

        completed_at = _utcnow()
        stats = ResearchStats(
            duration_seconds=max(0, int(perf_counter() - started_at_monotonic)),
            rounds=round_number,
            queries=executed_query_count,
            urls=len(all_hits),
            model=running.settings.model,
            search_providers=tuple(dict.fromkeys(executed_provider_names)),
            pre_extraction_sources_seen=pre_extraction_seen,
            pre_extraction_sources_kept=pre_extraction_kept,
            pre_extraction_sources_dropped=pre_extraction_dropped,
            authority_policy_applied=authority_policy_applied,
            authority_filter_fallback_used=authority_filter_fallback_used,
            dropped_source_types=tuple(sorted(set(dropped_source_types_seen))),
            packed_core_count=packed_core_count,
            packed_supporting_count=packed_supporting_count,
            packed_background_count=packed_background_count,
        )
        raw_findings = tuple(ResearchFinding(url=finding.url, title=finding.title, summary=finding.summary) for finding in all_findings)
        final_report = evolving_report or """# Deep Research

No report was produced."""
        provisional_result = ResearchResultArtifact(
            job_id=job_id,
            owner_id=running.owner_id,
            query=running.query,
            status=ResearchJobStatus.DONE,
            completion_mode=ResearchCompletionMode.FULL,
            result=final_report,
            raw_report=evolving_report or "",
            category=running.settings.category,
            stats=stats,
            sources=tuple(ResearchSource(url=hit.url, title=hit.title) for hit in all_hits),
            raw_findings=raw_findings,
            planning_analysis=running.planning_analysis,
            problem_analysis=running.problem_analysis,
            execution_plan=running.execution_plan,
            evidence_pack=evidence_pack,
            branch_proposals=branch_proposals,
            branch_evaluation=branch_evaluation,
        )
        projected_sources = _project_source_refs(
            provisional_result,
            _project_supporting_evidence(provisional_result),
        )
        post_evaluation = _evaluate_research_result(
            query=running.query,
            findings=raw_findings,
            report=final_report,
            stats=stats,
        )
        reflection = _derive_reflection(
            problem_analysis=running.problem_analysis,
            execution_plan=running.execution_plan,
            evidence_pack=evidence_pack,
            branch_evaluation=branch_evaluation,
            evaluation=post_evaluation,
        )
        result = ResearchResultArtifact(
            job_id=job_id,
            owner_id=running.owner_id,
            query=running.query,
            status=ResearchJobStatus.DONE,
            completion_mode=ResearchCompletionMode.FULL,
            result=final_report,
            raw_report=evolving_report or "",
            category=running.settings.category,
            stats=stats,
            sources=projected_sources,
            raw_findings=raw_findings,
            planning_analysis=running.planning_analysis,
            problem_analysis=running.problem_analysis,
            execution_plan=running.execution_plan,
            evidence_pack=evidence_pack,
            branch_proposals=branch_proposals,
            branch_evaluation=branch_evaluation,
            reflection=reflection,
            evaluation=post_evaluation,
            created_at=running.created_at,
            completed_at=completed_at,
        )
        self.persistence.results.save_result(result)
        compiled_artifact = _compile_research_artifact(result)
        self.persistence.compiled.save_artifact(compiled_artifact)
        self.persistence.compiled_lint.save_lint(_lint_compiled_research_artifact(compiled_artifact))
        done = replace(running, status=ResearchJobStatus.DONE, completed_at=completed_at)
        self.persistence.jobs.save_job(done)
        _emit_progress(self.persistence, 
            job_id,
            ResearchJobStatus.DONE,
            ResearchPhase.WRITING,
            round=round_number,
            total_sources=len(all_hits),
            total_findings=len(all_findings),
            message="Research job completed.",
            final=True,
        )
        return result

    def save_partial_result(
        self,
        job_id: str,
        *,
        mode: ResearchCompletionMode = ResearchCompletionMode.PARTIAL_ERROR,
        duration_seconds: int | None = None,
        rounds: int | None = None,
        queries: int | None = None,
        urls: int | None = None,
        search_providers: tuple[str, ...] = (),
        pre_extraction_sources_seen: int | None = None,
        pre_extraction_sources_kept: int | None = None,
        pre_extraction_sources_dropped: int | None = None,
        authority_policy_applied: bool | None = None,
        authority_filter_fallback_used: bool | None = None,
        dropped_source_types: tuple[str, ...] = (),
        packed_core_count: int | None = None,
        packed_supporting_count: int | None = None,
        packed_background_count: int | None = None,
    ) -> ResearchResultArtifact | None:
        job = self.persistence.jobs.get_job(job_id)
        if job is None:
            return None
        completed_at = _utcnow()
        stats = ResearchStats(
            duration_seconds=duration_seconds if duration_seconds is not None else 1,
            rounds=rounds if rounds is not None else 1,
            queries=queries if queries is not None else 1,
            urls=urls if urls is not None else 1,
            model=job.settings.model,
            search_providers=search_providers,
            pre_extraction_sources_seen=pre_extraction_sources_seen if pre_extraction_sources_seen is not None else 1,
            pre_extraction_sources_kept=pre_extraction_sources_kept if pre_extraction_sources_kept is not None else 1,
            pre_extraction_sources_dropped=pre_extraction_sources_dropped if pre_extraction_sources_dropped is not None else 0,
            authority_policy_applied=authority_policy_applied if authority_policy_applied is not None else _procedural_query_bias(job.query),
            authority_filter_fallback_used=authority_filter_fallback_used if authority_filter_fallback_used is not None else False,
            dropped_source_types=dropped_source_types,
            packed_core_count=packed_core_count if packed_core_count is not None else 1,
            packed_supporting_count=packed_supporting_count if packed_supporting_count is not None else 0,
            packed_background_count=packed_background_count if packed_background_count is not None else 0,
        )
        raw_findings = (ResearchFinding(url="https://example.test/partial", title="Partial source", summary="One useful finding survived."),)
        report = """# Partial Deep Research result

Partial salvage preserved."""
        salvage_evidence_pack = ResearchEvidencePack(
            query_class=_classify_query(job.query),
            core=raw_findings,
            supporting=(),
            background=(),
            has_direct_procedural_evidence=_procedural_query_bias(job.query),
        )
        salvage_branch_proposals = _derive_branch_proposals(
            problem_analysis=job.problem_analysis,
            execution_plan=job.execution_plan,
        )
        salvage_branch_evaluation = _evaluate_branch_proposals(
            problem_analysis=job.problem_analysis,
            execution_plan=job.execution_plan,
            evidence_pack=salvage_evidence_pack,
            branch_proposals=salvage_branch_proposals,
        )
        salvage_evaluation = _evaluate_research_result(
            query=job.query,
            findings=raw_findings,
            report=report,
            stats=stats,
        )
        salvage_reflection = _derive_reflection(
            problem_analysis=job.problem_analysis,
            execution_plan=job.execution_plan,
            evidence_pack=salvage_evidence_pack,
            branch_evaluation=salvage_branch_evaluation,
            evaluation=salvage_evaluation,
        )
        result = ResearchResultArtifact(
            job_id=job_id,
            owner_id=job.owner_id,
            query=job.query,
            status=ResearchJobStatus.DONE,
            completion_mode=mode,
            result=report,
            raw_report="Partial synthesis was available before failure.",
            category=job.settings.category,
            stats=stats,
            sources=(ResearchSource(url="https://example.test/partial", title="Partial source"),),
            raw_findings=raw_findings,
            planning_analysis=job.planning_analysis,
            problem_analysis=job.problem_analysis,
            execution_plan=job.execution_plan,
            evidence_pack=salvage_evidence_pack,
            branch_proposals=salvage_branch_proposals,
            branch_evaluation=salvage_branch_evaluation,
            reflection=salvage_reflection,
            evaluation=salvage_evaluation,
            created_at=job.created_at,
            completed_at=completed_at,
        )
        self.persistence.results.save_result(result)
        compiled_artifact = _compile_research_artifact(result)
        self.persistence.compiled.save_artifact(compiled_artifact)
        self.persistence.compiled_lint.save_lint(_lint_compiled_research_artifact(compiled_artifact))
        done = replace(job, status=ResearchJobStatus.DONE, completed_at=completed_at)
        self.persistence.jobs.save_job(done)
        _emit_progress(self.persistence, 
            job_id,
            ResearchJobStatus.DONE,
            ResearchPhase.ERROR,
            total_sources=1,
            total_findings=1,
            message="Partial research artifact salvaged after failure.",
            final=True,
        )
        return result

    


def _emit_progress(
    persistence: ResearchPersistence,
    job_id: str,
    status: ResearchJobStatus,
    phase: ResearchPhase,
    *,
    round: int = 0,
    queries: int = 0,
    query_preview: str | None = None,
    query_list: tuple[str, ...] = (),
    providers_attempted: tuple[str, ...] = (),
    total_sources: int = 0,
    new_sources: int = 0,
    total_findings: int = 0,
    url: str | None = None,
    title: str | None = None,
    message: str | None = None,
    details: dict[str, Any] | None = None,
    final: bool = False,
) -> None:
    persistence.progress.append_event(
        ResearchProgressEvent(
            job_id=job_id,
            status=status,
            phase=phase,
            round=round,
            queries=queries,
            query_preview=query_preview,
            query_list=query_list,
            providers_attempted=providers_attempted,
            total_sources=total_sources,
            new_sources=new_sources,
            total_findings=total_findings,
            url=url,
            title=title,
            message=message,
            details=details,
            final=final,
        )
    )


def _dedupe_hits(
    existing_hits: list[SearchHit],
    candidate_hits: tuple[SearchHit, ...],
    *,
    query: str,
    subject_sheet: SubjectSheet | None = None,
    planning_analysis: PlanningAnalysis | None = None,
) -> list[SearchHit]:
    seen = {hit.url for hit in existing_hits}
    domain_counts: dict[str, int] = {}
    for hit in existing_hits:
        domain = _normalized_domain(hit.url)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    deduped: list[SearchHit] = []
    for hit in candidate_hits:
        if hit.url in seen:
            continue
        if not _llm_or_heuristic_relevant_hit(query=query, hit=hit, subject_sheet=subject_sheet, planning_analysis=planning_analysis):
            continue
        domain = _normalized_domain(hit.url)
        limit = _max_hits_per_domain(query, domain)
        if domain_counts.get(domain, 0) >= limit:
            continue
        seen.add(hit.url)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        deduped.append(hit)
    return deduped





def _build_official_subject_precision_prompt(
    *,
    query: str,
    hit: SearchHit,
    subject_sheet: "SubjectSheet | None" = None,
    preview_text: str | None = None,
) -> str:
    subject_context = ""
    if subject_sheet is not None:
        primary_subject_obj = getattr(subject_sheet, 'primary_subject', None)
        primary_subject = getattr(primary_subject_obj, 'name', primary_subject_obj) or ""
        raw_aliases = getattr(subject_sheet, 'subject_aliases', None)
        if raw_aliases is None:
            raw_aliases = getattr(subject_sheet, 'aliases', ()) or ()
        raw_entities = getattr(subject_sheet, 'entities', None)
        if raw_entities is None:
            raw_entities = getattr(subject_sheet, 'related_entities', ()) or ()
        aliases = ", ".join(str(alias) for alias in tuple(raw_aliases)[:6])
        entities = ", ".join(
            getattr(entity, 'canonical_name', getattr(entity, 'name', str(entity)))
            for entity in tuple(raw_entities)[:6]
        )
        subject_context = (
            f"Primary subject: {primary_subject}\n"
            f"Subject aliases: {aliases}\n"
            f"Key entities: {entities}\n"
        )
    preview_block = f"Preview text:\n{preview_text}\n" if preview_text else ""
    return f"""
You are judging whether an official source is about the exact subject requested by the user.

User query:
{query}

{subject_context}Candidate source:
- URL: {hit.url}
- Title: {hit.title}
- Snippet: {hit.snippet}

{preview_block}Classify this source into exactly one bucket:
- exact_subject: directly about the user's specific case, entity, event, institution matter, or target issue
- related_but_broad: official and related domain/institutionally, but broader, adjacent, or about a different case
- off_topic: not materially about the user’s requested subject

Be strict. A general KNF, NIK, ministry, or sector report is not exact_subject unless it is clearly about the named case.

Return JSON only with this exact schema:
{{
  "subject_match": "exact_subject|related_but_broad|off_topic",
  "confidence": 0.0,
  "reason": "string"
}}
""".strip()


def _build_official_evidence_family_prompt(*, query: str, findings: tuple[ExtractedFinding, ...]) -> str:
    lines = []
    for idx, finding in enumerate(findings):
        lines.append(
            f'[{idx}]\nTitle: {finding.title}\nURL: {finding.url}\nSummary: {_clean_report_summary_text(finding.summary)}\n'
        )
    findings_block = '\n'.join(lines)
    return (
        'You are identifying which official pages in one topical family are canonical enough to keep as the main evidence pages.\n'
        'Return strict JSON only: {"canonical_indexes":[0,1],"reason":"short"}.\n'
        'Pick the smallest set of pages that directly answer the query.\n'
        'Do not keep collateral, homepage, portal, or loosely related official pages unless they are necessary.\n\n'
        f'User query: {query}\n\n'
        f'Candidate pages:\n{findings_block}\n'
    )


def _build_official_evidence_judge_prompt(*, query: str, hit: SearchHit, planning_analysis: PlanningAnalysis | None = None) -> str:
    query_class = planning_analysis.query_class.value if planning_analysis is not None else _classify_query(query).value
    goal = planning_analysis.goal if planning_analysis is not None else ''
    return (
        'You are judging whether an official/public-law source is semantically useful for answering the user query.\n'
        'Return strict JSON only: {"verdict":"primary|supporting|collateral|reject","confidence":0.0-1.0,"reason":"short"}.\n'
        'Use primary for a source that directly answers the query.\n'
        'Use supporting for a useful official source that helps but is not central.\n'
        'Use collateral for official but only loosely related/admin/background material.\n'
        'Use reject for off-topic or unhelpful material.\n\n'
        f'Query class: {query_class}\n'
        f'Goal: {goal}\n'
        f'User query: {query}\n\n'
        f'Title: {hit.title}\n'
        f'URL: {hit.url}\n'
        f'Snippet: {hit.snippet}\n'
    )


def _build_search_relevance_prompt(*, query: str, hit: SearchHit) -> str:
    return (
        "Return strict JSON only with keys relevant (boolean), confidence (number), reason (string).\n"
        "Judge whether this found page/item is relevant enough to keep as candidate evidence for the research query.\n"
        "Prefer keeping official/institutional pages if they plausibly concern the named subject, control, decision, finding, or follow-up.\n"
        "Reject clearly off-topic, generic, or unrelated pages.\n\n"
        f"Query: {query}\n"
        f"URL: {hit.url}\n"
        f"Title: {hit.title}\n"
        f"Snippet: {hit.snippet}\n"
    )


def _llm_or_heuristic_relevant_hit(*, query: str, hit: SearchHit, relevance_judge: "LlmSearchRelevanceJudge | None" = None, subject_sheet: SubjectSheet | None = None, planning_analysis: PlanningAnalysis | None = None) -> bool:
    heuristic = _is_relevant_hit(query=query, hit=hit, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
    if heuristic:
        return True
    if relevance_judge is None:
        return False
    return relevance_judge.accept_hit(query=query, hit=hit)

def _search_rejection_summary(*, query: str, existing_hits: list[SearchHit], candidate_hits: tuple[SearchHit, ...], subject_sheet: SubjectSheet | None = None, planning_analysis: PlanningAnalysis | None = None) -> str:
    analysis = _search_rejection_details(query=query, existing_hits=existing_hits, candidate_hits=candidate_hits, subject_sheet=subject_sheet, planning_analysis=planning_analysis)
    parts = [f"accepted={analysis['accepted']}"]
    reason_counts = analysis['reason_counts']
    for key in ('duplicate', 'low_relevance', 'domain_limit'):
        value = reason_counts.get(key, 0)
        if value:
            parts.append(f"{key}={value}")
    return ', '.join(parts)


def _search_rejection_details(*, query: str, existing_hits: list[SearchHit], candidate_hits: tuple[SearchHit, ...], subject_sheet: SubjectSheet | None = None, planning_analysis: PlanningAnalysis | None = None) -> dict[str, object]:
    seen = {hit.url for hit in existing_hits}
    domain_counts: dict[str, int] = {}
    for hit in existing_hits:
        domain = _normalized_domain(hit.url)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    reasons = {
        'duplicate': 0,
        'low_relevance': 0,
        'domain_limit': 0,
    }
    accepted = 0
    accepted_hits: list[dict[str, object]] = []
    rejected_hits: list[dict[str, object]] = []
    for hit in candidate_hits:
        domain = _normalized_domain(hit.url)
        source_type = _source_type(hit.url, hit.title)
        relevance = _general_relevance_score(query=query, hit=hit)
        record = {
            'url': hit.url,
            'title': hit.title,
            'domain': domain,
            'source_type': source_type,
            'general_relevance': relevance,
        }
        if hit.url in seen:
            reasons['duplicate'] += 1
            rejected_hits.append({**record, 'reason': 'duplicate'})
            continue
        if not _is_relevant_hit(query=query, hit=hit, subject_sheet=subject_sheet, planning_analysis=planning_analysis):
            reasons['low_relevance'] += 1
            rejected_hits.append({**record, 'reason': 'low_relevance'})
            continue
        limit = _max_hits_per_domain(query, domain)
        if domain_counts.get(domain, 0) >= limit:
            reasons['domain_limit'] += 1
            rejected_hits.append({**record, 'reason': 'domain_limit', 'domain_limit': limit})
            continue
        seen.add(hit.url)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        accepted += 1
        accepted_hits.append({**record, 'reason': 'accepted', 'domain_count_after_accept': domain_counts[domain]})
    return {
        'accepted': accepted,
        'reason_counts': reasons,
        'accepted_hits': accepted_hits,
        'rejected_hits': rejected_hits,
    }


def build_research_execution(*, persistence: ResearchPersistence | None = None) -> ResearchExecution:
    persistence = persistence or create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)
    worker = FakeResearchWorker(persistence, pdf_ingest=StubPdfIngestor())
    return ResearchExecution(
        start_job=manager.start_job,
        get_job_status=manager.get_job_status,
        cancel_job=manager.cancel_job,
        get_job_result=manager.get_job_result,
        list_jobs=manager.list_jobs,
        run_job=worker,
    )


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "build_provider_search_adapter",
    "DeterministicPlanningAnalyzer",
    "ResearchSearchError",
    "build_search_adapter",
    "DeterministicStopRails",
    "LlmResearchSynthesizer",
    "SearxNGSearchAdapter",
    "SearchProviderBridge",
    "ChainedSearchAdapter",
    "FakeResearchWorker",
    "ResearchJobManager",
    "StubExtractor",
    "StubQueryGenerator",
    "StubResearchPlanner",
    "StubSearchAdapter",
    "SearxNGSearchAdapter",
    "WebSearchBackedSearchAdapter",
    "StubSynthesizer",
    "build_research_execution",
]
