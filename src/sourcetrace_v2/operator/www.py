from __future__ import annotations

import argparse
import json
import time
from os import environ, getpgid, kill, makedirs
from pathlib import Path
from signal import SIGTERM
from subprocess import DEVNULL, PIPE, Popen
from sys import executable
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import uuid4

from sourcetrace.runtime_pdf_backend_openclaw import openclaw_pdf_capability
from sourcetrace.runtime_pdf_ingest import build_research_pdf_analyzer
from sourcetrace_v2.adapters.pdf.runtime_ingest import RuntimePdfReadGateway
from sourcetrace_v2.app.composition.runtime import (
    RuntimeAssembly,
    build_env_backed_live_litellm_with_searxng_jsonl_runtime,
)
from sourcetrace_v2.app.services.http_api import (
    handle_get_persisted_compiled_artifact_request,
    handle_get_persisted_execution_request,
    handle_run_minimal_flow_request,
)
from sourcetrace_v2.projections.api.http import HttpResponse

from wsgiref.simple_server import make_server

DEFAULT_PID_PATH: Final[Path] = Path.home() / ".cache" / "sourcetrace-v2" / "www.pid"
DEFAULT_LOG_PATH: Final[Path] = Path.home() / ".cache" / "sourcetrace-v2" / "www.log"
DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8000
DEFAULT_SYSTEMD_UNIT_PATH: Final[Path] = Path.home() / ".config" / "systemd" / "user" / "sourcetrace-v2-www.service"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _artifacts_dir() -> Path:
    raw = environ.get("SOURCETRACE_RESEARCH_DATA_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _repo_root() / "data" / "research"


def _runtime() -> RuntimeAssembly:
    base_dir = _artifacts_dir()
    runtime = build_env_backed_live_litellm_with_searxng_jsonl_runtime(
        base_dir=base_dir,
        api_key_env="AZURE_OPENAI_API_KEY",
        base_url_env="AZURE_OPENAI_ENDPOINT",
        api_version_env="AZURE_OPENAI_API_VERSION",
        search_base_url_env="SOURCETRACE_SEARXNG_BASE_URL",
    )
    return RuntimeAssembly(
        config=runtime.config,
        llm=runtime.llm,
        search=runtime.search,
        results=runtime.results,
        receipts=runtime.receipts,
        logger=runtime.logger,
        pdf=RuntimePdfReadGateway(analyzer=build_research_pdf_analyzer(openclaw_pdf_capability)),
    )


def _json_body(environ_dict: dict[str, object]) -> dict[str, object]:
    try:
        length = int(str(environ_dict.get("CONTENT_LENGTH") or "0"))
    except ValueError:
        length = 0
    if length <= 0:
        return {}
    raw = environ_dict["wsgi.input"].read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _status_text(status_code: int) -> str:
    return {
        200: "200 OK",
        201: "201 Created",
        202: "202 Accepted",
        400: "400 Bad Request",
        404: "404 Not Found",
        500: "500 Internal Server Error",
    }.get(status_code, f"{status_code} OK")


def _send(start_response, response: HttpResponse):
    start_response(_status_text(response.status_code), [("Content-Type", response.content_type)])
    return [response.body.encode("utf-8")]


def _not_found(start_response):
    start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
    return [b'{"error":"not_found"}']


def _health(start_response):
    start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
    return [b'{"status":"ok","runtime":"sourcetrace_v2"}']


def _home(start_response):
    body = (
        "<html><body><h1>SourceTrace v2</h1>"
        "<p>Minimal v2 operator surface.</p>"
        "<ul>"
        "<li>GET /api/health</li>"
        "<li>POST /api/v2/run</li>"
        "<li>GET /api/v2/execution/&lt;job_id&gt;/&lt;run_id&gt;</li>"
        "<li>GET /api/v2/compiled/&lt;job_id&gt;/&lt;run_id&gt;</li>"
        "</ul></body></html>"
    )
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body.encode("utf-8")]


