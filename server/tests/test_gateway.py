"""模型网关单测：任务路由链(环境变量/任务分配/当前模型/备用) 优先级与去重、
成功计量、失败降级、全链失败报错、review_cut 经网关解析、任务分配接口。"""
from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace as NS

os.environ.setdefault("SHANJIAN_DATA_DIR", tempfile.mkdtemp(prefix="shanjian_gateway_"))

import pytest  # noqa: E402

from app.core import gateway  # noqa: E402
from app.core import llm_config  # noqa: E402
from app.core import llm as qwen_vl  # noqa: E402

UID = 7


def _patch_routes(monkeypatch, current="qwen-vl", task_models=None, fallback=""):
    monkeypatch.setattr(llm_config, "get_current_model", lambda uid: {"modelId": current})
    monkeypatch.setattr(llm_config, "get_task_models",
                        lambda uid: task_models or {})
    monkeypatch.setattr(llm_config, "get_fallback_model", lambda uid: fallback)


def test_resolve_chain_inherit_current(monkeypatch):
    """未做任何分配 → 只用当前模型。"""
    _patch_routes(monkeypatch)
    assert gateway.resolve_chain("build_edl", UID) == ["qwen-vl"]


def test_resolve_chain_full_priority_and_dedup(monkeypatch):
    """环境变量 > 任务分配 > 当前模型 > 备用，且去重保序。"""
    _patch_routes(monkeypatch, current="qwen-vl", task_models={"build_edl": "glm-4v"},
                  fallback="qwen-vl")  # 备用与当前重复 → 去重
    monkeypatch.setenv("SHANJIAN_MODEL_BUILD_EDL", "doubao-vision")
    assert gateway.resolve_chain("build_edl", UID) == \
        ["doubao-vision", "glm-4v", "qwen-vl"]
    # 其他任务不受 build_edl 的环境变量与任务分配影响
    monkeypatch.delenv("SHANJIAN_MODEL_BUILD_EDL")
    assert gateway.resolve_chain("review_cut", UID) == ["qwen-vl"]


class _FakeAPI:
    """按预设脚本依次返回文本或抛异常的 chat.completions。"""

    def __init__(self, script):
        self.script = list(script)
        self.kwargs = []

    def create(self, **kw):
        self.kwargs.append(kw)
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        msg = NS(content=step, reasoning_content="")
        return NS(choices=[NS(message=msg)], usage=NS(prompt_tokens=11, completion_tokens=7))


def _fake_client(api):
    return NS(chat=NS(completions=api))


MODEL_OK = {"name": "通义千问 VL", "vl_model": "qwen-vl-max", "llm_model": "qwen-plus"}


def test_call_success_and_metering(monkeypatch):
    """成功调用返回 text/model，并计一条 ok 用量。"""
    _patch_routes(monkeypatch, current="qwen-vl")
    api = _FakeAPI(["你好"])
    monkeypatch.setattr(llm_config, "get_client_for_model",
                        lambda mid, uid: (_fake_client(api), MODEL_OK, None))
    seen = []
    monkeypatch.setattr(gateway.usage_repo, "add",
                        lambda *a: seen.append(a))
    out = gateway.chat("build_edl", [{"role": "user", "content": "hi"}], user_id=UID)
    assert out["text"] == "你好" and out["model"] == "qwen-vl"
    assert api.kwargs[0]["model"] == "qwen-plus"          # 文本任务用 llm_model
    assert seen and seen[0][:4] == (UID, "build_edl", "qwen-vl", 11) and seen[0][-1] is True


def test_call_fallback_on_failure(monkeypatch):
    """主模型报错 → 记失败用量并降级到备用模型，整体仍成功。"""
    _patch_routes(monkeypatch, current="qwen-vl", fallback="glm-4v")
    apis = {"qwen-vl": _FakeAPI([RuntimeError("boom")]), "glm-4v": _FakeAPI(["兜底结果"])}
    monkeypatch.setattr(llm_config, "get_client_for_model",
                        lambda mid, uid: (_fake_client(apis[mid]), MODEL_OK, None))
    seen = []
    monkeypatch.setattr(gateway.usage_repo, "add", lambda *a: seen.append(a))
    out = gateway.chat("write_narration", [{"role": "user", "content": "hi"}], user_id=UID)
    assert out["text"] == "兜底结果" and out["model"] == "glm-4v"
    assert [(r[2], r[-1]) for r in seen] == [("qwen-vl", False), ("glm-4v", True)]


