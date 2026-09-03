# services/plan_service.py —— 生成方案的业务逻辑
# step11：仅返回 mock；step13 接入真实 LLM（没配 Key 时 fallback 到 mock）

from __future__ import annotations

import logging
from typing import Any

from schemas import PlanRequest, PlanResponse
from data.mock_plan import build_mock_plan
from config import llm as llm_cfg

log = logging.getLogger(__name__)


def build_prompt(req: PlanRequest) -> str:
    """把前端上报的字段整合成自然语言提示词，交给大模型生成方案。"""
    return (
        f"【考生信息】\n"
        f"- 省份：{req.province}\n"
        f"- 选科组合：{', '.join(req.subjects)}（共{len(req.subjects)}门）\n"
        f"- 高考成绩：{req.score} 分（满分 750 分）\n\n"
        f"【偏好设置】\n"
        f"- 目标院校：{req.school}\n"
        f"- 地域偏好：{req.region}\n"
        f"- 专业偏好：{req.major}\n"
        f"- 优先策略：{req.strategy}\n"
        f"- 毕业规划：{req.gradPlan}\n"
        f"- 职业倾向：{req.career}\n"
        f"- 学费倾向：{req.tuition}\n\n"
        "请结合《近 3 年各省各批次投档分数线、院校特色、专业就业率、学费区间、"
        "考研/出国/考公表现》，给出个性化的志愿填报方案。\n"
        "要求：\n"
        "1) s06 冲刺院校：录取线贴近或略高于考生分数，可搏一下（2~3 所）；\n"
        "2) s07 稳妥院校：录取概率较高，分数利用充分（2~3 所）；\n"
        "3) s08 保底院校：往年录取线低于考生分数，确保有学上（2~3 所）；\n"
        "4) s09 备选建议：地域/专业/学费等维度的补充建议（1~2 所）。\n"
        "每条院校建议请写清风险标签（冲/稳/保/备）以及简短理由。\n"
        "务必遵守之前给出的 JSON 字段结构约束，不要输出 JSON 以外内容。"
    )


def _ensure_shape(data: dict, req_score: int) -> dict:
    """兜底：LLM 返回字段不齐时补全，保证前端不会崩。"""
    fallback = build_mock_plan(req_score)
    for k, v in fallback.items():
        if k not in data:
            data[k] = v
    # score 用用户真实分数回显，避免 LLM 写错
    data["score"] = req_score
    data["autoModeTag"] = data.get("autoModeTag") or fallback["autoModeTag"]
    return data


async def generate_plan(req: PlanRequest) -> dict[str, Any]:
    """
    生成方案：
    - 有 LLM Key：调用大模型，失败自动兜底 mock。
    - 无 Key：直接返回 mock（第13步"先用免费模型测试"前的阶段）。
    返回结构与 PlanResponse 严格一致。
    """
    if not llm_cfg.ENABLED:
        log.info("LLM 未启用（未配置 LLM_API_KEY），返回 mock 方案 score=%d", req.score)
        return build_mock_plan(req.score)

    prompt = build_prompt(req)
    try:
        from services.llm_client import call_llm

        result = await call_llm(prompt, req.score)
        result = _ensure_shape(result or {}, req.score)
        # 做一次 Pydantic 校验，有异常直接 fallback
        PlanResponse(**result)
        return result
    except Exception as e:
        log.error("LLM 生成失败，fallback 到 mock：%s", e)
        return build_mock_plan(req.score)
