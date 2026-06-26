"""Start/stop/status helpers for the repo-owned local web runtime."""

from __future__ import annotations

import argparse
import time
from os import environ, getpgid, kill, makedirs
from pathlib import Path
from signal import SIGTERM
from subprocess import DEVNULL, PIPE, Popen
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
    return Path(__file__).resolve().parents[3]


def _default_pythonpath() -> str:
    return str(_repo_root() / "src")


def _resolve_runtime_command(args: argparse.Namespace) -> list[str]:
    if args.mode == "local-launcher":
        return [executable, "-m", "sourcetrace.local_launcher"]
    return [executable, "-m", "sourcetrace.web"]


def _build_runtime_parser(*, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--mode",
        choices=("local-launcher", "web"),
        default="local-launcher",
        help="Runtime entrypoint to manage. Use local-launcher for full local research/runtime wiring; use web for the thinner HTTP front door.",
    )
    parser.add_argument("--pid-file", default=str(DEFAULT_PID_PATH), help="PID file used for lifecycle control of the managed runtime process.")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_PATH), help="Log file where stdout/stderr from the managed runtime are appended.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="HTTP bind host for the runtime or readiness probe target, depending on subcommand.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="HTTP bind port for the runtime or readiness probe target, depending on subcommand.")
    parser.add_argument("--width", type=int, default=1600, help="UI width hint injected into runtime env when starting the local runtime.")
    parser.add_argument("--height", type=int, default=1100, help="UI height hint injected into runtime env when starting the local runtime.")
    return parser


def _build_start_parser() -> argparse.ArgumentParser:
    return _build_runtime_parser(description="Start the Sourcetrace WWW runtime in the background. This writes PID/log files and requires a later readiness check; runtime code changes are not autoreloaded.")


def _build_stop_parser() -> argparse.ArgumentParser:
    return _build_runtime_parser(description="Stop the managed Sourcetrace WWW runtime by PID file and SIGTERM. Safe against stale PID files.")


def _build_status_parser() -> argparse.ArgumentParser:
    return _build_runtime_parser(description="Show whether the managed Sourcetrace WWW process exists and whether the endpoint is responding. This is a quick state probe, not a full health guarantee.")


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


def _merge_shell_env(base_env: dict[str, str], *, shell_rc: Path | None = None) -> dict[str, str]:
    rc_path = (shell_rc or Path.home() / '.bashrc').expanduser()
    if not rc_path.exists():
        return base_env
    shell = environ.get('SHELL', '/bin/bash')
    command = f"source {rc_path} >/dev/null 2>&1 && env"
    try:
        probe = Popen(
            [shell, '-lc', command],
            stdout=PIPE,
            stderr=DEVNULL,
            text=True,
            env=base_env,
        )
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
        if not key:
            continue
        merged[key] = value
    return merged


def start_main(argv: list[str] | None = None) -> int:
    parser = _build_start_parser()
    args = parser.parse_args(argv)
    pid_path = Path(args.pid_file).expanduser()
    log_path = Path(args.log_file).expanduser()

    _ensure_parent_dirs(pid_path, log_path)

    existing_pid = _read_pid(pid_path)
    if existing_pid is not None and _process_exists(existing_pid):
        print(f"Sourcetrace WWW already running with PID {existing_pid} ({args.mode}).")
        return 0

    repo_root = _repo_root()
    env = _merge_shell_env(environ.copy())
    env["PYTHONPATH"] = _default_pythonpath()
    env["SOURCETRACE_WWW_HOST"] = args.host
    env["SOURCETRACE_WWW_PORT"] = str(args.port)
    env["SOURCETRACE_RESEARCH_DATA_DIR"] = str(repo_root / "data" / "research")
    env["SOURCETRACE_UI_SCREEN_WIDTH"] = str(args.width)
    env["SOURCETRACE_UI_SCREEN_HEIGHT"] = str(args.height)

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
    parser = _build_stop_parser()
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
    parser = _build_status_parser()
    args = parser.parse_args(argv)
    pid_path = Path(args.pid_file).expanduser()
    pid = _read_pid(pid_path)
    line, exit_code = _status_line(pid, args.host, args.port)
    print(line)
    return exit_code


def _build_wait_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Wait until the Sourcetrace WWW endpoint responds. Use this after start/restart before trusting live validation results.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to probe for HTTP readiness.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to probe for HTTP readiness.")
    parser.add_argument("--timeout-seconds", type=float, default=15.0, help="Maximum wall-clock wait before failing readiness.")
    parser.add_argument("--interval-seconds", type=float, default=0.25, help="Polling interval between readiness probes.")
    return parser


def wait_main(argv: list[str] | None = None) -> int:
    parser = _build_wait_parser()
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


def _build_write_user_unit_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write a systemd --user unit file for Sourcetrace WWW. This generates the file only; it does not enable or start the service.")
    parser.add_argument("--mode", choices=("local-launcher", "web"), default="local-launcher", help="Runtime entrypoint the generated user unit should manage.")
    parser.add_argument("--unit-file", default=str(DEFAULT_SYSTEMD_UNIT_PATH), help="Destination path for the generated systemd --user unit.")
    return parser


def write_systemd_unit_main(argv: list[str] | None = None) -> int:
    parser = _build_write_user_unit_parser()
    args = parser.parse_args(argv)
    unit_path = Path(args.unit_file).expanduser()
    _ensure_parent_dirs(unit_path)
    unit_path.write_text(render_systemd_user_unit(mode=args.mode), encoding="utf-8")
    print(f"Wrote systemd --user unit: {unit_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage the Sourcetrace WWW runtime. Use subcommand help for lifecycle semantics, readiness behavior, and unit-file generation details.")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start the background runtime and write PID/log files.", description=_build_start_parser().description)
    for action in _build_start_parser()._actions[1:]:
        start_parser._add_action(action)

    stop_parser = subparsers.add_parser("stop", help="Stop the managed runtime using the PID file.", description=_build_stop_parser().description)
    for action in _build_stop_parser()._actions[1:]:
        stop_parser._add_action(action)

    status_parser = subparsers.add_parser("status", help="Show process presence and basic endpoint readiness state.", description=_build_status_parser().description)
    for action in _build_status_parser()._actions[1:]:
        status_parser._add_action(action)

    wait_parser = subparsers.add_parser("wait", help="Block until the runtime HTTP endpoint responds or timeout is reached.", description=_build_wait_parser().description)
    for action in _build_wait_parser()._actions[1:]:
        wait_parser._add_action(action)

    unit_parser = subparsers.add_parser("write-user-unit", help="Generate a systemd --user unit file for the runtime.", description=_build_write_user_unit_parser().description)
    for action in _build_write_user_unit_parser()._actions[1:]:
        unit_parser._add_action(action)

    args = parser.parse_args(argv)
    if args.command == "start":
        return start_main(argv[1:] if argv else None)
    if args.command == "stop":
        return stop_main(argv[1:] if argv else None)
    if args.command == "status":
        return status_main(argv[1:] if argv else None)
    if args.command == "wait":
        return wait_main(argv[1:] if argv else None)
    if args.command == "write-user-unit":
        return write_systemd_unit_main(argv[1:] if argv else None)

    parser.print_usage()
    return 2


__all__ = [
    "main",
    "render_systemd_user_unit",
    "start_main",
    "status_main",
    "stop_main",
    "wait_main",
    "write_systemd_unit_main",
]
