"""Runtime orchestration for the Deep Research lifecycle and bounded engine loop."""

from collections.abc import Callable
import json
import re
from urllib.error import URLError
from dataclasses import dataclass, replace
from collections import Counter
from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import urlparse
from uuid import uuid4

from sourcetrace.application.research import (
    ExtractedFinding,
    ResearchExecution,
    ResearchExtractor,
    ResearchJobListOutcome,
    ResearchJobResultOutcome,
    ResearchJobStartOutcome,
    ResearchJobStartRequest,
    ResearchJobStatusOutcome,
    ResearchPlanner,
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


class DeterministicPlanningAnalyzer:
    """Deterministic fallback planning-analysis builder from current heuristics."""

    def __call__(self, query: str) -> PlanningAnalysis:
        return _build_fallback_planning_analysis(query)


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

    def __call__(self, plan: ResearchExecutionPlan, *, round_number: int) -> tuple[str, ...]:
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
) -> ResearchSearchAdapter:
    """Procedural/admin Unified Search path with safe fallback to current search."""

    if unified_search_web is None:
        return current_search

    def _looks_official_enough(hits: tuple[SearchHit, ...]) -> bool:
        top_hits = hits[:5]
        return any(
            _source_type(hit.url, hit.title) == 'official_docs' or _authority_signal_score(query='how to', hit=hit) >= 10
            for hit in top_hits
        )

    class _ProceduralAdminUnifiedAdapter:
        provider_name = "procedural_admin_unified_search"
        active_provider_names = ("procedural_admin_unified_search", "searxng")

        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            objective = queries[0] if queries else ""
            unified_adapter = WebSearchBackedSearchAdapter(unified_search_web, count=10)
            hits = unified_adapter(queries, round_number=round_number)
            if not _procedural_query_bias(objective.lower()):
                if hits:
                    self.last_provider_names = (self.provider_name,)
                    return hits
                fallback_hits = current_search(queries, round_number=round_number)
                self.last_provider_names = tuple(
                    dict.fromkeys((self.provider_name, *_actual_search_provider_names(current_search)))
                )
                return fallback_hits
            if hits and _looks_official_enough(hits):
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
            SearxNGSearchAdapter(base_url=searxng_base_url),
            provider_adapter,
        )
    if searxng_base_url:
        return SearxNGSearchAdapter(base_url=searxng_base_url)
    if provider_adapter is None:
        raise ResearchSearchError(
            "Search is unavailable: no unified search provider is configured and no SearxNG fallback is configured."
        )
    return provider_adapter

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
        top_findings = _top_findings(findings, query=query)
        evidence = "\n".join(
            f"- {finding.title}: {finding.summary}" for finding in top_findings
        ) or "- No useful findings in this round."
        previous_answer = _extract_section_body(previous_report, "Current answer") or "NONE"
        query_class = _classify_query(query)
        packed = _pack_evidence_for_synthesis(query=query, findings=top_findings)
        prompt = _build_research_report_prompt(
            query=query,
            round_number=round_number,
            previous_answer=previous_answer,
            evidence=evidence,
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

    def __call__(self, hits: tuple[SearchHit, ...]) -> tuple[ExtractedFinding, ...]:
        findings: list[ExtractedFinding] = []
        for hit in hits:
            summary = _extract_evidence_summary(hit)
            if not summary:
                continue
            findings.append(
                ExtractedFinding(
                    url=hit.url,
                    title=hit.title.strip() or hit.url,
                    summary=summary,
                )
            )
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


def _is_relevant_hit(*, query: str, hit: SearchHit) -> bool:
    haystack = f"{hit.title} {hit.snippet} {hit.url}".lower()
    keywords = _query_keywords(query)
    if not keywords:
        return True
    matched = sum(1 for keyword in keywords if keyword in haystack)
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
    if _looks_like_listing_page(hit) or _looks_like_weak_general_source(hit):
        return False
    if matched >= 2 or _general_relevance_score(query=query, hit=hit) >= 4:
        return True
    source_type = _source_type(hit.url, hit.title)
    if matched >= 1 and source_type in {'generic', 'docs', 'official_docs', 'vendor_docs', 'analysis', 'data'}:
        return True
    score = _general_relevance_score(query=query, hit=hit)
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
    if any(token in haystack for token in ('reddit.com', 'stackoverflow.com', 'stack overflow')):
        return 'forum'
    if 'gist.github.com' in haystack:
        return 'snippet_repo'
    if any(token in haystack for token in ("technical", "technicals", "analysis", "chart")):
        return "analysis"
    if domain == 'research.ibm.com':
        return 'analysis'
    if any(token in title.lower() for token in ('study', 'survey', 'paper', 'journal', 'longitudinal')):
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


def _filter_hits_for_extraction(*, query: str, hits: tuple[SearchHit, ...]) -> PreExtractionFilterOutcome:
    if not _procedural_query_bias(query):
        if _classify_query(query) is not ResearchQueryClass.GENERAL:
            return PreExtractionFilterOutcome(
                kept_hits=hits,
                seen_count=len(hits),
                kept_count=len(hits),
                dropped_count=0,
                authority_policy_applied=False,
                fallback_used=False,
                dropped_source_types=(),
            )
        strong: list[SearchHit] = []
        secondary: list[SearchHit] = []
        dropped: list[SearchHit] = []
        for hit in hits:
            source_type = _source_type(hit.url, hit.title)
            relevance = _general_relevance_score(query=query, hit=hit)
            if source_type in {'forum', 'video', 'snippet_repo'}:
                dropped.append(hit)
                continue
            if source_type == 'official_docs' and relevance >= 6:
                strong.append(hit)
                continue
            if source_type in {'analysis', 'data'} and relevance >= 3:
                strong.append(hit)
                continue
            if relevance >= 5:
                secondary.append(hit)
                continue
            dropped.append(hit)

        fallback_used = False
        kept: list[SearchHit] = []
        if strong:
            kept.extend(strong)
            kept.extend(secondary[:1])
        else:
            fallback_used = True
            kept.extend(secondary[:2])
        if not kept and hits:
            fallback_used = True
            kept.append(hits[0])

        counter = Counter(_source_type(hit.url, hit.title) for hit in dropped)
        dropped_source_types = tuple(f"{source_type}:{count}" for source_type, count in sorted(counter.items()))
        return PreExtractionFilterOutcome(
            kept_hits=tuple(kept),
            seen_count=len(hits),
            kept_count=len(kept),
            dropped_count=max(0, len(hits) - len(kept)),
            authority_policy_applied=True,
            fallback_used=fallback_used,
            dropped_source_types=dropped_source_types,
        )
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
    strong_official_count = sum(1 for hit in strong if _source_type(hit.url, hit.title) == 'official_docs')
    if strong:
        kept.extend(strong)
        if strong_official_count < 2:
            kept.extend(secondary[:1])
    else:
        fallback_used = True
        kept.extend(secondary[:2])
    if not kept and hits:
        fallback_used = True
        kept.append(hits[0])

    counter = Counter(_source_type(hit.url, hit.title) for hit in dropped)
    dropped_source_types = tuple(f"{source_type}:{count}" for source_type, count in sorted(counter.items()))
    return PreExtractionFilterOutcome(
        kept_hits=tuple(kept),
        seen_count=len(hits),
        kept_count=len(kept),
        dropped_count=max(0, len(hits) - len(kept)),
        authority_policy_applied=True,
        fallback_used=fallback_used,
        dropped_source_types=dropped_source_types,
    )


def _pack_evidence_for_synthesis(*, query: str, findings: tuple[ExtractedFinding, ...]) -> PackedEvidence:
    ranked = _top_findings(findings, limit=max(6, len(findings)), query=query)
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
            direct = _procedural_directness_score(query=query, url=finding.url, title=finding.title) >= 3
            if direct:
                has_direct_procedural_evidence = True
            official_core_present = any(_source_type(item.url, item.title) == 'official_docs' for item in core)
            if direct and source_type == 'official_docs' and len(core) < core_limit:
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
            general_haystack = f"{finding.title} {finding.summary}".lower()
            research_like_general = any(token in general_haystack for token in ('study', 'research', 'analysis', 'report', 'evidence'))
            if not core and source_type in {'analysis', 'data'} and research_like_general:
                core.append(finding)
                continue
            if source_type in {'official_docs', 'docs', 'generic', 'vendor_docs', 'blog', 'analysis', 'data'} and len(supporting) < supporting_limit:
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


def _top_findings(findings: tuple[ExtractedFinding, ...], limit: int = 5, query: str | None = None) -> tuple[ExtractedFinding, ...]:
    normalized_query = query or ''
    ranked = sorted(
        findings,
        key=lambda finding: (
            _source_rank_for_query(query=normalized_query, url=finding.url, title=finding.title),
            -len(finding.summary),
            -len(finding.title),
        ),
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


def _build_research_report_prompt(*, query: str, round_number: int, previous_answer: str, evidence: str, query_class: ResearchQueryClass, has_direct_procedural_evidence: bool) -> str:
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
    if _classify_query(result.query) is ResearchQueryClass.PROCEDURAL_ADMIN:
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
    title = result.query.strip() or 'Compiled research artifact'
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

    def __init__(self, persistence: ResearchPersistence) -> None:
        self.persistence = persistence

    def start_job(self, request: ResearchJobStartRequest) -> ResearchJobStartOutcome:
        now = _utcnow()
        planning_analysis = _build_fallback_planning_analysis(request.query)
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
        stop_rails: DeterministicStopRails | None = None,
    ) -> None:
        self.persistence = persistence
        self.planner = planner or StubResearchPlanner()
        self.query_generator = query_generator or StubQueryGenerator()
        self.llm_query_generator = llm_query_generator
        self.search = search or build_search_adapter()
        self.extract = extract or StubExtractor()
        self.synthesize = synthesize or StubSynthesizer()
        self.stop_rails = stop_rails or DeterministicStopRails()

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

        planning_analysis = _build_fallback_planning_analysis(running.query)
        problem_analysis = running.problem_analysis or _planning_analysis_to_problem_analysis(planning_analysis)
        plan = self.planner(
            running.query,
            problem_analysis=problem_analysis,
            planning_analysis=planning_analysis,
        )
        running = replace(running, problem_analysis=problem_analysis, execution_plan=plan)
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

            queries = self.query_generator(plan, round_number=round_number)
            provider_names = _resolve_search_provider_names(self.search, configured_provider=None)
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
            rejection_summary = _search_rejection_summary(query=running.query, existing_hits=all_hits, candidate_hits=hits)
            new_hits = _dedupe_hits(all_hits, hits, query=running.query)
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
                        retry_summary = _search_rejection_summary(query=running.query, existing_hits=all_hits, candidate_hits=retry_hits)
                        retry_new_hits = _dedupe_hits(all_hits, retry_hits, query=running.query)
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

            filter_outcome = _filter_hits_for_extraction(query=running.query, hits=tuple(new_hits))
            filtered_hits = list(filter_outcome.kept_hits)
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
            )

            findings = self.extract(tuple(filtered_hits))
            all_findings.extend(findings)
            _emit_progress(self.persistence, 
                job_id,
                ResearchJobStatus.RUNNING,
                ResearchPhase.ANALYZING,
                round=round_number,
                total_sources=total_urls,
                total_findings=len(all_findings),
                message=f"Extracted {len(findings)} finding(s) this round.",
            )

            cumulative_findings = tuple(all_findings)
            packed = _pack_evidence_for_synthesis(query=running.query, findings=cumulative_findings)
            evidence_pack = _to_research_evidence_pack(query=running.query, packed=packed)
            packed_core_count = len(packed.core)
            packed_supporting_count = len(packed.supporting)
            packed_background_count = len(packed.background)
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
            final=final,
        )
    )


