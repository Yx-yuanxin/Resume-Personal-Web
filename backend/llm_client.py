# -*- coding: utf-8 -*-
"""大模型 API 客户端（OpenAI 兼容协议）。

设计要点（答辩可讲）：
1. 一套代码适配所有 OpenAI 兼容服务（DeepSeek/通义/Kimi/GLM...），比赛现场哪家有 Key 用哪家；
2. 未配置 API Key 时抛出 LLMUnavailable，由上层降级为 MOCK 模板回答，
   保证离线环境下演示链路依然完整（合规硬要求：宁可模板拼接，也不让模型编造）。
"""
import json
import logging

import requests

import config

logger = logging.getLogger("llm")


class LLMUnavailable(Exception):
    """LLM 不可用（无 Key / 网络失败），调用方应降级处理。"""


def is_llm_ready() -> bool:
    return bool(config.LLM_API_KEY)


def llm_chat(messages, temperature=None, json_mode=False):
    """调用 OpenAI 兼容的 /chat/completions 接口，返回文本内容。

    :param messages: [{"role": "system|user|assistant", "content": "..."}]
    :param json_mode: True 时要求模型输出 JSON（用于知识抽取）
    """
    if not is_llm_ready():
        raise LLMUnavailable("未配置 LLM_API_KEY，请设置环境变量后重启")

    headers = {
        "Authorization": f"Bearer {config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "temperature": config.LLM_TEMPERATURE if temperature is None else temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        resp = requests.post(
            f"{config.LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=config.LLM_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # 网络失败/限流/鉴权失败统一降级
        logger.warning("LLM 调用失败，降级 MOCK: %s", exc)
        raise LLMUnavailable(str(exc))


def llm_chat_json(messages, temperature=0.1):
    """要求模型返回 JSON 并解析；失败返回 None（调用方自行降级）。"""
    text = llm_chat(messages, temperature=temperature, json_mode=True)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 兜容：剥掉可能的 markdown 代码块包裹
        try:
            return json.loads(text.strip().strip("`").removeprefix("json").strip())
        except Exception:
            return None
