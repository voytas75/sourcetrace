"""Local launcher that wires runtime_config into the stdlib web server."""

from collections.abc import Callable
from os import environ
from pathlib import Path
from typing import Any

from sourcetrace.application import (
    ClaimExtractionOutcome,
    ClaimExtractionRequest,
    ClaimExtractionRuntime,
    CredibilityAssessmentExecution,
    CredibilityAssessmentOutcome,
    CredibilityAssessmentRequest,
    build_research_execution,
    build_search_adapter,
)
from sourcetrace.domain import Claim, ClaimEvidenceLink, Document, DocumentChunk, DocumentCredibilityAssessment
from sourcetrace.domain.types import CredibilityBand, ProvenanceDistance, VerificationVerdict
from sourcetrace.llm import build_llm_runtime
from sourcetrace.llm.errors import LlmConfigurationError
from sourcetrace.runtime_config import build_default_llm_config
from sourcetrace.web.api import run_local_server
from sourcetrace.web.delivery import create_default_delivery

_DEFAULT_WWW_HOST = "127.0.0.1"
_DEFAULT_WWW_PORT = 8000
_DEFAULT_RESEARCH_SYNTHESIS_FALLBACK = "## Current answer\nNo research synthesis content was generated.\n\n## Key findings\n- No structured research findings were returned.\n\n## Uncertainty\n- The synthesis backend returned an underspecified response.\n\n## Next checks\n- Re-run the research check with a markdown-shaped synthesis backend."


def _missing_litellm_completion(**_: Any) -> dict[str, Any]:
    raise RuntimeError(
        "LiteLLM completion function is not wired yet. "
        "Pass a real LiteLLM-compatible completion callable into build_local_server_runtime()."
    )


def _load_litellm_completion() -> Callable[..., dict[str, Any]] | None:
    try:
        from litellm import completion
    except ImportError:
        return None
    return completion


def _resolve_completion_fn(
    completion_fn: Callable[..., dict[str, Any]] | None,
) -> Callable[..., dict[str, Any]]:
    if completion_fn is not None:
        return completion_fn
    auto_completion_fn = _load_litellm_completion()
    if auto_completion_fn is not None:
        return auto_completion_fn
    raise RuntimeError(
        "LiteLLM is not installed in the local launcher environment. "
        "Install it or pass a real LiteLLM-compatible completion callable into build_local_server_runtime()."
    )


def _mirror_legacy_azure_env() -> None:
    if not environ.get("SOURCETRACE_LLM_API_KEY") and environ.get("AZURE_OPENAI_API_KEY"):
        environ["SOURCETRACE_LLM_API_KEY"] = environ["AZURE_OPENAI_API_KEY"]
    if not environ.get("SOURCETRACE_LLM_BASE_URL") and environ.get("AZURE_OPENAI_BASE_URL"):
        environ["SOURCETRACE_LLM_BASE_URL"] = environ["AZURE_OPENAI_BASE_URL"]
    if not environ.get("SOURCETRACE_LLM_API_VERSION") and environ.get("AZURE_OPENAI_API_VERSION"):
        environ["SOURCETRACE_LLM_API_VERSION"] = environ["AZURE_OPENAI_API_VERSION"]


def _build_runtime_config_with_legacy_env_fallback():
    _mirror_legacy_azure_env()
    try:
        return build_default_llm_config()
    except LlmConfigurationError:
        raise


def _resolve_server_bind() -> tuple[str, int]:
    host = environ.get("SOURCETRACE_WWW_HOST", _DEFAULT_WWW_HOST).strip() or _DEFAULT_WWW_HOST
    raw_port = environ.get("SOURCETRACE_WWW_PORT", str(_DEFAULT_WWW_PORT)).strip() or str(
        _DEFAULT_WWW_PORT
    )
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("SOURCETRACE_WWW_PORT must be an integer.") from exc
    return host, port


def _resolve_searxng_base_url() -> str | None:
    raw = environ.get("SOURCETRACE_SEARXNG_BASE_URL", "").strip()
    return raw or None


