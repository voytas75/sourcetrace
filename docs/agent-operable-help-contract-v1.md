# Agent-operable help contract v1

## Goal
Define a project SSOT for command, option, parameter, endpoint, and result semantics that should be available both:
1. inside the application through `help` / `--help`, and
2. as project documentation in-repo.

This document is the first semantic contract draft. It is not yet a generated schema layer.

## Scope for v1
Focus on the most important control surfaces an operator or AI agent needs to safely run, inspect, and reason about the local SourceTrace runtime.

Covered in v1:
- `python -m sourcetrace.www_control`
- subcommands: `start`, `stop`, `status`, `wait`, `write-user-unit`
- reusable smoke commands:
  - `python -m sourcetrace.smoke_flow`
  - `python -m sourcetrace.credibility_smoke`
- runtime HTTP endpoints and result semantics:
  - `/api/runtime`
  - `/api/ready`
  - `/api/research/start`
  - `/api/research/run/{job_id}`
  - `/api/research/result/{job_id}`
- high-value result semantics:
  - `core`
  - `supporting`
  - `background`
  - `sources`
  - `official_evidence_verdict`
  - `official_family_trace`

## Design rule
The same semantic contract should drive:
- in-app `--help`
- command-specific help
- option/parameter help
- project docs

## Root command
## `python -m sourcetrace.www_control`
### Intent
Manage the local SourceTrace WWW runtime owned by this repository.

### Scope
Controls the local runtime process only. It is not a general deployment manager.

### Side effects
Depends on subcommand. Can start, stop, inspect, or generate a user unit.

### Key semantic note
`local-launcher` is the important runtime mode for full local behavior. It keeps the richer LLM/runtime wiring. Runtime code changes require explicit restart; there is no autoreload guarantee.

---

## Subcommand: `start`
### Intent
Start the local SourceTrace WWW runtime process.

### Preconditions
- repository checkout exists
- Python environment can import `sourcetrace`
- target host/port are usable
- operator understands that code changes after start are not automatically reloaded

### Side effects
- starts a background runtime process
- writes PID file
- appends to log file
- sets runtime env like `PYTHONPATH`, host, port, data dir, UI dimensions

### Important options
#### `--mode {local-launcher,web}`
- `local-launcher`: preferred for full local runtime behavior and research wiring
- `web`: thinner HTTP front door

#### `--pid-file`
Path to the PID file used for lifecycle management.

#### `--log-file`
Path to the runtime log file.

#### `--host`, `--port`
HTTP bind target used by the runtime.

#### `--width`, `--height`
UI dimension hints injected into runtime env.

### Failure semantics
- may claim already-running when a live PID exists
- may start successfully but still not be ready; readiness must be checked separately

### Agent notes
After `start`, do not claim success until a readiness check has passed.

---

## Subcommand: `stop`
### Intent
Stop the managed local runtime process.

### Preconditions
- PID file exists or runtime was previously started through this control path

### Side effects
- sends `SIGTERM`
- removes PID file

### Failure semantics
- stale PID file is treated as cleanup, not fatal failure

### Agent notes
Use `restart`-style operational behavior as stop + start only when no dedicated restart exists. For this repo, explicit stop/start sequencing may still be needed, but readiness must be rechecked after start.

---

## Subcommand: `status`
### Intent
Inspect whether the managed runtime process exists and whether the endpoint looks ready enough to answer HTTP.

### Output semantics
- `running pid=... ready=yes|no` means process exists and endpoint responded to a simple HTTP probe
- `ready=no` is not equivalent to dead process; it can mean starting, wedged, or partially available

### Agent notes
Treat `status` as a quick state probe, not as full health verification.

---

## Subcommand: `wait`
### Intent
Block until the runtime endpoint starts responding or timeout is reached.

### Preconditions
- runtime is expected to start soon
- host/port are correct

### Important options
#### `--host`, `--port`
Endpoint target to probe.

#### `--timeout-seconds`
Maximum wall-clock wait before failure.

#### `--interval-seconds`
Polling interval between readiness checks.

### Failure semantics
- timeout means endpoint did not become ready in time; it does not fully explain why

### Agent notes
Preferred follow-up after `start` when validating runtime availability.

---

## Subcommand: `write-user-unit`
### Intent
Generate a `systemd --user` unit file for the local runtime.

### Side effects
- writes a unit file to the requested path
- does not itself enable or start the unit

### Important options
#### `--mode`
Determines which runtime entrypoint the generated service will use.

#### `--unit-file`
Output path for the unit file.

### Agent notes
This is documentation/config generation, not service activation.

---

## Command: `python -m sourcetrace.smoke_flow`
### Intent
Run a reusable WWW smoke flow against a running SourceTrace endpoint.

### Important options
#### `--base-url`
Base URL of the target SourceTrace runtime.

#### `--pretty`
Pretty-print result payload.

#### `--expect-claims-min`
Minimum expected claims count for pass/fail logic.

### Agent notes
Use when you need a bounded end-to-end smoke instead of manual endpoint sequencing.

---

## Command: `python -m sourcetrace.credibility_smoke`
### Intent
Run a small credibility API smoke against a running SourceTrace endpoint.

### Important options
- `--base-url`
- `--pretty`

### Agent notes
Use for bounded verification of the credibility-facing path, not the full deep-research runtime.

---

## HTTP endpoint semantics
## `/api/runtime`
### Intent
Return runtime metadata / process-level availability details.

### Agent notes
Useful for confirming the runtime is alive and exposing the expected interface, but not sufficient by itself to prove a full research path is healthy.

## `/api/ready`
### Intent
Return readiness state for the HTTP runtime.

### Agent notes
Use after restart/start before trusting live validation results.

## `/api/research/start`
### Intent
Create a research job shell for an `owner_id` and `query`.

### Side effects
- persists job metadata
- returns job identity

### Agent notes
This does not guarantee the research run has executed yet.

## `/api/research/run/{job_id}`
### Intent
Execute the research job.

### Side effects
- starts the actual research pipeline for the job
- persists events, findings, and final artifact if successful

### Agent notes
Use sequentially for live validation. Parallel starts previously caused misleading failures/timeouts in this local runtime posture.

## `/api/research/result/{job_id}`
### Intent
Fetch the resulting artifact for a completed job.

### Output semantics
Returns the packed result artifact, not raw retrieval state.

### Agent notes
Do not confuse final `sources` projection with raw search-hit order.

---

## Result semantics
## `core`
Best evidence selected for direct answer support after packing.

## `supporting`
Useful corroborating evidence that informs the answer but is not the main evidence basis.

## `background`
Context, collateral, or downgraded evidence kept for traceability but not central to the answer.

## `sources`
User-facing projection of sources shown with the result artifact. This is not the same as raw search-hit order and may be reordered to better reflect official-first/canonical-first outcome quality.

## `official_evidence_verdict`
Semantic verdict used in the official/public-law evidence path.
Expected labels include:
- `primary`
- `supporting`
- `collateral`
- `reject`

## `official_family_trace`
Trace of official-page family consolidation. Used to show which official pages were treated as candidate family members, which were kept canonical, and which were downgraded to collateral.

---

## Environment / runtime notes for later expansion
These need fuller help integration later, but should stay in scope:
- `SOURCETRACE_RUNTIME_PDF_ANALYZER`
- local launcher mode semantics
- data directory semantics
- provider/retry/timeouts where externally configurable
\n## v1 next step
Use this file as SSOT for:
1. root help improvement
2. subcommand help improvement
3. option/parameter help enrichment inside the application

The key implementation rule is: avoid maintaining separate freeform descriptions in code and docs that can drift.
