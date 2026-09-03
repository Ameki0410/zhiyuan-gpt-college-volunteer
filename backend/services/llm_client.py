# services/llm_client.py —— 通用大模型调用（OpenAI 兼容接口）
# step13：用通用的 httpx 异步 POST 调 OpenAI 兼容接口（chat/completions）。
#         默认指向 DeepSeek（支持免费额度，中文好）。切换只需改 .env 里 LLM_BASE_URL / LLM_MODEL。
#         若未配置 LLM_API_KEY，则本文件不被使用，plan_service 会 fallback 到 mock。

from __future__ import annotations

import json
import logging

import httpx

from config import llm as cfg

log = logging.getLogger(__name__)

# 强制让大模型输出 JSON 的系统提示前缀（保证返回能被 parse 为 PlanResponse）
_JSON_PROMPT = (
    "你必须严格只输出一个 JSON 对象，不能有任何多余的文字、解释、Markdown 代码块包裹、"
    "或前后缀说明。JSON 的顶级字段必须严格包含：autoModeTag(string), score(number), "
    "s06, s07, s08, s09。其中 s06/s07/s08/s09 都是对象，字段为 title(string), "
    "level(string,取值 red|org|grn|blu), items(数组，每项含 sch/major/risk/note 四个 string 字段)。"
    "risk 的取值严格限定为：冲 / 稳 / 保 / 备。不要输出 JSON 以外的任何字符。"
)


def _json_schema_example(score: int) -> dict:
    return {
        "autoModeTag": "AI智能推荐",
        "score": score,
        "s06": {
            "title": "冲刺院校",
            "level": "red",
            "items": [
                {"sch": "示例大学", "major": "示例专业", "risk": "冲", "note": "示例说明"},
            ],
        },
        "s07": {"title": "稳妥院校", "level": "org", "items": []},
        "s08": {"title": "保底院校", "level": "grn", "items": []},
        "s09": {"title": "备选建议", "level": "blu", "items": []},
    }


async def call_llm(prompt: str, score: int) -> dict:
    """调用大模型，返回 JSON。失败抛异常，由调用方 fallback 到 mock。"""
    user_msg = (
        f"{_JSON_PROMPT}\n\n"
        f"参考 JSON 结构示例：\n{json.dumps(_json_schema_example(score), ensure_ascii=False)}\n\n"
        f"请根据以下用户输入，为考生生成一份完整的志愿填报方案 JSON（score 字段必须等于考生分数 {score}）：\n"
        f"{prompt}"
    )

    headers = {
        "Authorization": f"Bearer {cfg.API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": cfg.MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "你是一名资深的高考志愿填报规划师。"},
            {"role": "user", "content": user_msg},
        ],
        # DeepSeek/OpenAI 都支持 JSON 模式时优先强制 JSON
        "response_format": {"type": "json_object"},
    }
    url = f"{cfg.BASE_URL}/chat/completions"

    log.info("LLM call start: model=%s score=%d", cfg.MODEL, score)
    async with httpx.AsyncClient(timeout=cfg.TIMEOUT) as client:
        r = await client.post(url, headers=headers, json=body)
        if r.status_code != 200:
            log.error("LLM HTTP %s: %s", r.status_code, r.text[:300])
            raise RuntimeError(f"LLM HTTP {r.status_code}")
        data = r.json()

    content = data["choices"][0]["message"]["content"]
    log.info("LLM call done, content length=%d", len(content or ""))
    # 兼容模型给的 markdown 代码块
    content = (content or "").strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
        content = content.strip()
    return json.loads(content)
