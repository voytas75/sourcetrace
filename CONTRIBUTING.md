# Contributing

SourceTrace is not open for broad external contribution yet.

For now, treat this repository as owner-operated and local-first.

## Current contribution stance
- default mode: private development
- issues, plans, and research notes may exist only locally and may not appear in the remote repo
- product and architecture truth should be updated in tracked SSOT docs before larger implementation changes
- keep changes bounded and verifiable

## Local setup
```bash
uv sync --dev --extra dev
uv run pytest -q
```

## Change rules
- prefer small slices over broad refactors
- preserve evidence-first boundaries
- do not commit secrets, datasets, generated runtime state, or local process notes
- treat README and tracked docs as GitHub-facing surfaces; avoid references to local-only artifacts

## Before proposing a change
1. confirm scope against tracked docs
2. run the smallest relevant test slice
3. update README / docs only when verified behavior changed
4. keep uncertain claims marked as `do weryfikacji`
