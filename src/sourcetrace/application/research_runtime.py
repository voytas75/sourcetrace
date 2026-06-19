"""Runtime orchestration for the Deep Research lifecycle and bounded engine loop."""

from collections.abc import Callable
from urllib.error import URLError
from dataclasses import dataclass, replace
from datetime import UTC, datetime
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
    ResearchPlan,
    ResearchPlanner,
    ResearchQueryGenerator,
    ResearchSearchAdapter,
    ResearchSynthesizer,
    SearchHit,
    SynthesisResult,
)
from sourcetrace.domain.research import (
    ResearchCompletionMode,
    ResearchFinding,
    ResearchJob,
    ResearchJobStatus,
    ResearchPhase,
    ResearchProgressEvent,
    ResearchResultArtifact,
    ResearchSource,
    ResearchStats,
)
from sourcetrace.storage.research import ResearchPersistence, create_in_memory_research_persistence


class StubResearchPlanner:
    """Deterministic planner stub for the first engine-loop slice."""

    def __call__(self, query: str) -> ResearchPlan:
        return ResearchPlan(
            objective=query,
            subquestions=(
                f"What is the system shape of {query}?",
                f"What runtime rails matter for {query}?",
            ),
        )


class StubQueryGenerator:
    """Deterministic query generator stub with light domain-aware shaping."""

    def __call__(self, plan: ResearchPlan, *, round_number: int) -> tuple[str, ...]:
        objective = plan.objective.strip()
        normalized = objective.lower()
        if _looks_like_market_query(normalized):
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
        if round_number == 1:
            return (
                objective,
                f"{objective} architecture",
            )
        return (
            f"{objective} stop rails",
            f"{objective} result artifact",
        )



from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen




class ResearchSearchError(RuntimeError):
    """Raised when a provider-backed search adapter cannot return usable results."""


class SearxNGSearchAdapter:
    """HTTP-backed SearxNG adapter normalized to ResearchSearchAdapter output."""

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
        del round_number
        hits: list[SearchHit] = []
        seen: set[str] = set()
        try:
            for query in queries:
                for item in self._fetch(query):
                    url = str(item.get("url") or "").strip()
                    title = str(item.get("title") or query).strip() or query
                    snippet = str(item.get("content") or item.get("snippet") or "").strip()
                    if not url or url in seen:
                        continue
                    seen.add(url)
                    hits.append(SearchHit(url=url, title=title, snippet=snippet))
        except (OSError, TimeoutError, URLError, ValueError) as exc:
            raise ResearchSearchError(f"SearxNG search failed: {type(exc).__name__}: {exc}") from exc
        return tuple(hits)

    def _fetch(self, query: str) -> list[dict[str, object]]:
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
        return [item for item in results[: self.count] if isinstance(item, dict)]

class WebSearchBackedSearchAdapter:
    """Small real search adapter using a caller-supplied web search function."""

    def __init__(
        self,
        search_web: Callable[..., list[dict[str, object]]],
        *,
        count: int = 3,
    ) -> None:
        self.search_web = search_web
        self.count = count

    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        del round_number
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
        return tuple(hits)


