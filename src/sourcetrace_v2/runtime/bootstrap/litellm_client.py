from __future__ import annotations

from typing import Any

import litellm


def litellm_completion(**kwargs: Any) -> dict[str, Any]:
    response = litellm.completion(**kwargs)
    if hasattr(response, "model_dump"):
        return response.model_dump()  # pydantic v2
    if hasattr(response, "dict"):
        return response.dict()  # pragma: no cover - compatibility
    if isinstance(response, dict):
        return response
    raise TypeError(f"unsupported LiteLLM response type: {type(response).__name__}")
