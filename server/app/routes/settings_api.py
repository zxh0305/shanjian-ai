"""模型设置接口（跟用户走）：GET/POST /settings/model、POST /settings/model/test、
POST /settings/model/tasks（任务分配+备用模型）、GET /settings/usage（本月用量）。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..core import llm_config
from ..repositories import usage as usage_repo
from .auth import current_user

router = APIRouter()


class SaveModelBody(BaseModel):
    modelId: str
    apiKey: str | None = None
    switch: bool = True


class TestModelBody(BaseModel):
    modelId: str
    apiKey: str


class TaskModelsBody(BaseModel):
    taskModels: dict[str, str] = {}
    fallback: str = ""


@router.get("/settings/model")
def get_model_settings(request: Request):
    user = current_user(request)
    return llm_config.get_config(user["id"])


@router.post("/settings/model")
def save_model_settings(body: SaveModelBody, request: Request):
    user = current_user(request)
    result = llm_config.save_config(user["id"], body.modelId, body.apiKey, switch=body.switch)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/settings/model/test")
def test_model_connection(body: TestModelBody):
    # 测试只验证密钥本身，与用户无关
    return llm_config.test_model(body.modelId, body.apiKey)


@router.post("/settings/model/tasks")
def save_task_models(body: TaskModelsBody, request: Request):
    user = current_user(request)
    result = llm_config.set_task_models(user["id"], body.taskModels)
    if "error" in result:
        raise HTTPException(400, result["error"])
    result = llm_config.set_fallback_model(user["id"], body.fallback.strip())
    if "error" in result:
        raise HTTPException(400, result["error"])
    return llm_config.get_config(user["id"])


@router.get("/settings/usage")
def usage_summary(request: Request):
    user = current_user(request)
    return usage_repo.month_summary(user["id"])
