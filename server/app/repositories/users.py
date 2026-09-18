"""SQL 层 · 用户与令牌。"""
from __future__ import annotations

from ..db import execute, query_one


def get_by_name(name: str) -> dict | None:
    return query_one("SELECT * FROM users WHERE name=?", (name,))


def create(name: str, pass_hash: str) -> int:
    return execute("INSERT INTO users (name, pass_hash) VALUES (?,?)", (name, pass_hash))


def claim_legacy_projects(uid: int) -> None:
    """首个注册用户认领升级前的无主项目。"""
    execute("UPDATE projects SET user_id=? WHERE user_id IS NULL", (uid,))


def new_token(uid: int, token: str) -> None:
    execute("INSERT INTO auth_tokens (token, user_id) VALUES (?,?)", (token, uid))


def user_by_token(token: str) -> dict | None:
    return query_one(
        "SELECT u.id, u.name FROM auth_tokens t JOIN users u ON u.id = t.user_id WHERE t.token = ?",
        (token,))


def delete_token(token: str) -> None:
    execute("DELETE FROM auth_tokens WHERE token=?", (token,))
