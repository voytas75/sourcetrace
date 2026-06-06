# Contributing

SourceTrace is not open to broad public contribution yet.

At this stage the repository should be read as owner-operated, local-first, and still being shaped into a clearer external surface.

## Current contribution stance
- default mode: private development
- issues, plans, and research notes may exist only locally and may not appear in the remote repo
- product and architecture truth should be updated in tracked SSOT docs before larger implementation changes
- changes should stay bounded, reviewable, and verifiable

## Local setup
```bash
uv sync --dev --extra dev
uv run pytest -q
```

## What to keep in mind
- prefer small slices over broad refactors
- preserve evidence-first boundaries
- do not commit secrets, datasets, generated runtime state, or local process notes
- treat `README.md` and tracked docs as GitHub-facing surfaces; avoid references to local-only artifacts

## Before proposing a change
1. confirm scope against tracked docs
2. run the smallest relevant verification slice
3. update `README.md` or tracked docs only when verified behavior changed
4. keep uncertain claims marked as `do weryfikacji`
