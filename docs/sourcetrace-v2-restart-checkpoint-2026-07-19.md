# SourceTrace active-v2 restart checkpoint — 2026-07-19

Status: current active-v2 entrypoint / restart guide  
Scope: local repository posture only; no live provider, service, or deployment validation

## Start here

`sourcetrace_v2` is the active implementation and default local runtime surface. The primary entrypoint is:

```bash
PYTHONPATH=src ./.venv/bin/python -m sourcetrace_v2.operator.www serve --host 127.0.0.1 --port 8000
```

For the managed local wrapper, use the `start`, `wait`, `status`, and `stop` subcommands documented in [README-dev](../README-dev.md#runtime-commands). Do not treat the legacy `sourcetrace.web` or old Deep Research runtime path as the default forward path.

## Verified repository posture

- The default runtime command and installed console scripts target `sourcetrace_v2.operator.www`.
- The legacy `sourcetrace.www_control` wait wrapper imports and dispatches consistently again.
- Dependency resolution was refreshed locally with `uv lock --offline`; the lock file now represents the base `pdfplumber` dependency declared in `pyproject.toml`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider` completed with `665 passed, 3 xfailed`.
- `uv sync --locked --offline --dry-run --dev --extra dev` completed successfully against the refreshed lock.
- Trust no longer infers jurisdiction mismatch from URL/title anchors. `jurisdiction_mixed_selected_institutional_pair` now requires explicit selected-evidence `trust_metadata`; absent metadata is treated as unknown rather than guessed.
- Retrieval relevance treats search-engine constraints as corpus selection rather than semantic support, and normalizes bounded lexical variants before target scoring; see [retrieval semantic-scoring contract v1](retrieval-semantic-scoring-contract-v1-2026-07-19.md).
- Retrieval readback now preserves the shaped pre-trim candidate pool and surfaces an explicit semantic-fit guard. Only explicit upstream pre-trim insufficiency projects `retrieval_insufficient_semantic_fit`; trimmed/selected evidence behavior remains unchanged.

This checkpoint deliberately does **not** claim a live Azure OpenAI or SearxNG run. It also does not start, stop, or alter any service or systemd unit.

## Current limitations

- The HTTP/operator surface is intentionally minimal and local-first, not a hosted production deployment.
- Live v2 execution still requires valid Azure OpenAI and SearxNG configuration; retrieval quality, selected evidence quality, and trust alignment must be assessed against a live run when that work is authorized.
- Legacy v1 / Deep Research documents remain useful historical and migration references, but they are not current runtime instructions.
- The architecture SSOT remains a product-baseline document, not a current implementation/runbook SSOT.

## Next action

When live-provider validation is explicitly in scope, configure the required local environment and run one bounded v2 operator smoke through the documented `/api/v2/run` and readback paths. Keep that validation separate from this repository-integrity checkpoint.

## Related documents

- [README-dev runtime commands](../README-dev.md#runtime-commands)
- [v2 trust-metadata contract](trust-metadata-contract-v2-2026-07-19.md)
- [v2 retrieval semantic-scoring contract](retrieval-semantic-scoring-contract-v1-2026-07-19.md)
- [v2 retrieval semantic-fit guard](retrieval-semantic-fit-guard-v1-2026-07-19.md)
- [v2 closure / packaging checkpoint](sourcetrace-v2-closure-packaging-checkpoint-2026-06-27.md)
- [v2 docs posture](sourcetrace-v2-docs-posture-2026-06-27.md)
- [Architecture SSOT / legacy product baseline](architecture-ssot.md)
- [Legacy Deep Research checkpoint](deep-research-status-checkpoint-2026-06-22.md)