class ChainedSearchAdapter:
    """Try multiple search adapters in order until one returns usable hits."""

    def __init__(self, *adapters: ResearchSearchAdapter) -> None:
        self.adapters = tuple(adapter for adapter in adapters if adapter is not None)

    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        if not self.adapters:
            return ()
        errors: list[str] = []
        for adapter in self.adapters:
            try:
                hits = adapter(queries, round_number=round_number)
            except ResearchSearchError as exc:
                errors.append(str(exc))
                continue
            if hits:
                return hits
        if errors:
            raise ResearchSearchError(" ; ".join(errors))
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
        return StubSearchAdapter()
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
        prompt = (
            "You are writing an operator-facing Deep Research update.\n"
            "Be concrete, compact, and evidence-first. Avoid vague meta commentary.\n"
            "Lead with the best current answer to the query, not with discussion of process.\n\n"
            f"Query: {query}\n"
            f"Round: {round_number}\n"
            f"Previous answer: {previous_answer}\n"
            f"Evidence:\n{evidence}\n\n"
            "Return plain markdown with exactly these sections in this order:\n"
            "## Current answer\n"
            "- 2 to 4 sentences answering the query directly\n\n"
            "## Key findings\n"
            "- 3 to 5 bullet points using only the strongest findings\n\n"
            "## Uncertainty\n"
            "- 1 to 3 bullet points describing what is still weak, ambiguous, or missing\n\n"
            "## Next checks\n"
            "- 1 to 3 bullet points for the next most useful verification steps\n"
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


class StubSearchAdapter:
    """Deterministic search adapter stub with normalized hits."""

    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        if round_number == 1:
            return (
                SearchHit(
                    url="https://example.test/odysseus-architecture",
                    title="Odysseus Deep Research Architecture",
                    snippet="Async jobs, progress streaming, and persisted artifacts.",
                ),
                SearchHit(
                    url="https://example.test/source-trace-design",
                    title="SourceTrace Deep Research Design",
                    snippet="Lifecycle-first implementation reduces rework.",
                ),
            )
        return (
            SearchHit(
                url="https://example.test/stop-rails",
                title="Deterministic Stop Rails",
                snippet="Bound the loop with max rounds and low-yield guards.",
            ),
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
        top_findings = _top_findings(findings, query=query)
        key_findings = "\n".join(
            f"- {finding.title}: {finding.summary}" for finding in top_findings[:4]
        ) or "- No useful findings in this round."
        summary_line = _summary_line(query=query, findings=top_findings)
        uncertainty = _uncertainty_lines(query=query, findings=top_findings)
        next_checks = _next_check_lines(query=query, findings=top_findings)
        report = (
            f"# Deep Research: {query}\n\n"
            f"## Current answer\n{summary_line}\n\n"
            f"## Key findings\n{key_findings}\n\n"
            f"## Uncertainty\n{uncertainty}\n\n"
            f"## Next checks\n{next_checks}"
        )
        return SynthesisResult(
            report_markdown=report,
            answer_summary=summary_line,
            should_continue=round_number < 2 and len(top_findings) > 0,
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
    return any(token in lowered for token in ("jak ", "how ", "wdroż", "wdroze", "deploy", "configuration", "baseline", "sccm", "kiedy", "when "))


def _looks_like_listing_page(hit: SearchHit) -> bool:
    haystack = f"{hit.title} {hit.url}".lower()
    return any(token in haystack for token in ("/category/", "/tag/", "/archive/", " category ", "| category", "– category", "archive"))


def _looks_like_weak_general_source(hit: SearchHit) -> bool:
    domain = _normalized_domain(hit.url)
    path = urlparse(hit.url).path.lower()
    title = hit.title.lower()
    weak_domains = {"quora.com"}
    if domain in weak_domains:
        return True
    if domain.endswith("blogspot.com") and path in {"", "/", "/index.html"}:
        return True
    if path in {"", "/", "/index.html"} and not any(token in title for token in ("configuration baseline", "sccm", "configuration manager", "microsoft learn")):
        return True
    if path.endswith('.pdf') and not any(token in f"{title} {hit.snippet}".lower() for token in ("configuration baseline", "sccm", "configuration manager", "compliance baseline")):
        return True
    return False


def _general_relevance_score(*, query: str, hit: SearchHit) -> int:
    haystack = f"{hit.title} {hit.snippet} {hit.url}".lower()
    score = 0
    keywords = _query_keywords(query)
    score += sum(2 for keyword in keywords if keyword in hit.title.lower())
    score += sum(1 for keyword in keywords if keyword in haystack)
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
    return matched >= 2 or _general_relevance_score(query=query, hit=hit) >= 4


def _source_type(url: str, title: str) -> str:
    haystack = f"{url} {title}".lower()
    if 'learn.microsoft.com' in haystack or any(token in haystack for token in ('/docs/', 'documentation', 'configuration manager | microsoft learn')):
        return 'official_docs'
    if any(token in haystack for token in ("technical", "technicals", "analysis", "chart")):
        return "analysis"
    if any(token in haystack for token in ("historical", "ohlcv", "price", "quotes", "markets", "market")):
        return "data"
    if 'youtube.com' in haystack or 'youtu.be' in haystack:
        return 'video'
    if any(token in haystack for token in ('blog', 'blogspot', 'anoopcnair')):
        return 'blog'
    if any(token in haystack for token in ("docs", "architecture", "design", "guide")):
        return "docs"
    return "generic"


def _source_rank_for_query(*, query: str, url: str, title: str) -> int:
    source_type = _source_type(url, title)
    if _procedural_query_bias(query):
        order = {
            'official_docs': 0,
            'docs': 1,
            'generic': 2,
            'blog': 3,
            'video': 4,
            'analysis': 5,
            'data': 6,
        }
        return order.get(source_type, 9)
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


def _top_findings(findings: tuple[ExtractedFinding, ...], limit: int = 5, query: str | None = None) -> tuple[ExtractedFinding, ...]:
    ranked = sorted(
        findings,
        key=lambda finding: (
            _source_rank_for_query(query=query or '', url=finding.url, title=finding.title),
            -len(finding.summary),
            -len(finding.title),
        ),
    )
    selected: list[ExtractedFinding] = []
    seen_types: set[str] = set()
    for finding in ranked:
        source_type = _source_type(finding.url, finding.title)
        if source_type in seen_types:
            continue
        selected.append(finding)
        seen_types.add(source_type)
        if len(selected) >= limit:
            return tuple(selected)
    for finding in ranked:
        if finding in selected:
            continue
        selected.append(finding)
        if len(selected) >= limit:
            break
    return tuple(selected)


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
        job = ResearchJob(
            job_id=f"rj-{uuid4().hex[:12]}",
            owner_id=request.owner_id,
            query=request.query,
            status=ResearchJobStatus.QUEUED,
            created_at=now,
            settings=request.settings,
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
        search: ResearchSearchAdapter | None = None,
        extract: ResearchExtractor | None = None,
        synthesize: ResearchSynthesizer | None = None,
        stop_rails: DeterministicStopRails | None = None,
    ) -> None:
        self.persistence = persistence
        self.planner = planner or StubResearchPlanner()
        self.query_generator = query_generator or StubQueryGenerator()
        self.search = search or build_search_adapter()
        self.extract = extract or StubExtractor()
        self.synthesize = synthesize or StubSynthesizer()
        self.stop_rails = stop_rails or DeterministicStopRails()

    def __call__(self, job_id: str) -> ResearchResultArtifact | None:
        job = self.persistence.jobs.get_job(job_id)
        if job is None:
            return None
        if job.status == ResearchJobStatus.CANCELLED:
            return self.persistence.results.get_result(job_id)
        if job.status == ResearchJobStatus.DONE:
            return self.persistence.results.get_result(job_id)

        started = replace(job, status=ResearchJobStatus.PROBING, started_at=_utcnow())
        self.persistence.jobs.save_job(started)
        self._emit(job_id, ResearchJobStatus.PROBING, ResearchPhase.PROBING, message="Probing runtime configuration.")

        running = replace(started, status=ResearchJobStatus.RUNNING)
        self.persistence.jobs.save_job(running)

        plan = self.planner(running.query)
        self._emit(job_id, ResearchJobStatus.RUNNING, ResearchPhase.PLANNING, round=1, message=f"Planning around {len(plan.subquestions)} subquestion(s).")

        round_number = 0
        total_urls = 0
        consecutive_empty_rounds = 0
        all_hits: list[SearchHit] = []
        all_findings: list[ExtractedFinding] = []
        evolving_report: str | None = None

        while True:
            round_number += 1
            current = self.persistence.jobs.get_job(job_id)
            if current is not None and current.status == ResearchJobStatus.CANCELLED:
                return self.persistence.results.get_result(job_id)

            queries = self.query_generator(plan, round_number=round_number)
            self._emit(
                job_id,
                ResearchJobStatus.RUNNING,
                ResearchPhase.SEARCHING,
                round=round_number,
                queries=len(queries),
                query_preview=queries[0] if queries else None,
                message=f"Running {len(queries)} search querie(s).",
            )
            try:
                hits = self.search(queries, round_number=round_number)
            except ResearchSearchError as exc:
                self._emit(
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
                    )
                self._emit(
                    job_id,
                    ResearchJobStatus.ERROR,
                    ResearchPhase.ERROR,
                    round=round_number,
                    message="Research job failed before any usable findings were collected.",
                    final=True,
                )
                errored = replace(running, status=ResearchJobStatus.ERROR, completed_at=_utcnow(), error=str(exc))
                self.persistence.jobs.save_job(errored)
                return None
            new_hits = self._dedupe_hits(all_hits, hits, query=running.query)
            all_hits.extend(new_hits)
            total_urls = len(all_hits)
            if new_hits:
                consecutive_empty_rounds = 0
            else:
                consecutive_empty_rounds += 1

            self._emit(
                job_id,
                ResearchJobStatus.RUNNING,
                ResearchPhase.READING,
                round=round_number,
                total_sources=total_urls,
                new_sources=len(new_hits),
                url=new_hits[0].url if new_hits else None,
                title=new_hits[0].title if new_hits else None,
                message=f"Normalized {len(new_hits)} new source(s).",
            )

            findings = self.extract(tuple(new_hits))
            all_findings.extend(findings)
            self._emit(
                job_id,
                ResearchJobStatus.RUNNING,
                ResearchPhase.ANALYZING,
                round=round_number,
                total_sources=total_urls,
                total_findings=len(all_findings),
                message=f"Extracted {len(findings)} finding(s) this round.",
            )

            synthesis = self.synthesize(
                query=running.query,
                round_number=round_number,
                findings=findings,
                previous_report=evolving_report,
            )
            evolving_report = synthesis.report_markdown
            self._emit(
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
        result = ResearchResultArtifact(
            job_id=job_id,
            owner_id=running.owner_id,
            query=running.query,
            status=ResearchJobStatus.DONE,
            completion_mode=ResearchCompletionMode.FULL,
            result=evolving_report or """# Deep Research

No report was produced.""",
            raw_report=evolving_report or "",
            category=running.settings.category,
            stats=ResearchStats(
                duration_seconds=1,
                rounds=round_number,
                queries=2 * round_number,
                urls=len(all_hits),
                model=running.settings.model,
                search_providers=((running.settings.search_provider,) if running.settings.search_provider else ("stub-search",)),
            ),
            sources=tuple(ResearchSource(url=hit.url, title=hit.title) for hit in all_hits),
            raw_findings=tuple(ResearchFinding(url=finding.url, title=finding.title, summary=finding.summary) for finding in all_findings),
            created_at=running.created_at,
            completed_at=completed_at,
        )
        self.persistence.results.save_result(result)
        done = replace(running, status=ResearchJobStatus.DONE, completed_at=completed_at)
        self.persistence.jobs.save_job(done)
        self._emit(
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
    ) -> ResearchResultArtifact | None:
        job = self.persistence.jobs.get_job(job_id)
        if job is None:
            return None
        completed_at = _utcnow()
        result = ResearchResultArtifact(
            job_id=job_id,
            owner_id=job.owner_id,
            query=job.query,
            status=ResearchJobStatus.DONE,
            completion_mode=mode,
            result="""# Partial Deep Research result

Partial salvage preserved.""",
            raw_report="Partial synthesis was available before failure.",
            category=job.settings.category,
            stats=ResearchStats(duration_seconds=1, rounds=1, queries=1, urls=1, model=job.settings.model),
            sources=(ResearchSource(url="https://example.test/partial", title="Partial source"),),
            raw_findings=(ResearchFinding(url="https://example.test/partial", title="Partial source", summary="One useful finding survived."),),
            created_at=job.created_at,
            completed_at=completed_at,
        )
        self.persistence.results.save_result(result)
        done = replace(job, status=ResearchJobStatus.DONE, completed_at=completed_at)
        self.persistence.jobs.save_job(done)
        self._emit(
            job_id,
            ResearchJobStatus.DONE,
            ResearchPhase.ERROR,
            total_sources=1,
            total_findings=1,
            message="Partial research artifact salvaged after failure.",
            final=True,
        )
        return result

    def _dedupe_hits(
        self,
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

    def _emit(
        self,
        job_id: str,
        status: ResearchJobStatus,
        phase: ResearchPhase,
        *,
        round: int = 0,
        queries: int = 0,
        query_preview: str | None = None,
        total_sources: int = 0,
        new_sources: int = 0,
        total_findings: int = 0,
        url: str | None = None,
        title: str | None = None,
        message: str | None = None,
        final: bool = False,
    ) -> None:
        self.persistence.progress.append_event(
            ResearchProgressEvent(
                job_id=job_id,
                status=status,
                phase=phase,
                round=round,
                queries=queries,
                query_preview=query_preview,
                total_sources=total_sources,
                new_sources=new_sources,
                total_findings=total_findings,
                url=url,
                title=title,
                message=message,
                final=final,
            )
        )


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
