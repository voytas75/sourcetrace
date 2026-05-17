from pathlib import Path


def test_expected_package_directories_exist() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "sourcetrace"
    expected = ["domain", "application", "pipeline", "storage", "web", "config", "shared"]
    for name in expected:
        assert (root / name).is_dir(), name
