import json

from sourcetrace_v2.app.composition.runtime import build_preferred_search_backed_stubbed_jsonl_runtime
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request
from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate
from sourcetrace_v2.execution.stages.retrieval import (
    RetrievalStage,
    _candidate_target_quality_priority,
    _query_focus_tokens,
)


def test_run_flow_promotes_more_targeted_official_candidate_before_selection(tmp_path) -> None:
    runtime = build_preferred_search_backed_stubbed_jsonl_runtime(
        base_dir=tmp_path,
        base_url="http://127.0.0.1:8080",
        unified_search_web=lambda query, count=10: [
            {
                "url": "https://gov.example.test/labour/remote-work",
                "title": "Official labour ministry portal",
                "snippet": "Broad official portal page covering remote work obligations.",
            },
            {
                "url": "https://legal.example.test/remote-work-reporting-obligations",
                "title": "Detailed legal commentary on reporting obligations",
                "snippet": "Focused commentary on the exact reporting obligation question.",
            },
            {
                "url": "https://gov.example.test/labour/remote-work-reporting-faq",
                "title": "Official FAQ on remote work reporting obligations for employers in Poland",
                "snippet": "Specific official FAQ on remote work reporting obligations for employers in Poland.",
            },
        ],
    )

    response = handle_run_minimal_flow_request(
        job_id="job-target-quality",
        run_id="run-target-quality",
        seed_text="remote work reporting obligations Poland employer official guidance",
        runtime=runtime,
    )

    payload = json.loads(response.body)

    assert response.status_code == 201
    assert payload["artifact"]["present"] is True
    assert payload["evidence_input"]["candidates"][0]["title"] == (
        "Official FAQ on remote work reporting obligations for employers in Poland"
    )
    assert payload["evidence_input"]["candidates"][1]["title"] == "Official labour ministry portal"
    assert payload["selected_evidence"]["items"][0]["title"] == (
        "Official FAQ on remote work reporting obligations for employers in Poland"
    )
    assert "top_source=procedural_admin_unified_search:Official FAQ on remote work reporting obligations for employers in Poland" in payload["artifact"]["summary"]


def test_run_flow_prefers_official_guidance_surface_over_publication_like_institutional_result(tmp_path) -> None:
    runtime = build_preferred_search_backed_stubbed_jsonl_runtime(
        base_dir=tmp_path,
        base_url="http://127.0.0.1:8080",
        unified_search_web=lambda query, count=10: [
            {
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12622382/",
                "title": "Clarifying the legal requirement for cross-border sharing of health data ...",
                "snippet": "Academic article discussing cross-border sharing of health data.",
            },
            {
                "url": "https://www.edpb.europa.eu/sme/be-compliant/international-data-transfers_en",
                "title": "International data transfers | Data protection guide for small business",
                "snippet": "Official EDPB guidance for international data transfers under the GDPR.",
            },
            {
                "url": "https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/international-transfers/",
                "title": "International transfers",
                "snippet": "ICO guidance and resources for UK GDPR international transfers.",
            },
        ],
    )

    response = handle_run_minimal_flow_request(
        job_id="job-guidance-surface",
        run_id="run-guidance-surface",
        seed_text="cross-border data transfer official guidance",
        runtime=runtime,
    )

    payload = json.loads(response.body)

    assert response.status_code == 201
    assert payload["artifact"]["present"] is True
    assert payload["evidence_input"]["candidates"][0]["title"] == (
        "International data transfers | Data protection guide for small business"
    )
    assert payload["evidence_input"]["candidates"][1]["title"] == "International transfers"
    assert payload["evidence_input"]["candidates"][2]["title"] == (
        "Clarifying the legal requirement for cross-border sharing of health data ..."
    )
    assert payload["selected_evidence"]["items"][0]["title"] == (
        "International data transfers | Data protection guide for small business"
    )
    assert "top_source=procedural_admin_unified_search:International data transfers | Data protection guide for small business" in payload["artifact"]["summary"]


