"""Canonical v2 app-service path:

- execution.py -> execute_minimal_research_flow
- persistence.py -> persist_execution_outcome
- readback.py -> load_persisted_execution_view
- run_use_case.py -> run_and_persist_minimal_flow
- http_api.py -> transport-facing handlers

Files with *_demo.py are temporary scaffolding helpers and are not the canonical v2 path.
"""
