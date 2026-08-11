from collections.abc import Callable

import pytest

from sourcetrace_v2.runtime.bootstrap import litellm_client

_COMPLETION_ATTRIBUTE = "completion"


class _ModelDumpResponse:
    def model_dump(self) -> dict[str, object]:
        return {"content": "model-dump"}


class _DictResponse:
    def dict(self) -> dict[str, object]:
        return {"content": "legacy-dict"}


def _model_dump_completion(**_: object) -> object:
    return _ModelDumpResponse()


def _legacy_dict_completion(**_: object) -> object:
    return _DictResponse()


def _unsupported_completion(**_: object) -> object:
    return object()


def _replace_completion(completion: Callable[..., object]) -> object:
    previous = vars(litellm_client.litellm)[_COMPLETION_ATTRIBUTE]
    setattr(litellm_client.litellm, _COMPLETION_ATTRIBUTE, completion)
    return previous


def _restore_completion(previous: object) -> None:
    setattr(litellm_client.litellm, _COMPLETION_ATTRIBUTE, previous)


def test_litellm_completion_accepts_model_dump_response() -> None:
    previous = _replace_completion(_model_dump_completion)
    try:
        assert litellm_client.litellm_completion(model="example") == {
            "content": "model-dump"
        }
    finally:
        _restore_completion(previous)


def test_litellm_completion_accepts_legacy_dict_response() -> None:
    previous = _replace_completion(_legacy_dict_completion)
    try:
        assert litellm_client.litellm_completion(model="example") == {
            "content": "legacy-dict"
        }
    finally:
        _restore_completion(previous)


def test_litellm_completion_rejects_unsupported_response() -> None:
    previous = _replace_completion(_unsupported_completion)
    try:
        with pytest.raises(
            TypeError, match="unsupported LiteLLM response type: object"
        ):
            litellm_client.litellm_completion(model="example")
    finally:
        _restore_completion(previous)
