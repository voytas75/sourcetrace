"""Local runnable front door for the SourceTrace stdlib WSGI demo server."""

from sourcetrace.web import run_local_server


def main() -> int:
    runtime = run_local_server()
    try:
        runtime.server.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        runtime.server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
