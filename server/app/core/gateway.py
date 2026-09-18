"""模型网关（进程内薄网关）：任务 → 模型 → 密钥 → 重试 → 降级 → 计量。

智能体只喊任务名（build_edl / review_cut / write_narration / analyze_scenes），
不认识供应商与密钥。路由优先级：
  1) 环境变量 SHANJIAN_MODEL_<TASK>（临时排障用）
  2) 用户的任务分配（llm_config.taskModels）
  3) 用户当前模型
失败自动降级到用户的备用模型，再失败则抛 GatewayError（不再静默）。
"""
from __future__ import annotations

import os
import time

from ..repositories import usage as usage_repo
from . import llm_config


class GatewayError(RuntimeError):
    pass


def _env_override(task: str) -> str:
    return os.environ.get(f"SHANJIAN_MODEL_{task.upper()}", "")


def resolve_chain(task: str, user_id: int) -> list[str]:
    """该任务要尝试的模型 id 顺序（去重）。"""
    chain = []
    env = _env_override(task)
    if env:
        chain.append(env)
    task_model = llm_config.get_task_models(user_id).get(task)
    if task_model:
        chain.append(task_model)
    chain.append(llm_config.get_current_model(user_id)["modelId"])
    fb = llm_config.get_fallback_model(user_id)
    if fb:
        chain.append(fb)
    out, seen = [], set()
    for m in chain:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _call(task: str, user_id: int, build_kwargs, want_vision: bool) -> dict:
    """通用调用：按链路尝试，计量并返回 {text, model, usage}。"""
    last_err = ""
    for model_id in resolve_chain(task, user_id):
        client, model, err = llm_config.get_client_for_model(model_id, user_id)
        if err:
            last_err = err
            continue
        target_model = model["vl_model"] if want_vision else model["llm_model"]
        t0 = time.time()
        try:
            kwargs = build_kwargs(target_model, model)
            resp = _with_retry(lambda: client.chat.completions.create(**kwargs))
            elapsed = int((time.time() - t0) * 1000)
            msg = resp.choices[0].message
            text = (getattr(msg, "content", "") or "").strip()
            if not text:  # 推理型模型兜底
                text = (getattr(msg, "reasoning_content", "") or "").strip()
            u = getattr(resp, "usage", None)
            usage_repo.add(user_id, task, model_id,
                           int(getattr(u, "prompt_tokens", 0) or 0),
                           int(getattr(u, "completion_tokens", 0) or 0), elapsed, True)
            return {"text": text, "model": model_id, "elapsedMs": elapsed}
        except Exception as e:  # noqa: BLE001 供应商差异统一收敛
            elapsed = int((time.time() - t0) * 1000)
            usage_repo.add(user_id, task, model_id, 0, 0, elapsed, False)
            last_err = f"{model['name']}: {str(e)[:160]}"
            continue
    raise GatewayError(last_err or "没有可用的模型（请到设置页配置密钥）")


def _with_retry(fn, max_retries: int = 3):
    """限流(429)/网络抖动自动等待重试。"""
    import time as _t
    last = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            msg = str(e)
            if attempt < max_retries and ("429" in msg or "rate" in msg.lower() or "timeout" in msg.lower()):
                _t.sleep(2 * (attempt + 1))
                continue
            raise
    raise last


def chat(task: str, messages: list[dict], user_id: int = 1, **kw) -> dict:
    """文本任务调用（build_edl / write_narration）。"""
    return _call(task, user_id,
                 lambda target, model: {"model": target, "messages": messages, **kw},
                 want_vision=False)


def vision(task: str, prompt: str, images_b64: list[str], user_id: int = 1, **kw) -> dict:
    """视觉任务调用（analyze_scenes / review_cut）：prompt + base64 图片列表。"""
    content = [{"type": "text", "text": prompt}]
    content += [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}}
                for b in images_b64]
    return _call(task, user_id,
                 lambda target, model: {"model": target,
                                        "messages": [{"role": "user", "content": content}], **kw},
                 want_vision=True)