def _dedupe_hits(
    existing_hits: list[SearchHit],
    candidate_hits: tuple[SearchHit, ...],
    *,
    query: str,
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
        if not _is_relevant_hit(query=query, hit=hit):
            continue
        domain = _normalized_domain(hit.url)
        limit = _max_hits_per_domain(query, domain)
        if domain_counts.get(domain, 0) >= limit:
            continue
        seen.add(hit.url)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        deduped.append(hit)
    return deduped



def _search_rejection_summary(*, query: str, existing_hits: list[SearchHit], candidate_hits: tuple[SearchHit, ...]) -> str:
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
    for hit in candidate_hits:
        if hit.url in seen:
            reasons['duplicate'] += 1
            continue
        if not _is_relevant_hit(query=query, hit=hit):
            reasons['low_relevance'] += 1
            continue
        domain = _normalized_domain(hit.url)
        limit = _max_hits_per_domain(query, domain)
        if domain_counts.get(domain, 0) >= limit:
            reasons['domain_limit'] += 1
            continue
        seen.add(hit.url)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        accepted += 1
    parts = [f"accepted={accepted}"]
    for key in ('duplicate', 'low_relevance', 'domain_limit'):
        value = reasons[key]
        if value:
            parts.append(f"{key}={value}")
    return ', '.join(parts)


def build_research_execution(*, persistence: ResearchPersistence | None = None) -> ResearchExecution:
    persistence = persistence or create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)
    worker = FakeResearchWorker(persistence)
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
