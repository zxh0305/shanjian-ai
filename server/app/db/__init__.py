"""数据库层：连接、Schema、版本化迁移。

兼容门面：`db.query / db.query_one / db.execute / db.executemany / db.init_db`
供存量代码（pipeline/renderer 等）过渡使用；新代码请走 `repositories/`。
"""
from __future__ import annotations

from .connection import connect, executemany, execute, query, query_one
from .migrate import init_db

__all__ = ["connect", "query", "query_one", "execute", "executemany", "init_db"]
