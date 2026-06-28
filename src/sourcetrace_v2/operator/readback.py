from __future__ import annotations

import argparse
import json
import sys

from sourcetrace_v2.app.composition.runtime import build_stubbed_jsonl_runtime
from sourcetrace_v2.app.services.compiled_readback import load_persisted_compiled_artifact_view
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.projections.api.compiled_readback import project_persisted_compiled_artifact_view
from sourcetrace_v2.projections.api.readback import project_persisted_execution_view


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read one persisted v2 run view from JSONL storage.")
    parser.add_argument("mode", choices=("execution", "compiled"), help="Which persisted view to load.")
    parser.add_argument("job_id", help="Persisted job id.")
    parser.add_argument("run_id", help="Persisted run id.")
    parser.add_argument("--artifacts-dir", required=True, help="JSONL artifacts base dir.")
    parser.add_argument("--json-pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime = build_stubbed_jsonl_runtime(base_dir=args.artifacts_dir)

    if args.mode == "execution":
        view = load_persisted_execution_view(
            job_id=args.job_id,
            run_id=args.run_id,
            results=runtime.results,
            receipts=runtime.receipts,
        )
        payload = project_persisted_execution_view(view=view)
        status = view.status.value
    else:
        view = load_persisted_compiled_artifact_view(
            job_id=args.job_id,
            run_id=args.run_id,
            results=runtime.results,
        )
        payload = project_persisted_compiled_artifact_view(view=view)
        status = view.status.value

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2 if args.json_pretty else None)
    sys.stdout.write("\n")
    return 0 if status == "found" else 1


if __name__ == "__main__":
    raise SystemExit(main())
