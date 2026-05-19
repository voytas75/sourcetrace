"""Start/stop/status helpers for the repo-owned local web runtime."""

from __future__ import annotations

import argparse
import time
from os import environ, getpgid, kill, makedirs
from pathlib import Path
from signal import SIGTERM
from subprocess import DEVNULL, Popen
from sys import executable
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

DEFAULT_PID_PATH: Final[Path] = Path.home() / ".cache" / "sourcetrace" / "www.pid"
DEFAULT_LOG_PATH: Final[Path] = Path.home() / ".cache" / "sourcetrace" / "www.log"
DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8000
DEFAULT_SYSTEMD_UNIT_PATH: Final[Path] = Path.home() / ".config" / "systemd" / "user" / "sourcetrace-www.service"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_pythonpath() -> str:
    return str(_repo_root() / "src")


def _resolve_runtime_command(args: argparse.Namespace) -> list[str]:
    if args.mode == "local-launcher":
        return [executable, "-m", "sourcetrace.local_launcher"]
    return [executable, "-m", "sourcetrace.web"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start or stop the Sourcetrace WWW runtime.")
    parser.add_argument(
        "--mode",
        choices=("local-launcher", "web"),
        default="local-launcher",
        help="Runtime entrypoint to manage. local-launcher keeps LLM credibility wiring; web is the thinner HTTP front door.",
    )
    parser.add_argument("--pid-file", default=str(DEFAULT_PID_PATH))
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


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


def _process_exists(pid: int) -> bool:
    try:
        getpgid(pid)
    except ProcessLookupError:
        return False
    return True


def _ensure_parent_dirs(*paths_to_prepare: Path) -> None:
    for target in paths_to_prepare:
        makedirs(target.parent, exist_ok=True)


def _http_ready(host: str, port: int, timeout_seconds: float = 0.5) -> bool:
    url = f"http://{host}:{port}/"
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            return 200 <= response.status < 500
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def _status_line(pid: int | None, host: str, port: int) -> tuple[str, int]:
    if pid is None:
        return (f"Sourcetrace WWW not running (no PID file). expected endpoint=http://{host}:{port}", 1)
    if not _process_exists(pid):
        return (f"Sourcetrace WWW not running (stale PID {pid}). expected endpoint=http://{host}:{port}", 1)
    ready = _http_ready(host, port)
    return (f"Sourcetrace WWW running pid={pid} endpoint=http://{host}:{port} ready={'yes' if ready else 'no'}", 0)


def start_main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    pid_path = Path(args.pid_file).expanduser()
    log_path = Path(args.log_file).expanduser()

    _ensure_parent_dirs(pid_path, log_path)

    existing_pid = _read_pid(pid_path)
    if existing_pid is not None and _process_exists(existing_pid):
        print(f"Sourcetrace WWW already running with PID {existing_pid} ({args.mode}).")
        return 0

    repo_root = _repo_root()
    env = environ.copy()
    env["PYTHONPATH"] = _default_pythonpath()
    env["SOURCETRACE_WWW_HOST"] = args.host
    env["SOURCETRACE_WWW_PORT"] = str(args.port)

    with log_path.open("a", encoding="utf-8") as log_handle:
        process = Popen(
            _resolve_runtime_command(args),
            cwd=repo_root,
            env=env,
            stdout=log_handle,
            stderr=log_handle,
            stdin=DEVNULL,
            start_new_session=True,
        )

    pid_path.write_text(f"{process.pid}\n", encoding="utf-8")
    print(f"Started Sourcetrace WWW ({args.mode}) with PID {process.pid}.")
    print(f"PID file: {pid_path}")
    print(f"Log file: {log_path}")
    return 0


def stop_main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
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
    print(f"Stopped Sourcetrace WWW PID {pid}.")
    return 0


def status_main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    pid_path = Path(args.pid_file).expanduser()
    pid = _read_pid(pid_path)
    line, exit_code = _status_line(pid, args.host, args.port)
    print(line)
    return exit_code


def wait_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wait until the Sourcetrace WWW endpoint responds.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--interval-seconds", type=float, default=0.25)
    args = parser.parse_args(argv)

    deadline = time.monotonic() + args.timeout_seconds
    while time.monotonic() < deadline:
        if _http_ready(args.host, args.port):
            print(f"Sourcetrace WWW ready at http://{args.host}:{args.port}")
            return 0
        time.sleep(args.interval_seconds)
    print(f"Sourcetrace WWW not ready before timeout at http://{args.host}:{args.port}")
    return 1


def render_systemd_user_unit(mode: str = "local-launcher") -> str:
    repo_root = _repo_root()
    if mode == "local-launcher":
        exec_start = f"{repo_root}/.venv/bin/sourcetrace-www-start --mode local-launcher"
    else:
        exec_start = f"{repo_root}/.venv/bin/sourcetrace-www-start --mode web"
    exec_stop = f"{repo_root}/.venv/bin/sourcetrace-www-stop --mode {mode}"
    return f"""[Unit]
Description=SourceTrace WWW ({mode})
After=network.target

[Service]
Type=forking
WorkingDirectory={repo_root}
Environment=PYTHONPATH={repo_root}/src
ExecStart=/bin/bash -lc 'source ~/.bashrc && cd {repo_root} && {exec_start}'
ExecStop=/bin/bash -lc 'cd {repo_root} && {exec_stop}'
PIDFile=%h/.cache/sourcetrace/www.pid
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
"""


def write_systemd_unit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a systemd --user unit for Sourcetrace WWW.")
    parser.add_argument("--mode", choices=("local-launcher", "web"), default="local-launcher")
    parser.add_argument("--unit-file", default=str(DEFAULT_SYSTEMD_UNIT_PATH))
    args = parser.parse_args(argv)
    unit_path = Path(args.unit_file).expanduser()
    _ensure_parent_dirs(unit_path)
    unit_path.write_text(render_systemd_user_unit(mode=args.mode), encoding="utf-8")
    print(f"Wrote systemd --user unit: {unit_path}")
    return 0


__all__ = [
    "render_systemd_user_unit",
    "start_main",
    "status_main",
    "stop_main",
    "wait_main",
    "write_systemd_unit_main",
]