def test_run_flow_expands_and_reorders_community_quality_of_life_queries_toward_direct_outcomes(tmp_path) -> None:
    runtime = build_preferred_search_backed_stubbed_jsonl_runtime(
        base_dir=tmp_path,
        base_url="http://127.0.0.1:8080",
        unified_search_web=lambda query, count=10: [
            {
                "url": "https://example.test/brain-drain",
                "title": "Brain drain among diaspora communities in Germany",
                "snippet": "Study of migration outflows and return intentions.",
            },
            {
                "url": "https://example.test/transnational-care",
                "title": "Transnational care networks in migrant communities",
                "snippet": "Report on family care across borders.",
            },
            {
                "url": "https://example.test/cultural-identity",
                "title": "Cultural identity maintenance in diaspora communities",
                "snippet": "Analysis of identity, language, and belonging.",
            },
            {
                "url": "https://example.test/outcomes-report",
                "title": "Housing, employment and life satisfaction among the Polish diaspora in Germany",
                "snippet": "Direct outcome evidence on living conditions, labour market outcomes, and life satisfaction.",
            },
            {
                "url": "https://example.test/discrimination-report",
                "title": "Discrimination, education and health outcomes for migrant communities in Germany",
                "snippet": "Direct quality-of-life evidence about discrimination, education, and health.",
            },
            {
                "url": "https://example.test/general-diaspora-overview",
                "title": "Overview of diaspora communities in Germany",
                "snippet": "General background overview.",
            },
        ],
    )

    response = handle_run_minimal_flow_request(
        job_id="job-community-outcomes",
        run_id="run-community-outcomes",
        seed_text="What are the main findings in PDF reports about the quality of life of the Polish diaspora in Germany?",
        runtime=runtime,
    )

    payload = json.loads(response.body)

    assert response.status_code == 201
    assert payload["artifact"]["present"] is True
    assert payload["evidence_input"]["candidates"][0]["title"] == (
        "Housing, employment and life satisfaction among the Polish diaspora in Germany"
    )
    assert payload["evidence_input"]["candidates"][1]["title"] == (
        "Discrimination, education and health outcomes for migrant communities in Germany"
    )
    assert payload["evidence_input"]["candidates"][2]["title"] == "Brain drain among diaspora communities in Germany"
    assert "top_source=procedural_admin_unified_search:Housing, employment and life satisfaction among the Polish diaspora in Germany" in payload["artifact"]["summary"]


def test_relevance_focus_excludes_search_operator_clauses() -> None:
    query = "employer reporting obligations official guidance site:driver-registry.example OR site:labour-authority.example"

    assert _query_focus_tokens(query) == ("employer", "report", "obligation")


def test_target_quality_uses_semantic_terms_and_light_morphology_not_search_constraints() -> None:
    query = "employer official guidance site:driver-registry.example"
    driver_result = RetrievedEvidenceCandidate(
        candidate_id="driver", job_id="job", run_id="run", provider="fixture", query=query,
        title="Driver registry notice", url="https://driver-registry.example/notice",
        snippet="Driver registration information.", rank=1, source_type="institutional",
    )
    employer_result = RetrievedEvidenceCandidate(
        candidate_id="employer", job_id="job", run_id="run", provider="fixture", query=query,
        title="Employers handbook", url="https://labour-authority.example/handbook",
        snippet="Official obligations for employers.", rank=2, source_type="institutional",
    )

    assert _candidate_target_quality_priority(candidate=employer_result, query=query) > _candidate_target_quality_priority(
        candidate=driver_result, query=query
    )


def test_retrieval_stage_prefers_exact_subject_institutional_candidate_over_broad_adjacent_institutional_page() -> None:
    stage = RetrievalStage(search=None)  # type: ignore[arg-type]
    candidates = (
        RetrievedEvidenceCandidate(
            candidate_id="cand:1",
            job_id="job",
            run_id="run",
            provider="searxng",
            query="praca zdalna obowiązki pracodawcy zgłoszenie oficjalne gov.pl pip",
            title="Prawo do bycia offline - PARP - Centrum Rozwoju MŚP",
            url="https://www.parp.gov.pl/component/content/article/81845:prawo-do-bycia-offline",
            snippet="Bierność pracodawcy może wiązać się z wypaleniem zawodowym i problemami organizacyjnymi.",
            rank=1,
            source_type="institutional",
        ),
        RetrievedEvidenceCandidate(
            candidate_id="cand:2",
            job_id="job",
            run_id="run",
            provider="searxng",
            query="praca zdalna obowiązki pracodawcy zgłoszenie oficjalne gov.pl pip",
            title="Praca zdalna - Państwowa Inspekcja Pracy",
            url="https://www.pip.gov.pl/files/126/Dla-pracownikow/1139/Praca-zdalna.pdf",
            snippet="Oficjalny materiał PIP o pracy zdalnej i obowiązkach pracodawcy.",
            rank=2,
            source_type="institutional",
        ),
        RetrievedEvidenceCandidate(
            candidate_id="cand:3",
            job_id="job",
            run_id="run",
            provider="searxng",
            query="praca zdalna obowiązki pracodawcy zgłoszenie oficjalne gov.pl pip",
            title="Zgłoszenie oferty pracy - Urząd Pracy m.st. Warszawy - Wortal PSZ",
            url="https://warszawa.praca.gov.pl/zgloszenie-oferty-pracy",
            snippet="Informacje o zgłoszeniu oferty pracy do urzędu pracy.",
            rank=3,
            source_type="institutional",
        ),
    )

    shaped = stage._shape_source_mix(
        candidates=candidates,
        query="praca zdalna obowiązki pracodawcy zgłoszenie oficjalne gov.pl pip",
    )

    assert shaped[0].title == "Praca zdalna - Państwowa Inspekcja Pracy"
    assert shaped[0].rank == 1