def test_call_vision_uses_vl_model(monkeypatch):
    """视觉任务用 vl_model，图片按 data URL 组装。"""
    _patch_routes(monkeypatch, current="glm-4v")
    api = _FakeAPI(["画面是海"])
    monkeypatch.setattr(llm_config, "get_client_for_model",
                        lambda mid, uid: (_fake_client(api), MODEL_OK, None))
    monkeypatch.setattr(gateway.usage_repo, "add", lambda *a: None)
    out = gateway.vision("analyze_scenes", "描述", ["QUJD"], user_id=UID)
    assert out["text"] == "画面是海"
    content = api.kwargs[0]["messages"][0]["content"]
    assert content[0]["type"] == "text" and content[1]["image_url"]["url"].endswith("base64,QUJD")


def test_call_no_model_raises_gateway_error(monkeypatch):
    """全部模型不可用 → 抛 GatewayError（不再静默）。"""
    _patch_routes(monkeypatch, current="qwen-vl")
    monkeypatch.setattr(llm_config, "get_client_for_model",
                        lambda mid, uid: (None, None, f"模型 {mid} 未配置可用密钥"))
    monkeypatch.setattr(gateway.usage_repo, "add", lambda *a: None)
    with pytest.raises(gateway.GatewayError, match="未配置"):
        gateway.chat("build_edl", [{"role": "user", "content": "hi"}], user_id=UID)


def test_review_cut_parses_via_gateway(monkeypatch):
    """review_cut 经网关视觉调用并解析 verdict（回归：user_id 透传、无残留死代码）。"""
    calls = {}

    class _GW:
        def vision(self, task, prompt, images, user_id=1, **kw):
            calls.update(task=task, user_id=user_id, images=images)
            return {"text": '{"score": 91, "pass": true, "comment": "节奏好", '
                            '"suggestions": ["再紧凑点", "x", "y", "z"]}'}

    import app.core.llm as llm_mod
    monkeypatch.setattr(llm_mod, "_gw", lambda: _GW())
    out = qwen_vl.review_cut(["ZmFrZQ=="], "摘要", user_id=5)
    assert out == {"score": 91, "pass": True, "comment": "节奏好",
                   "suggestions": ["再紧凑点", "x", "y"]}   # 最多 3 条
    assert calls["task"] == "review_cut" and calls["user_id"] == 5 and calls["images"] == ["ZmFrZQ=="]


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/auth/register", json={"name": "pytest_gw", "password": "pytest123"})
        if r.status_code != 200:
            r = c.post("/auth/login", json={"name": "pytest_gw", "password": "pytest123"})
        assert r.status_code == 200, r.text
        c.headers.update({"Authorization": "Bearer " + r.json()["token"]})
        yield c


def test_settings_tasks_api(client):
    """任务分配保存与校验；用量接口返回汇总结构。"""
    r = client.post("/settings/model/tasks",
                    json={"taskModels": {"build_edl": "glm-4v", "unknown_task": "qwen-vl"},
                          "fallback": ""})
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["taskModels"] == {"build_edl": "glm-4v"}     # 白名单外的任务名被丢弃
    assert cfg["fallback"] == ""

    r = client.post("/settings/model/tasks",
                    json={"taskModels": {"build_edl": "not-a-model"}, "fallback": ""})
    assert r.status_code == 400                             # 模型 id 白名单校验

    r = client.post("/settings/model/tasks",
                    json={"taskModels": {}, "fallback": "glm-4v"})
    assert r.status_code == 200 and r.json()["fallback"] == "glm-4v"

    r = client.get("/settings/usage")
    assert r.status_code == 200
    assert set(r.json().keys()) == {"calls", "failed", "tokens_in", "tokens_out"}
