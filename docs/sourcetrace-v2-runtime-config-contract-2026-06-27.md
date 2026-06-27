# SourceTrace v2 runtime config contract (2026-06-27)

## Verdict
SourceTrace v2 should include a **small first-class runtime configuration layer**.

The goal is not to expose every internal knob.
The goal is to make provider/model/runtime selection easy, explicit, and stable without leaking provider-specific strings into core application logic.

## Design goal
Application and stage code should depend on **logical runtime profiles**, not raw provider/model identifiers.

Good:
- `planning_default`
- `judge_strict`
- `research_fast`
- `research_quality`
- `synthesis_default`

Bad as application truth:
- `azure/gpt-5.4`
- `openai/gpt-4.1`
- `anthropic/claude-...`

Provider/model strings belong to runtime mapping, not to core business logic.

## Contract shape
The config layer should have four levels.

### 1. Profiles
Profiles are the main operator-facing LLM/runtime handles.
They define:
- provider
- model
- mode (`text` / `structured`)
- temperature
- max output tokens
- timeout seconds
- retry policy
- fallback profiles

Example shape:

```yaml
profiles:
  planning_default:
    provider: azure
    model: gpt-5.4
    mode: structured
    temperature: 0.0
    max_output_tokens: 800
    timeout_seconds: 30
    retries: 1
    fallbacks: [planning_fallback]
```

### 2. Feature policy
Feature policy maps business responsibilities to logical profiles.

Example:

```yaml
features:
  deep_research:
    planning_profile: planning_default
    subject_sheet_profile: judge_strict
    query_refinement_profile: research_fast
    evidence_judge_profile: judge_strict
    synthesis_profile: research_quality
```

This lets the app say:
- “Deep Research planning uses `planning_default`”

instead of:
- “Deep Research planning uses provider X model Y with timeout Z”.

### 3. Runtime adapters
Adapters resolve profile settings into concrete provider/runtime execution.

This layer owns:
- provider-specific model naming
- base URLs / endpoints
- API version specifics
- auth/bootstrap requirements
- provider capability checks
- provider fallback routing

### 4. Deployment/bootstrap inputs
Secrets and deployment-specific parameters should stay outside repo-owned business policy.

Examples:
- API keys
- base URLs
- API versions
- deployment toggles
- environment-specific endpoint aliases

These should usually come from env vars or secret stores, not hardcoded repo defaults.

## What should be configurable in v2
Minimum v2 runtime contract should support configuration for:
- provider
- model
- text vs structured mode
- timeout
- retries
- max output tokens
- fallback chain
- feature-to-profile mapping
- search provider selection
- PDF backend selection
- logging level / logging format
- execution diagnostics toggles

## What should not be configurable in v2
Do not try to expose every low-level behavior as config at the start.

Keep these out of early v2 unless a real need appears:
- arbitrary workflow graph editing
- unlimited per-stage freeform overrides
- plugin installation policy via runtime config
- fragile prompt assembly via config strings
- dynamic operator editing of deep internal contracts

V2 should have a **clear config contract**, not a “configuration-shaped programming language.”

## Core rules

### Rule 1 — Core code uses logical names only
Application/stage code should reference logical profiles and feature policy names.
It should not carry provider-specific model names as business truth.

### Rule 2 — Provider specifics stay at the adapter edge
Provider-specific routing belongs in runtime adapter resolution.
Core contracts should stay provider-neutral.

### Rule 3 — Defaults should be explicit and inspectable
Operators should be able to see:
- which profile was selected,
- what provider/model it resolved to,
- which fallback path was used,
- which runtime path executed.

### Rule 4 — Requested config and actual execution must stay separate
Requested profile != actual execution receipt.
If a fallback or alternate provider was used, the execution record must reflect that truth explicitly.

### Rule 5 — Feature policy is a first-class layer
The mapping from feature/stage to runtime profile should be explicit, typed, and inspectable.
That mapping is product policy, not adapter trivia.

## Recommended implementation form
Smallest healthy implementation:
- one typed config schema,
- one loader/validator,
- one profile resolver,
- one feature-policy mapping layer,
- env/secret resolution for deployment/bootstrap inputs.

That is enough for v2 start.

## Suggested operator-facing sections
The config should be easy to reason about.
A practical split would be:
- `profiles`
- `features`
- `providers`
- `search`
- `pdf`
- `logging`
- `diagnostics`

## Logging/config crossover
Logging should be configured through the same runtime contract family, but as its own concern.
At minimum:
- log level
- log format (`text` / `json`)
- sinks/handlers
- redaction policy
- request/job correlation settings

Do not bury logging setup in unrelated runtime code.

## Bottom line
SourceTrace v2 should absolutely add a small easy-configuration layer.
But it should be:
- profile-based,
- provider-neutral at core,
- explicit about feature policy,
- strict about separating requested config from actual execution truth.
