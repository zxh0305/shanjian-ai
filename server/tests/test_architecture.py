"""架构契约（替代 import-linter）：层间只能向下依赖，反向即失败。

层序（高→低）：routes > services > tools > core > repositories > db
另外：
- tools 只准包装 core，不得碰 repositories/db（纯能力层）；
- agents 可用 tools/core/repositories/prompts，但不得 import routes/services/db（编排靠 ctx 注入回调）。
"""
from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"
LAYERS = ["routes", "services", "agents", "tools", "core", "repositories", "db", "schemas"]


def _layer_of(module: str) -> str | None:
    parts = module.split(".")
    if parts[0] != "app" or len(parts) < 2:
        return None
    return parts[1] if parts[1] in LAYERS else None


def _imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            base = "." * (node.level or 0) + node.module
            mods.add("app" + base.lstrip(".") if node.level else node.module)
    return mods


def test_layer_dependencies():
    violations = []
    for f in APP.rglob("*.py"):
        rel = f.relative_to(APP)
        if len(rel.parts) < 2 or rel.parts[0] not in LAYERS:
            continue
        src_layer = rel.parts[0]
        src_idx = LAYERS.index(src_layer)
        for mod in _imports_of(f):
            dst = _layer_of(mod)
            if dst and dst != src_layer and LAYERS.index(dst) < src_idx:
                violations.append(f"{rel} ({src_layer}) → {mod} ({dst})")
    assert not violations, "反向依赖:\n" + "\n".join(violations)


def test_agents_no_upward_deps():
    for f in (APP / "agents").rglob("*.py"):
        for mod in _imports_of(f):
            dst = _layer_of(mod)
            assert dst not in ("routes", "services", "db"), f"{f.name} 不得依赖 {dst}（应经 ctx 注入）"


def test_tools_stay_pure():
    for f in (APP / "tools").glob("*.py"):
        for mod in _imports_of(f):
            dst = _layer_of(mod)
            assert dst not in ("repositories", "db"), f"{f.name} 不得依赖 {dst}（工具层只包装 core）"
