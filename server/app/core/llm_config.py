"""多模型配置服务：支持国内主流视觉大模型动态切换。

模型列表、密钥存储、调用接口统一管理。
配置跟着用户走：每个账号一份 data/llm_config_{user_id}.json；
单人时期的全局 llm_config.json 在首个账号首次访问时自动迁移归它。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from ..config import settings

LEGACY_FILE = settings.db_path.parent / "llm_config.json"

# 支持的模型列表
MODELS = [
    {
        "id": "qwen-vl",
        "name": "通义千问 VL",
        "provider": "阿里云百炼",
        "vl_model": "qwen-vl-max-latest",
        "llm_model": "qwen-plus-latest",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_var": "DASHSCOPE_API_KEY",
        "free_quota": "新用户约7000万Token，90天",
        "get_key_url": "https://bailian.console.aliyun.com",
        "config_note": "登录百炼平台 → 左侧「API Key」→ 创建 Key → 复制 sk- 开头的密钥",
    },
    {
        "id": "glm-4v",
        "name": "智谱 GLM-4V",
        "provider": "智谱AI",
        "vl_model": "glm-4.6v-flash",
        "llm_model": "glm-4-flash",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "env_var": "GLM_API_KEY",
        "free_quota": "视觉模型GLM-4.6V-Flash永久免费不限量",
        "get_key_url": "https://open.bigmodel.cn",
        "config_note": "推荐！注册智谱开放平台(bigmodel.cn) → 右上角「API Keys」→ 创建 Key → 复制。视觉模型免费不限量，格式如 id.secret",
    },
    {
        "id": "doubao-vision",
        "name": "豆包 Vision",
        "provider": "字节跳动",
        "vl_model": "doubao-1-5-thinking-vision-pro-250428",
        "llm_model": "doubao-1-5-pro-32k-250115",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "env_var": "ARK_API_KEY",
        "free_quota": "新用户体验额度",
        "get_key_url": "https://console.volcengine.com/ark",
        "config_note": "豆包需要先在控制台创建「接入点」获取 Endpoint ID。在 API Key 输入框填入 Ark API Key，模型名会自动使用上述模型。如果创建了自定义接入点，请在 API Key 框中填入 'sk-xxx|ep-xxx' 格式（密钥|接入点ID）。",
    },
    {
        "id": "moonshot-vision",
        "name": "Kimi 视觉版",
        "provider": "月之暗面",
        "vl_model": "moonshot-v1-8k-vision-preview",
        "llm_model": "moonshot-v1-8k",
        "base_url": "https://api.moonshot.cn/v1",
        "env_var": "MOONSHOT_API_KEY",
        "free_quota": "15元体验额度",
        "get_key_url": "https://platform.moonshot.cn",
        "config_note": "注册月之暗面开放平台 → 「API Key」→ 创建 Key → 复制",
    },
    {
        "id": "deepseek-vision",
        "name": "DeepSeek Vision",
        "provider": "DeepSeek",
        "vl_model": "deepseek-flash",
        "llm_model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "env_var": "DEEPSEEK_API_KEY",
        "free_quota": "按量计费，价格便宜",
        "get_key_url": "https://platform.deepseek.com",
        "config_note": "注册 DeepSeek 开放平台 → 「API Keys」→ 创建 Key → 复制 sk- 开头密钥。注意：需要账户有余额才能调用",
    },
    {
        "id": "hunyuan-vision",
        "name": "腾讯混元 Vision",
        "provider": "腾讯",
        "vl_model": "hunyuan-vision",
        "llm_model": "hunyuan-plus",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "env_var": "HUNYUAN_API_KEY",
        "free_quota": "新用户体验额度",
        "get_key_url": "https://console.cloud.tencent.com/hunyuan",
        "config_note": "登录腾讯云 → 搜索「混元」→ 获取 API Key → 复制",
    },
]

DEFAULT_MODEL_ID = "qwen-vl"

# 任务级模型分配（网关用）：任务名 → 说明（能力由调用方决定）
TASKS = {
    "analyze_scenes": "画面理解（视觉）",
    "build_edl": "剪辑方案（文本）",
    "write_narration": "风格文案（文本）",
    "review_cut": "审片打分（视觉）",
}


def _config_file(user_id: int) -> Path:
    return settings.db_path.parent / f"llm_config_{user_id}.json"


def _read_config(user_id: int = 1) -> dict:
    f = _config_file(user_id)
    if not f.exists() and user_id == 1 and LEGACY_FILE.exists():
        # 一次性迁移：单人时期的全局配置归首个账号
        try:
            legacy = json.loads(LEGACY_FILE.read_text(encoding="utf-8"))
            _write_config(legacy, user_id)
            return legacy
        except (json.JSONDecodeError, OSError):
            pass
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _write_config(cfg: dict, user_id: int = 1) -> None:
    _config_file(user_id).write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def get_task_models(user_id: int = 1) -> dict:
    """任务级模型覆盖：{task: modelId}；缺省（未配置）由网关继承当前模型。"""
    cfg = _read_config(user_id)
    return {k: v for k, v in (cfg.get("taskModels") or {}).items() if k in TASKS and v}


def set_task_models(user_id: int, mapping: dict) -> dict:
    """保存任务分配；值为空字符串表示恢复「继承当前模型」。"""
    cfg = _read_config(user_id)
    clean = {k: v for k, v in (mapping or {}).items() if k in TASKS}
    valid_ids = [m["id"] for m in MODELS]
    for k, v in clean.items():
        if v and v not in valid_ids:
            return {"error": f"不支持的模型: {v}"}
    cfg["taskModels"] = {k: v for k, v in clean.items() if v}
    _write_config(cfg, user_id)
    return {"ok": True}


def get_fallback_model(user_id: int = 1) -> str:
    return (_read_config(user_id).get("fallback") or "")


def set_fallback_model(user_id: int, model_id: str) -> dict:
    cfg = _read_config(user_id)
    if model_id and model_id not in [m["id"] for m in MODELS]:
        return {"error": f"不支持的模型: {model_id}"}
    cfg["fallback"] = model_id or ""
    _write_config(cfg, user_id)
    return {"ok": True}


def get_config(user_id: int = 1) -> dict:
    """返回该用户的配置 + 模型列表 + 各模型密钥状态。"""
    cfg = _read_config(user_id)
    current = cfg.get("modelId", DEFAULT_MODEL_ID)
    keys = cfg.get("apiKeys", {})
    verified = cfg.get("verified", {})
    out_models = []
    for m in MODELS:
        has_key = bool(keys.get(m["id"]) or os.environ.get(m["env_var"]))
        # 只有通过真实调用验证的 key 才算「可用」
        usable = has_key and (verified.get(m["id"]) or os.environ.get(m["env_var"]))
        out_models.append({
            **m,
            "configured": has_key,
            "verified": bool(usable),
            "current": m["id"] == current,
        })
    return {
        "modelId": current,
        "models": out_models,
        "tasks": TASKS,
        "taskModels": get_task_models(user_id),
        "fallback": get_fallback_model(user_id),
    }


def save_config(user_id: int, model_id: str, api_key: str | None = None, switch: bool = True) -> dict:
    """保存该用户的模型选择和密钥。

    - 带密钥：必须先通过真实调用测试，失败则拒绝保存
    - 切换模型：目标模型必须已验证可用，否则拒绝
    """
    cfg = _read_config(user_id)
    valid_ids = [m["id"] for m in MODELS]
    if model_id not in valid_ids:
        return {"error": f"不支持的模型: {model_id}"}

    if api_key is not None:
        if api_key:
            # 保存前强制测试，不可用就不保存
            test = test_model(model_id, api_key)
            if not test.get("ok"):
                return {"error": f"密钥不可用，未保存：{test.get('error', '测试失败')}"}
            keys = cfg.get("apiKeys", {})
            keys[model_id] = api_key
            cfg["apiKeys"] = keys
            verified = cfg.get("verified", {})
            verified[model_id] = True
            cfg["verified"] = verified
        else:
            # 清空密钥
            keys = cfg.get("apiKeys", {})
            keys.pop(model_id, None)
            cfg["apiKeys"] = keys
            verified = cfg.get("verified", {})
            verified.pop(model_id, None)
            cfg["verified"] = verified

    if switch:
        # 切换前检查该模型密钥已验证可用
        keys = cfg.get("apiKeys", {})
        verified = cfg.get("verified", {})
        env_ok = bool(os.environ.get(next(m["env_var"] for m in MODELS if m["id"] == model_id), ""))
        if not (keys.get(model_id) or env_ok):
            return {"error": "请先配置该模型的 API Key"}
        if not (verified.get(model_id) or env_ok):
            return {"error": "该模型密钥未通过验证，请重新测试保存"}
        cfg["modelId"] = model_id
    _write_config(cfg, user_id)
    return get_config(user_id)


def get_current_model(user_id: int = 1) -> dict:
    """返回该用户当前选中模型的完整配置（含密钥）。"""
    cfg = _read_config(user_id)
    model_id = cfg.get("modelId", DEFAULT_MODEL_ID)
    model = next((m for m in MODELS if m["id"] == model_id), MODELS[0])
    keys = cfg.get("apiKeys", {})
    verified = cfg.get("verified", {})
    stored = keys.get(model_id, "")
    env_key = os.environ.get(model["env_var"], "")
    # 只有已验证通过的密钥才真正可用，避免无效 key 在剪辑流程中反复失败
    if stored and verified.get(model_id):
        api_key = stored
    elif env_key:
        api_key = env_key
    else:
        api_key = ""
    return {**model, "apiKey": api_key, "modelId": model_id}


def get_client_for_model(model_id: str, user_id: int = 1):
    """按指定模型构造客户端（网关用）：返回 (client, model_cfg, err)。"""
    model = next((m for m in MODELS if m["id"] == model_id), None)
    if not model:
        return None, None, f"模型不存在: {model_id}"
    cfg = _read_config(user_id)
    stored = (cfg.get("apiKeys") or {}).get(model_id, "")
    verified = bool((cfg.get("verified") or {}).get(model_id))
    env_key = os.environ.get(model["env_var"], "")
    api_key = stored if (stored and verified) else (env_key or "")
    if not api_key:
        return None, None, f"模型 {model['name']} 未配置可用密钥"
    from openai import OpenAI
    vl_model, llm_model = model["vl_model"], model["llm_model"]
    if model_id == "doubao-vision" and "|" in api_key:
        api_key, ep = api_key.split("|", 1)
        ep = ep.strip()
        if ep:
            vl_model = llm_model = ep
    client = OpenAI(api_key=api_key, base_url=model["base_url"])
    return client, {**model, "apiKey": api_key, "vl_model": vl_model, "llm_model": llm_model}, None


def get_client(user_id: int = 1):
    """返回该用户当前模型的 OpenAI 兼容客户端。"""
    model = get_current_model(user_id)
    if not model["apiKey"]:
        return None, None, "未配置API密钥"
    from openai import OpenAI

    api_key = model["apiKey"]
    vl_model = model["vl_model"]
    llm_model = model["llm_model"]

    # 豆包特殊处理：支持 "sk-xxx|ep-xxx" 格式（密钥|接入点ID）
    if model["id"] == "doubao-vision" and "|" in api_key:
        parts = api_key.split("|", 1)
        api_key = parts[0]
        ep_id = parts[1].strip()
        if ep_id:
            vl_model = ep_id
            llm_model = ep_id

    client = OpenAI(api_key=api_key, base_url=model["base_url"])
    model = {**model, "apiKey": api_key, "vl_model": vl_model, "llm_model": llm_model}
    return client, model, None


def test_model(model_id: str, api_key: str) -> dict:
    """测试模型连通性。"""
    model = next((m for m in MODELS if m["id"] == model_id), None)
    if not model:
        return {"ok": False, "error": "模型不存在"}
    if not api_key:
        return {"ok": False, "error": "请填写API密钥"}
    try:
        import base64
        from openai import OpenAI

        test_key = api_key
        vl_model = model["vl_model"]

        # 豆包特殊处理
        if model_id == "doubao-vision" and "|" in api_key:
            parts = api_key.split("|", 1)
            test_key = parts[0]
            ep_id = parts[1].strip()
            if ep_id:
                vl_model = ep_id

        # 用真实图片调用视觉模型验证（测通=剪辑时的视觉分析一定可用）
        # 1x1 红色 JPEG，base64 编码
        tiny_jpeg = (
            "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
            "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
            "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AVN//2Q=="
        )
        client = OpenAI(api_key=test_key, base_url=model["base_url"])
        resp = client.chat.completions.create(
            model=vl_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "这张图片是什么颜色？只回答一个词"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{tiny_jpeg}"}},
                ],
            }],
            max_tokens=10,
        )
        text = (resp.choices[0].message.content or "").strip()
        return {"ok": True, "response": f"视觉模型({vl_model})验证通过: {text[:30]}"}
    except Exception as e:
        return {"ok": False, "error": f"视觉模型({model['vl_model']})调用失败: {str(e)[:180]}"}
