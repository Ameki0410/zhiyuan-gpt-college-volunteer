# services/consult_service.py —— 专业顾问问答业务逻辑
# 默认选项：
#   UI = 顶部Tab（由前端实现）；边界控制 = 纯系统 Prompt；
#   知识库 = L1 本科专业目录 JSON；上下文 = 前端 localStorage 带 history 过来。
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import httpx

from config import llm as cfg
from data.major_catalog import get_catalog

log = logging.getLogger(__name__)

REFUSE_TEXT = (
    "抱歉，我是高考专业顾问，只回答**高考选专业、专业学习内容、就业前景/考研发展**"
    "相关的问题，其他问题无法解答。"
)

# ---------- 硬拒答关键词（兜底边界：命中直接拒，不花钱调 LLM）----------
_HARD_REFUSE_RE = re.compile(
    r"(怎么追|撩妹|谈恋爱|减肥|健身食谱|手机.*推荐|电脑.*推荐|帮我.*写.*作文|"
    r"作弊|泄题|答案|帮我.*盗号|怎么黑|攻击网站|多少钱.*买|"
    r"今天天气|天气预报|几点了|现在时间|"
    r"写一首诗|写篇小说|翻译.*英文|帮我编.*程序|修电脑|怎么装系统|"
    r"医疗诊断|我得.*病|吃什么药|抑郁.*怎么办|心理.*咨询.*治疗|"
    r"政治敏感|领导人|台独|港独|新疆|民族歧视|男女.*必须|"
    r"彩票|买彩票|博彩|赌博|怎么赚钱快|借钱|"
    r"gpt|你是|你是谁|自我介绍|你能做什么|siri|小爱同学|训练数据)")

# ---------- 放行（相关）关键词 ----------
_ALLOW_RE = re.compile(
    r"(专业|学科|门类|就业|前景|发展|考研|读研|考公|公务员|选科|选什么|"
    r"课程|学什么|内容|修业|学位|学制|授予|院校|大学|学院|排名|"
    r"志愿|填报|高考|分数|位次|报考|适合|推荐|对比|和.*的区别|"
    r"薪资|工资|收入|待遇|年薪|月薪|就业方向|行业|公司|企业|"
    r"考不考数学|数学要求|英语要求|化学|物理|生物|政治|历史|地理|技术|"
    r"就业率|转行|转专业|考研方向|出国|留学|保研|深造|"
    r"本科|专科|新增|撤销|代码|0809|0101|1002|四位|六位.*专业|"
    r"职业规划|未来发展|未来十年|行业趋势|风口|天花板|裁员|"
    r"人工智能|AI|大模型|芯片|半导体|新能源|电池|医药|医疗|"
    r"计算机|软件|电气|临床|口腔|法学|师范|教师|机械|土木|自动化|电子|通信)")


# ---------- 系统提示词（边界控制主阵地）----------
_SYSTEM_PROMPT = """你是「智愿 · AI 高考专业顾问」，服务对象是即将参加高考填报志愿的高中生与家长。

【必须遵守的硬性边界】：
1) 你只回答以下 8 类问题，其他问题一律不回答，且必须严格一字不差返回固定拒答文案：
   拒答文案 = "抱歉，我是高考专业顾问，只回答**高考选专业、专业学习内容、就业前景/考研发展**相关的问题，其他问题无法解答。"
2) 8 类可答范围：
   · 专业信息：某专业的学习内容、课程设置、培养方案、修业年限、授予学位、专业代码、学科门类
   · 选科/选考要求：某专业在某省份的选科限制、选科组合适配
   · 院校/排名：某专业在国内/省内高校的开设情况、学科评估、就业口碑
   · 就业 & 薪酬：就业方向、典型雇主、入行起薪、职业天花板、行业发展趋势
   · 发展 & 考研：研究生方向推荐、跨考可能性、是否需要读研/读博、留学方向
   · 性格/分数/选科适配：给定分数/选科/性格，推荐合适的专业
   · 专业对比：A 专业和 B 专业的区别、怎么选、就业/考研/薪酬对比
   · 新专业/冷门专业解读：新开设专业、小众专业值不值得报
3) 绝对不能出现：
   · 任何非高考选专业范畴的建议（手机/电脑/游戏/减肥/写代码/写诗/翻译等全部拒答）
   · 需要执业资质的内容：医疗诊断、开处方、心理疾病治疗与诊断、法律咨询（可回答"法学专业学什么"，但不能给法律意见）
   · 性别/地域/民族/宗教歧视性内容（必须强调：选择专业与性别/地域无关，应结合兴趣与能力）
   · 任何鼓励作弊、违法、不道德的内容

【回答风格（专业顾问型）】：
· 语气客观专业，数据详实，分点回答更清晰。
· 能结合用户的分数、选科、位次给出建议时，优先提醒用户"结合实际位次与选科综合判断"。
· 涉及具体某专业的学习内容/学位/修业年限时，必须优先使用下方"参考专业知识库"里的素材，禁止与素材矛盾（例如素材里写的是五年制就不能说四年）。
· 任何你不确定的内容，必须明确说"该数据每年可能变化，建议以教育部最新《普通高等学校本科专业目录》和各高校当年招生章程为准"，不能瞎编。
· 回答完正文后，如该问题能关联到"本平台填报方案功能"，最后加一行短引导：
  "📌 想结合分数+选科+偏好生成个性化志愿方案？可使用本 App 顶部「填报方案」Tab 一键 AI 生成。"
  （但如果已经在拒答场景，不得加这一行。）
"""


