import ast
import importlib
import inspect
from ast import ImportFrom
from pathlib import Path


def test_from_imports_only_reference_classes_or_modules():
    root = Path(__file__).resolve().parents[2]
    paths = [
        *root.joinpath("app").rglob("*.py"),
        root / "extension" / "build.py",
    ]
    violations = []
    for path in paths:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ImportFrom) or node.level:
                continue
            if not node.module or node.module == "__future__":
                continue
            module = importlib.import_module(node.module)
            for alias in node.names:
                symbol = getattr(module, alias.name)
                if not (inspect.isclass(symbol) or inspect.ismodule(symbol)):
                    violations.append(
                        f"{path.relative_to(root)}:{node.lineno}: "
                        f"access {alias.name} through {node.module}"
                    )
    assert not violations, "\n".join(violations)
