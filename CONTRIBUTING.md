# Contributing

SourceTrace is still primarily owner-operated, but the repository is being shaped into a clearer public-facing surface.

## Current contribution stance
- the project currently prefers bounded, reviewable changes over broad feature pushes
- product and architecture truth should be updated in tracked SSOT docs before larger implementation changes
- some issues, plans, and research notes may remain outside the repo or be summarized rather than mirrored in full
- contribution posture should stay aligned with verified behavior and current product boundaries

## Public vs developer-facing docs
- `README.md` is the public-facing repo entry point
- `README-dev.md` holds developer/operator setup, runtime variants, command references, and development constraints
- tracked SSOT docs under `docs/` should carry durable product and architecture truth

## Local setup
```bash
uv sync --dev --extra dev
uv run pytest -q
```

## What to keep in mind
- prefer small slices over broad refactors
- preserve evidence-first boundaries
- do not commit secrets, datasets, generated runtime state, or local process notes
- treat `README.md` and tracked docs as GitHub-facing surfaces
- keep uncertain claims marked as `do weryfikacji` until verified

## Before proposing a change
1. confirm scope against tracked docs
2. run the smallest relevant verification slice
3. update `README.md` when the public-facing product framing or verified behavior changed
4. update `README-dev.md` when the change affects setup, runtime commands, or operator/developer guidance
5. keep tracked docs consistent with the verified state