def _resolve_research_persistence_root_dir() -> Path | None:
    raw = environ.get("SOURCETRACE_RESEARCH_DATA_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path("data/research").resolve()


def _resolve_continuity_pack_root_dir() -> Path | None:
    raw_root_dir = environ.get("SOURCETRACE_CONTINUITY_PACK_ROOT_DIR", "").strip()
    if not raw_root_dir:
        return None
    resolved_root_dir = Path(raw_root_dir).expanduser().resolve()
    if resolved_root_dir.exists() and not resolved_root_dir.is_dir():
        raise ValueError(
            "SOURCETRACE_CONTINUITY_PACK_ROOT_DIR must point to a directory."
        )
    return resolved_root_dir


def _use_smoke_claim_extraction_stub() -> bool:
    return environ.get("SOURCETRACE_CI_SMOKE_STUB_CLAIM_EXTRACTION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _build_smoke_claim_extraction_runtime() -> ClaimExtractionRuntime:
    def extract_claims(
        request: ClaimExtractionRequest,
        *,
        document: Document,
        chunks: tuple[DocumentChunk, ...],
    ) -> ClaimExtractionOutcome:
        if not chunks:
            return ClaimExtractionOutcome(
                request=request,
                document=document,
                chunks=chunks,
                claims=(),
                evidence_links=(),
            )
        first_chunk = chunks[0]
        exact_text = first_chunk.raw_text.strip().split(".")[0].strip() or first_chunk.raw_text.strip()
        claim = Claim(
            claim_id=f"{document.document_id}:claim-smoke-1",
            case_id=request.case_id,
            document_id=request.document_id,
            chunk_id=first_chunk.chunk_id,
            exact_text=exact_text,
            source_span_reference=first_chunk.position_reference or "p1",
            system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            rationale="CI smoke stub claim extracted from first prepared chunk.",
        )
        evidence_link = ClaimEvidenceLink(
            claim_id=claim.claim_id,
            document_id=document.document_id,
            chunk_id=first_chunk.chunk_id,
            evidence_rank=1,
            evidence_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            rationale="CI smoke stub evidence link.",
            snippet=first_chunk.raw_text,
            score=None,
        )
        return ClaimExtractionOutcome(
            request=request,
            document=document,
            chunks=chunks,
            claims=(claim,),
            evidence_links=(evidence_link,),
            review_cautions=("ci_smoke_stub_claim_extraction",),
        )

    return ClaimExtractionRuntime(extract_claims=extract_claims)


def _use_smoke_credibility_stub() -> bool:
    return environ.get("SOURCETRACE_CI_SMOKE_STUB_CREDIBILITY", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _build_smoke_credibility_assessment_execution() -> CredibilityAssessmentExecution:
    def assess_credibility(
        request: CredibilityAssessmentRequest,
    ) -> CredibilityAssessmentOutcome:
        assessment = DocumentCredibilityAssessment(
            assessment_id=f"{request.document.document_id}:credibility-smoke-1",
            document_id=request.document.document_id,
            source_reliability=CredibilityBand.MEDIUM,
            information_credibility=CredibilityBand.MEDIUM,
            source_reliability_factors=("CI smoke stub used local launcher fallback.",),
            information_credibility_factors=("Assessment generated from deterministic smoke stub.",),
            provenance_distance=ProvenanceDistance.UNKNOWN,
            method=request.assessment_method or "ci_smoke_stub",
            notes="CI smoke stub credibility assessment.",
            summary="Looks plausible.",
            strengths=("Deterministic smoke stub response.",),
            concerns=("Not a production credibility assessment.",),
            verification_checks=("Run full credibility assessment outside CI smoke.",),
            assessed_at=request.document.retrieved_at,
        )
        return CredibilityAssessmentOutcome(request=request, assessment=assessment)

    return CredibilityAssessmentExecution(assess_credibility=assess_credibility)


def _research_synthesis_with_markdown_fallback(
    synthesize_text: Callable[[str], object],
) -> Callable[[str], object]:
    def wrapped(prompt: str) -> object:
        result = synthesize_text(prompt)
        text = str(getattr(result, "text", "") or "").strip()
        if text.startswith("## Current answer") and "## Next checks" in text:
            return result
        from types import SimpleNamespace
        return SimpleNamespace(text=_DEFAULT_RESEARCH_SYNTHESIS_FALLBACK)

    return wrapped


def build_local_server_runtime(
    *,
    completion_fn: Callable[..., dict[str, Any]] | None = None,
    research_search_web: Callable[..., list[dict[str, object]]] | None = None,
):
    """Build the local web server runtime using the repo-owned runtime config."""

    environ.setdefault("LITELLM_LOG", "ERROR")
    llm_runtime = build_llm_runtime(
        completion_fn=_resolve_completion_fn(completion_fn),
        config=_build_runtime_config_with_legacy_env_fallback(),
    )
    claim_extraction_runtime = (
        _build_smoke_claim_extraction_runtime()
        if _use_smoke_claim_extraction_stub()
        else None
    )
    credibility_assessment = (
        _build_smoke_credibility_assessment_execution()
        if _use_smoke_credibility_stub()
        else None
    )
    searxng_base_url = _resolve_searxng_base_url()
    research = build_research_execution()
    if searxng_base_url:
        from sourcetrace.application import (
            FakeResearchWorker,
            LlmResearchSynthesizer,
            ResearchExecution,
            ResearchJobManager,
        )
        from sourcetrace.storage import (
            create_file_backed_research_persistence,
            create_in_memory_research_persistence,
            recover_interrupted_research_jobs,
        )

        research_root = _resolve_research_persistence_root_dir()
        research_persistence = (
            create_file_backed_research_persistence(research_root)
            if research_root is not None
            else create_in_memory_research_persistence()
        )
        if research_root is not None:
            recover_interrupted_research_jobs(research_root)
            research_persistence = create_file_backed_research_persistence(research_root)
        research_manager = ResearchJobManager(research_persistence)
        research_synthesizer = LlmResearchSynthesizer(
            _research_synthesis_with_markdown_fallback(llm_runtime.research_synthesis)
        )
        provider_search = research_search_web
        research_worker = FakeResearchWorker(
            research_persistence,
            search=build_search_adapter(
                searxng_base_url=searxng_base_url,
                search_web=provider_search,
            ),
            synthesize=research_synthesizer,
        )
        research = ResearchExecution(
            start_job=research_manager.start_job,
            get_job_status=research_manager.get_job_status,
            cancel_job=research_manager.cancel_job,
            get_job_result=research_manager.get_job_result,
            list_jobs=research_manager.list_jobs,
            run_job=research_worker,
        )
    delivery = create_default_delivery(
        credibility_draft=None if credibility_assessment is not None else llm_runtime.credibility_draft,
        credibility_assessment=credibility_assessment,
        claim_extraction=llm_runtime.claim_extraction,
        claim_normalization=llm_runtime.claim_normalization,
        claim_extraction_runtime=claim_extraction_runtime,
        continuity_pack_root_dir=_resolve_continuity_pack_root_dir(),
        research=research,
        research_search_backend=("searxng" if searxng_base_url else "stub"),
        research_search_configured=bool(searxng_base_url),
    )
    host, port = _resolve_server_bind()
    return run_local_server(host=host, port=port, delivery=delivery)


def main() -> int:
    runtime = build_local_server_runtime()
    try:
        runtime.server.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        runtime.server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_local_server_runtime", "main"]
