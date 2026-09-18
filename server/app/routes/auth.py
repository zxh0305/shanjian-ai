"""用户登录与数据隔离（家人局域网自用强度）。

- 注册/登录：用户名 + 密码（scrypt 加盐哈希），返回长期令牌
- 令牌放 Authorization: Bearer，前端存 localStorage
- 数据隔离：projects.user_id 过滤；素材/时间线/成片都挂在 project 下自动隔离
- 音乐库、AI 模型配置为共享（一台 Mac 一份）
"""
from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..repositories import projects as projects_repo
from ..repositories import users as users_repo

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    h = hashlib.scrypt(password.encode(), salt=salt.encode(), n=2 ** 14, r=8, p=1)
    return f"{salt}${h.hex()}"


def _verify(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_hash(password, salt), stored)


class AuthBody(BaseModel):
    name: str = Field(min_length=1, max_length=24)
    password: str = Field(min_length=6, max_length=64)


def _new_token(user_id: int) -> str:
    token = secrets.token_hex(24)
    users_repo.new_token(user_id, token)
    return token


def _bearer(request: Request) -> str | None:
    h = request.headers.get("authorization", "")
    return h[7:].strip() if h.lower().startswith("bearer ") else None


def current_user(request: Request) -> dict:
    """从请求头解析令牌 → 用户；未登录 401。路由函数用 request: Request 声明依赖。"""
    tok = _bearer(request)
    u = users_repo.user_by_token(tok) if tok else None
    if not u:
        raise HTTPException(401, "请先登录")
    return u


def owned_project(user: dict, project_id: int) -> dict:
    """校验项目归属；他人的项目按不存在处理（不泄露存在性）。"""
    p = projects_repo.get(project_id)
    if not p or p["user_id"] != user["id"]:
        raise HTTPException(404, "项目不存在")
    return p


@router.post("/register")
def register(body: AuthBody):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "用户名不能为空")
    if users_repo.get_by_name(name):
        raise HTTPException(400, "这个用户名已被使用")
    uid = users_repo.create(name, _hash(body.password))
    # 第一个注册的用户认领历史上无主的项目（升级前单人时期的数据）
    if uid == 1:
        users_repo.claim_legacy_projects(uid)
    return {"token": _new_token(uid), "user": {"id": uid, "name": name}}


@router.post("/login")
def login(body: AuthBody):
    u = users_repo.get_by_name(body.name.strip())
    if not u or not _verify(body.password, u["pass_hash"]):
        raise HTTPException(401, "用户名或密码不对")
    return {"token": _new_token(u["id"]), "user": {"id": u["id"], "name": u["name"]}}


@router.post("/logout")
def logout(request: Request):
    tok = _bearer(request)
    if tok:
        users_repo.delete_token(tok)
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    return {"user": current_user(request)}