@dataclass
class ConsultReply:
    reply: str
    source: str          # llm / mock / refuse
    hits: list[str]      # 命中的专业名（给前端高亮/展示"参考来源"）


def _hard_refuse_check(message: str) -> str | None:
    """硬兜底：明显越界直接返回拒答，不花钱调 LLM。"""
    if _HARD_REFUSE_RE.search(message):
        return REFUSE_TEXT
    return None


def _is_soft_on_topic(message: str) -> bool:
    """软判断是否在领域内。放行任一关键词即判 on-topic。"""
    return bool(_ALLOW_RE.search(message))


def _assemble_messages(user_message: str, history: list[dict] | None,
                       hits_names: list[str]) -> list[dict]:
    # 检索素材注入：把命中的专业目录 JSON 原文作为 system prompt 的一部分
    cat = get_catalog()
    hits = cat.search(user_message, top_k=5)
    # 同时看历史里有没有提到专业名
    if history:
        for h in history[-4:]:
            c = h.get("content", "") if isinstance(h, dict) else ""
            for extra in cat.search(c, top_k=3):
                if extra.name not in {x.name for x in hits}:
                    hits.append(extra)
        hits = hits[:6]
    hits_names.clear()
    hits_names.extend(it.name for it in hits)
    knowledge_block = cat.format_for_prompt(hits)

    system_text = _SYSTEM_PROMPT + "\n\n" + knowledge_block

    messages = [{"role": "system", "content": system_text}]
    for h in history or []:
        if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
            c = h.get("content")
            if c:
                # 只保留最近 6 轮，避免 prompt 过长
                messages.append({"role": h["role"], "content": str(c)[:800]})
    if len(messages) > 13:
        messages = [messages[0]] + messages[-12:]
    messages.append({"role": "user", "content": user_message[:1500]})
    return messages


async def _call_llm(messages: list[dict]) -> str:
    headers = {
        "Authorization": f"Bearer {cfg.API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": cfg.MODEL,
        "temperature": 0.4,
        "messages": messages,
    }
    async with httpx.AsyncClient(timeout=cfg.TIMEOUT) as client:
        r = await client.post(f"{cfg.BASE_URL}/chat/completions",
                              headers=headers, json=body)
        if r.status_code != 200:
            log.error("Consult LLM HTTP %s: %s", r.status_code, r.text[:300])
            raise RuntimeError(f"LLM HTTP {r.status_code}")
        data = r.json()
    return data["choices"][0]["message"]["content"]


# ---------- mock 回复（未配置 Key 时用，保证本地能体验完整交互）----------
_MOCK_ON_TOPIC_REPLY = (
    "（本地演示版：未配置 LLM_API_KEY 时的 mock 回复；配置真实 Key 后将调用大模型给出更详细的回答）\n\n"
    "根据你提到的专业方向，建议从以下 4 个维度综合判断：\n"
    "1. 「学什么」：去教育部《普通高等学校本科专业目录》查该专业的修业年限、授予学位、核心课程；\n"
    "2. 「适合谁」：结合自己选科限制（比如临床医学多数要求物化同选）、分数位次、兴趣特长；\n"
    "3. 「就业」：关注该专业对应的典型雇主行业、入行门槛、薪资区间、是否需要读研；\n"
    "4. 「发展」：行业处于上升/稳定/下行哪一段，未来 5~10 年有没有结构性机会。\n\n"
    "📌 想结合分数+选科+偏好生成个性化志愿方案？可使用本 App 顶部「填报方案」Tab 一键 AI 生成。"
)


async def consult(user_message: str, history: list[dict] | None = None,
                  *, on_topic_override: bool | None = None) -> ConsultReply:
    """对外主入口：一次提问-回答。"""
    user_message = (user_message or "").strip()
    if not user_message:
        return ConsultReply(reply="请问点关于高考选专业、专业内容、就业/考研的问题吧～",
                            source="refuse", hits=[])

    # 1) 硬关键词拒答
    hard = _hard_refuse_check(user_message)
    if hard:
        return ConsultReply(reply=hard, source="refuse", hits=[])

    # 2) 是否 on-topic（显式指定则用指定；否则走关键词+LLM自行边界双判）
    on_topic = on_topic_override if on_topic_override is not None else _is_soft_on_topic(user_message)

    # 3) 未配 Key：直接给 mock（on-topic 场景），或拒答
    if not cfg.ENABLED:
        if on_topic:
            return ConsultReply(reply=_MOCK_ON_TOPIC_REPLY, source="mock", hits=[])
        return ConsultReply(reply=REFUSE_TEXT, source="refuse", hits=[])

    # 4) 配了 Key：调 LLM（系统 Prompt 内部含严格拒答指令，越界由 LLM 输出拒答话术）
    hits_names: list[str] = []
    messages = _assemble_messages(user_message, history, hits_names)
    try:
        reply = await _call_llm(messages)
    except Exception as e:
        log.exception("Consult LLM call failed: %s", e)
        return ConsultReply(reply=(
            "抱歉，AI 服务暂时繁忙，请稍后再试。\n"
            "你可以先试试顶部「填报方案」Tab 生成个性化志愿方案。"
        ), source="mock", hits=[])

    reply = (reply or "").strip()
    # 双重兜底：LLM 忘记拒答时，如果问题明显越界，就把回复替换成拒答
    if not on_topic and ("抱歉" not in reply[:10] or "无法解答" not in reply):
        reply = REFUSE_TEXT
    return ConsultReply(reply=reply, source="llm", hits=hits_names)
