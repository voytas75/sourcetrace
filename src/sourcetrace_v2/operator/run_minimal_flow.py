from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from uuid import uuid4

from sourcetrace.runtime_pdf_ingest import build_research_pdf_analyzer
from sourcetrace.runtime_pdf_backend_openclaw import openclaw_pdf_capability
from sourcetrace_v2.adapters.pdf.runtime_ingest import RuntimePdfReadGateway
from sourcetrace_v2.app.composition.runtime import RuntimeAssembly, build_env_backed_live_litellm_with_searxng_jsonl_runtime
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one v2 minimal flow against the live operator runtime.")
    parser.add_argument("query", help="Seed query for the bounded v2 run.")
    parser.add_argument("--job-id", default=None, help="Optional explicit job id.")
    parser.add_argument("--run-id", default=None, help="Optional explicit run id.")
    parser.add_argument("--artifacts-dir", default=None, help="Optional persistence dir; temp dir when omitted.")
    parser.add_argument("--json-pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base_dir = args.artifacts_dir or tempfile.mkdtemp(prefix="sourcetrace-v2-run-")

    runtime = build_env_backed_live_litellm_with_searxng_jsonl_runtime(
        base_dir=base_dir,
        api_key_env="AZURE_OPENAI_API_KEY",
        base_url_env="AZURE_OPENAI_ENDPOINT",
        api_version_env="AZURE_OPENAI_API_VERSION",
        search_base_url_env="SOURCETRACE_SEARXNG_BASE_URL",
    )
    runtime = RuntimeAssembly(
        config=runtime.config,
        llm=runtime.llm,
        search=runtime.search,
        results=runtime.results,
        receipts=runtime.receipts,
        logger=runtime.logger,
        pdf=RuntimePdfReadGateway(analyzer=build_research_pdf_analyzer(openclaw_pdf_capability)),
    )

    response = handle_run_minimal_flow_request(
        job_id=args.job_id or f"job-{uuid4().hex[:12]}",
        run_id=args.run_id or f"run-{uuid4().hex[:12]}",
        seed_text=args.query,
        runtime=runtime,
    )
    payload = json.loads(response.body)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2 if args.json_pretty else None)
    sys.stdout.write("\n")
    return 0 if response.status_code == 201 else 1


if __name__ == "__main__":
    raise SystemExit(main())
