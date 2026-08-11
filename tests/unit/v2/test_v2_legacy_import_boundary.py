import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_active_v2_source_and_tests_do_not_import_legacy_sourcetrace() -> None:
    legacy_imports: list[str] = []
    for relative_root in ("src/sourcetrace_v2", "tests/unit/v2"):
        for path in (ROOT / relative_root).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and (
                        node.module == "sourcetrace"
                        or node.module.startswith("sourcetrace.")
                    )
                ):
                    legacy_imports.append(f"{path.relative_to(ROOT)}:{node.module}")
                elif isinstance(node, ast.Import):
                    legacy_imports.extend(
                        f"{path.relative_to(ROOT)}:{alias.name}"
                        for alias in node.names
                        if alias.name == "sourcetrace"
                        or alias.name.startswith("sourcetrace.")
                    )
    assert legacy_imports == []
