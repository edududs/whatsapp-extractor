"""The core may import only the stdlib, pydantic and the layers beneath it."""

from __future__ import annotations

import ast
import sys
from importlib.util import resolve_name
from pathlib import Path

import pytest

ROOT = "whatsapp_extractor"
PACKAGE = Path(__file__).resolve().parents[1] / "src" / ROOT
ALLOWED = {
    "domain": {"pydantic", f"{ROOT}.domain"},
    "application": {"pydantic", f"{ROOT}.domain", f"{ROOT}.application"},
}


def violations(source: str, module: str, layer: str) -> list[str]:
    package = module.rsplit(".", 1)[0]
    imported: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            name = "." * node.level + (node.module or "")
            imported.append(resolve_name(name, package) if node.level else name)
    return [
        name
        for name in imported
        if name.split(".")[0] not in sys.stdlib_module_names
        and not any(name == allowed or name.startswith(f"{allowed}.") for allowed in ALLOWED[layer])
    ]


@pytest.mark.parametrize("layer", list(ALLOWED))
def test_layers_import_only_what_they_may(layer: str) -> None:
    for path in (PACKAGE / layer).rglob("*.py"):
        module = ".".join((ROOT, *path.relative_to(PACKAGE).with_suffix("").parts))
        assert not violations(path.read_text(encoding="utf-8"), module, layer), path


def test_guard_detects_deliberate_violations() -> None:
    assert violations("import neonize", f"{ROOT}.application.extract", "application")
    assert violations("import sqlalchemy", f"{ROOT}.domain.message", "domain")
    assert violations(f"from {ROOT} import adapters", f"{ROOT}.domain.message", "domain")
    assert violations("from ..application import ports", f"{ROOT}.domain.message", "domain")
    assert violations(f"from {ROOT}.adapters import x", f"{ROOT}.application.bus", "application")


def test_guard_accepts_the_allowed_imports() -> None:
    source = "import asyncio\nfrom pydantic import BaseModel\nfrom .base import FrozenModel\n"
    assert not violations(source, f"{ROOT}.domain.message", "domain")
