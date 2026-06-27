from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.runtime.config.resolver import RuntimeProfileNotFoundError, resolve_profile


def test_default_runtime_profiles_are_resolvable() -> None:
    config = build_default_runtime_config()

    profile = resolve_profile(config, "planning_default")

    assert profile.provider == "azure"
    assert profile.model == "gpt-5.4"
    assert profile.mode == "structured"


def test_missing_profile_raises_explicit_error() -> None:
    config = build_default_runtime_config()

    try:
        resolve_profile(config, "does_not_exist")
    except RuntimeProfileNotFoundError as exc:
        assert str(exc).strip("'") == "does_not_exist"
    else:
        raise AssertionError("expected RuntimeProfileNotFoundError")