def build_wsgi_app():
    runtime = _runtime()

    def app(environ_dict, start_response):
        method = environ_dict.get("REQUEST_METHOD", "GET")
        path = environ_dict.get("PATH_INFO", "/")

        if method == "GET" and path == "/":
            return _home(start_response)
        if method == "GET" and path == "/api/health":
            return _health(start_response)
        if method == "GET" and path == "/api/ready":
            return _health(start_response)
        if method == "GET" and path == "/api/runtime":
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            payload = {"runtime": "sourcetrace_v2", "artifacts_dir": str(_artifacts_dir())}
            return [json.dumps(payload).encode("utf-8")]
        if method == "POST" and path == "/api/v2/run":
            payload = _json_body(environ_dict)
            query = str(payload.get("query") or "").strip()
            if not query:
                start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
                return [b'{"error":"query is required"}']
            job_id = str(payload.get("job_id") or f"job-{uuid4().hex[:12]}")
            run_id = str(payload.get("run_id") or f"run-{uuid4().hex[:12]}")
            response = handle_run_minimal_flow_request(job_id=job_id, run_id=run_id, seed_text=query, runtime=runtime)
            return _send(start_response, response)
        if method == "GET" and path.startswith("/api/v2/execution/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) == 5:
                _, _, _, job_id, run_id = parts
                response = handle_get_persisted_execution_request(job_id=job_id, run_id=run_id, runtime=runtime)
                return _send(start_response, response)
        if method == "GET" and path.startswith("/api/v2/compiled/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) == 5:
                _, _, _, job_id, run_id = parts
                response = handle_get_persisted_compiled_artifact_request(job_id=job_id, run_id=run_id, runtime=runtime)
                return _send(start_response, response)
        return _not_found(start_response)

    return app


def run_server(*, host: str, port: int) -> None:
    with make_server(host, port, build_wsgi_app()) as httpd:
        print(f"SourceTrace v2 listening on http://{host}:{port}")
        httpd.serve_forever()


def _process_exists(pid: int) -> bool:
    try:
        getpgid(pid)
    except ProcessLookupError:
        return False
    return True


def _read_pid(pid_path: Path) -> int | None:
    try:
        content = pid_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not content:
        return None
    try:
        return int(content)
    except ValueError:
        return None


def _ensure_parent_dirs(*paths_to_prepare: Path) -> None:
    for target in paths_to_prepare:
        makedirs(target.parent, exist_ok=True)


def _http_ready(host: str, port: int, timeout_seconds: float = 0.5) -> bool:
    url = f"http://{host}:{port}/api/health"
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            return 200 <= response.status < 500
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def _merge_shell_env(base_env: dict[str, str], *, shell_rc: Path | None = None) -> dict[str, str]:
    rc_path = (shell_rc or Path.home() / '.bashrc').expanduser()
    if not rc_path.exists():
        return base_env
    shell = environ.get('SHELL', '/bin/bash')
    command = f"source {rc_path} >/dev/null 2>&1 && env"
    try:
        probe = Popen([shell, '-lc', command], stdout=PIPE, stderr=DEVNULL, text=True, env=base_env)
        stdout, _ = probe.communicate(timeout=10)
    except Exception:
        return base_env
    if probe.returncode != 0 or not stdout:
        return base_env
    merged = dict(base_env)
    for line in stdout.splitlines():
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key:
            merged[key] = value
    return merged


def _build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--pid-file", default=str(DEFAULT_PID_PATH))
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--interval-seconds", type=float, default=0.25)
    parser.add_argument("--unit-file", default=str(DEFAULT_SYSTEMD_UNIT_PATH))
    return parser


def start_main(argv: list[str] | None = None) -> int:
    args = _build_parser("Start SourceTrace v2 WWW in background.").parse_args(argv)
    pid_path = Path(args.pid_file).expanduser()
    log_path = Path(args.log_file).expanduser()
    _ensure_parent_dirs(pid_path, log_path)
    existing_pid = _read_pid(pid_path)
    if existing_pid is not None and _process_exists(existing_pid):
        print(f"SourceTrace v2 WWW already running with PID {existing_pid}.")
        return 0
    repo_root = _repo_root()
    env = _merge_shell_env(environ.copy())
    env["PYTHONPATH"] = str(repo_root / "src")
    env["SOURCETRACE_WWW_HOST"] = args.host
    env["SOURCETRACE_WWW_PORT"] = str(args.port)
    env.setdefault("SOURCETRACE_RESEARCH_DATA_DIR", str(repo_root / "data" / "research"))
    with log_path.open("a", encoding="utf-8") as log_handle:
        process = Popen(
            [executable, "-m", "sourcetrace_v2.operator.www", "serve", "--host", args.host, "--port", str(args.port)],
            cwd=repo_root,
            env=env,
            stdout=log_handle,
            stderr=log_handle,
            stdin=DEVNULL,
            start_new_session=True,
        )
    pid_path.write_text(f"{process.pid}\n", encoding="utf-8")
    print(f"Started SourceTrace v2 WWW with PID {process.pid}.")
    print(f"PID file: {pid_path}")
    print(f"Log file: {log_path}")
    return 0


def stop_main(argv: list[str] | None = None) -> int:
    args = _build_parser("Stop SourceTrace v2 WWW.").parse_args(argv)
    pid_path = Path(args.pid_file).expanduser()
    pid = _read_pid(pid_path)
    if pid is None:
        print(f"No PID file at {pid_path}; nothing to stop.")
        return 0
    if not _process_exists(pid):
        pid_path.unlink(missing_ok=True)
        print(f"Stale PID file removed: {pid_path}")
        return 0
    kill(pid, SIGTERM)
    pid_path.unlink(missing_ok=True)
    print(f"Stopped SourceTrace v2 WWW PID {pid}.")
    return 0


def status_main(argv: list[str] | None = None) -> int:
    args = _build_parser("Status for SourceTrace v2 WWW.").parse_args(argv)
    pid_path = Path(args.pid_file).expanduser()
    pid = _read_pid(pid_path)
    if pid is None:
        print(f"SourceTrace v2 WWW not running (no PID file). expected endpoint=http://{args.host}:{args.port}")
        return 1
    if not _process_exists(pid):
        print(f"SourceTrace v2 WWW not running (stale PID {pid}). expected endpoint=http://{args.host}:{args.port}")
        return 1
    ready = _http_ready(args.host, args.port)
    print(f"SourceTrace v2 WWW running pid={pid} endpoint=http://{args.host}:{args.port} ready={'yes' if ready else 'no'}")
    return 0 if ready else 1


def wait_main(argv: list[str] | None = None) -> int:
    args = _build_parser("Wait for SourceTrace v2 WWW readiness.").parse_args(argv)
    deadline = time.monotonic() + args.timeout_seconds
    while time.monotonic() < deadline:
        if _http_ready(args.host, args.port):
            print(f"SourceTrace v2 WWW ready at http://{args.host}:{args.port}")
            return 0
        time.sleep(args.interval_seconds)
    print(f"SourceTrace v2 WWW not ready before timeout at http://{args.host}:{args.port}")
    return 1


def write_systemd_unit_main(argv: list[str] | None = None) -> int:
    args = _build_parser("Write a systemd user unit for SourceTrace v2 WWW.").parse_args(argv)
    unit_path = Path(args.unit_file).expanduser()
    _ensure_parent_dirs(unit_path)
    repo_root = _repo_root()
    unit_text = f"""[Unit]
Description=SourceTrace v2 WWW
After=network.target

[Service]
Type=forking
WorkingDirectory={repo_root}
Environment=PYTHONPATH={repo_root}/src
ExecStart=/bin/bash -lc 'source ~/.bashrc && cd {repo_root} && {repo_root}/.venv/bin/sourcetrace-www-start'
ExecStop=/bin/bash -lc 'cd {repo_root} && {repo_root}/.venv/bin/sourcetrace-www-stop'
PIDFile=%h/.cache/sourcetrace-v2/www.pid
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
"""
    unit_path.write_text(unit_text, encoding="utf-8")
    print(f"Wrote systemd --user unit: {unit_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SourceTrace v2 WWW runtime and lifecycle.")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve")
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)

    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("status")
    sub.add_parser("wait")
    sub.add_parser("write-user-unit")

    args, rest = parser.parse_known_args(argv)
    if args.command == "serve":
        run_server(host=args.host, port=args.port)
        return 0
    if args.command == "start":
        return start_main(rest)
    if args.command == "stop":
        return stop_main(rest)
    if args.command == "status":
        return status_main(rest)
    if args.command == "wait":
        return wait_main(rest)
    if args.command == "write-user-unit":
        return write_systemd_unit_main(rest)
    parser.print_usage()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
