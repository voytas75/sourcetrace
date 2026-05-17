from pathlib import Path


def test_expected_package_directories_exist() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "sourcetrace"
    expected = ["domain", "application", "pipeline", "storage", "web", "config", "shared"]
    for name in expected:
        assert (root / name).is_dir(), name


def test_application_contract_module_exists() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "sourcetrace" / "application"
    assert (root / "__init__.py").is_file()
    assert (root / "verification.py").is_file()
