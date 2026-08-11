from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, cast

import litellm


class _ModelDumpResponse(Protocol):
    def model_dump(self) -> dict[str, Any]: ...


class _DictResponse(Protocol):
    def dict(self) -> dict[str, Any]: ...


def litellm_completion(**kwargs: Any) -> dict[str, Any]:
    completion = cast(Callable[..., object], vars(litellm)["completion"])
    response = completion(**kwargs)
    if hasattr(response, "model_dump"):
        return cast(_ModelDumpResponse, response).model_dump()  # pydantic v2
    if hasattr(response, "dict"):
        return cast(_DictResponse, response).dict()  # pragma: no cover - compatibility
    if isinstance(response, dict):
        return cast(dict[str, Any], response)
    raise TypeError(f"unsupported LiteLLM response type: {type(response).__name__}")
