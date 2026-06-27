# SourceTrace v2 native logging layer + JSON formatter (2026-06-27)

## Verdict
Yes — SourceTrace v2 should include a **first-class native logging layer**, and it should support **structured JSON logging** from the start.

This should not be treated as a minor implementation detail.
Logging is one of the operator-facing and diagnostics-facing layers of the system.

But it must stay clearly separated from execution receipts:
- receipts are typed execution truth,
- logs are diagnostic narration and operational observability.

Both matter.
They should not be collapsed into one thing.

## Goal
Provide a native logging layer that is:
- easy to configure,
- usable in local development,
- suitable for structured ingestion and filtering,
- correlation-friendly,
- safe for operator use,
- compatible with append-only execution receipt truth.

## Why v2 should add this early
A growing system without a coherent native logging layer usually degrades into:
- print-style debugging,
- inconsistent logger names,
- mixed text formats,
- missing correlation fields,
- hard-to-filter runtime output,
- accidental leakage of sensitive payloads.

Adding native logging early gives the v2 spine a healthier operational boundary.

## Separation of concerns

### Execution receipts are for truth
Receipts should answer:
- what actually ran,
- what usage/provenance/degradation occurred,
- what artifacts were emitted.

### Logs are for diagnostics and operational narration
Logs should answer:
- what the system is doing,
- what path it took,
- what warning or failure condition occurred,
- what context helps debug the issue.

Logs may reference receipt IDs, job IDs, run IDs, and stage IDs.
But logs should not be the only durable source for execution truth.

## Required v2 logging properties

### 1. Native logger hierarchy
Use a consistent app logger namespace, for example:
- `sourcetrace.app`
- `sourcetrace.runtime`
- `sourcetrace.llm`
- `sourcetrace.search`
- `sourcetrace.pdf`
- `sourcetrace.web`
- `sourcetrace.storage`\n
This should be intentional, not accidental.

### 2. Structured JSON formatter
V2 should ship with a JSON formatter as a supported first-class output format.

Minimum structured fields:
- timestamp
- level
- logger
- message
- event_name
- job_id
- run_id
- stage_id
- call_site
- request_id
- receipt_id
- provider
- model
- feature
- exception type/message when relevant

Optional fields can expand later, but these are the useful starting spine.

### 3. Text formatter for local readability
JSON should not be the only mode.
For local development, a concise human-readable text formatter is still useful.

V2 should support at least:
- `text`
- `json`

through the same logging config layer.

### 4. Correlation-first posture
Logs should make it easy to follow one request/job/run/stage path across the system.

At minimum, support correlation keys for:
- request
- job
- run
- stage
- receipt

### 5. Redaction/safety policy
The logging layer should have explicit rules for what must not be logged by default.
Examples:
- API keys
- auth headers
- raw full prompts unless explicitly allowed
- sensitive provider payloads
- raw document text dumps unless in a bounded debug mode

### 6. Stable configuration surface
Logging should be configurable through the same v2 runtime config family.
Minimum knobs:
- log level
- format (`text` / `json`)
- sink/handler selection
- correlation enabled/disabled
- debug payload mode
- redaction posture

## JSON formatter posture
The JSON formatter should be simple and boring.

It should:
- emit one JSON object per line,
- keep core fields stable,
- allow extra structured context,
- avoid giant nested blobs by default,
- remain easy to parse by local tools and collectors.

Do not build a highly magical formatter.
The goal is reliable structured output.

## Suggested event classes for logs
Useful log event families:
- `job.accepted`
- `job.started`
- `stage.started`
- `stage.completed`
- `stage.failed`
- `llm.call.started`
- `llm.call.completed`
- `llm.call.degraded`
- `artifact.emitted`
- `projection.rendered`
- `config.profile_resolved`
- `runtime.fallback_used`

These are log event names, not replacements for typed receipts.

## Config example shape
A practical v2 config section might look like:

```yaml
logging:
  level: INFO
  format: json
  redact_sensitive: true
  include_correlation: true
  handlers:
    - console
```

And optionally:

```yaml
logging:
  level: DEBUG
  format: text
  redact_sensitive: true
  include_correlation: true
  handlers:
    - console
```

## Relationship to receipts and projections
Recommended layering:
- logger emits structured diagnostics,
- receipt collector emits typed execution truth,
- API/UI/diagnostics project from receipts/artifacts,
- logs stay useful for debugging and operations but not as the only truth model.

This keeps the system inspectable without turning logs into the database.

## What should stay out of early v2 logging
Avoid overbuilding early:
- no heavy custom observability platform,
- no huge schema zoo,
- no complex remote log transport requirement,
- no logging framework that becomes harder to understand than the app.

Keep it native, structured, and correlated.

## Smallest healthy implementation
The smallest healthy v2 logging layer is:
- native Python logger setup,
- one text formatter,
- one JSON formatter,
- one correlation context helper,
- one redaction helper,
- config-driven selection from the runtime config layer.

That is enough to make logging a real architecture layer rather than an afterthought.

## Bottom line
SourceTrace v2 should include a native logging layer with JSONFormatter support from the start.

That gives the system:
- better operator visibility,
- better diagnostics,
- safer structured output,
- easier integration with future tooling,

while preserving the more important rule:
**logs support the truth model; they do not replace it.**
