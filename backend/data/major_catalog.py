# data/major_catalog.py —— 本科专业目录知识库检索（L1 层 RAG 素材注入）
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)

_JSON_PATH = Path(__file__).resolve().parent / "undergraduate_majors.json"


@dataclass
class MajorItem:
    code: str
    name: str
    cat: str            # 门类：哲学/经济学/法学/教育学/文学/历史学/理学/工学/农学/医学/管理学/艺术学
    cat2: str           # 专业类：计算机类/电子信息类/临床医学类 等
    degree: str
    years: str
    tags: list[str] = field(default_factory=list)
    note: str = ""

    def to_prompt_block(self) -> str:
        """给 LLM 读的一行素材"""
        tags_str = "/".join(self.tags) if self.tags else ""
        return (
            f"【{self.name}】 代码 {self.code} | 门类 {self.cat} · 专业类 {self.cat2} | "
            f"授予 {self.degree} · {self.years} | 标签 {tags_str or '无'}\n"
            f"  专业说明: {self.note}"
        )


@dataclass
class MajorCatalog:
    items: list[MajorItem]

    @classmethod
    def load(cls) -> "MajorCatalog":
        raw = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
        items: list[MajorItem] = []
        for r in raw:
            if not r.get("code") or not r.get("name"):
                continue
            tags = r.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in re.split(r"[,，、/]", tags) if t.strip()]
            items.append(MajorItem(
                code=r["code"], name=r["name"],
                cat=r.get("cat", ""), cat2=r.get("cat2", ""),
                degree=r.get("degree", ""), years=r.get("years", ""),
                tags=list(tags), note=r.get("note", "") or "",
            ))
        log.info("Loaded %d undergraduate majors from catalog.", len(items))
        return cls(items=items)

    # ---------- 检索：多字段关键词命中 + 专业名称模糊优先 ----------
    def search(self, query: str, *, top_k: int = 5) -> list[MajorItem]:
        if not query or not query.strip():
            return []
        q = query.strip()

        # 1. 构建候选：基于"任一关键词"匹配
        tokens = self._tokenize(q)
        if not tokens:
            return []

        scored: list[tuple[int, MajorItem]] = []
        for it in self.items:
            score = self._score(it, q, tokens)
            if score > 0:
                scored.append((score, it))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:top_k]]

    def search_code(self, code: str) -> MajorItem | None:
        code = (code or "").strip()
        if not code:
            return None
        for it in self.items:
            if it.code == code:
                return it
        return None

    def format_for_prompt(self, items: Iterable[MajorItem]) -> str:
        items = list(items)
        if not items:
            return "（本次提问未命中专业知识库白名单，请你仅基于通用常识回答，切勿编造具体专业条目。）"
        head = f"【参考专业知识库·命中 {len(items)} 条，按相关度排序】：\n"
        body = "\n\n".join(it.to_prompt_block() for it in items)
        return head + body + "\n\n"

    # ---------- helpers ----------
    @staticmethod
    def _tokenize(q: str) -> list[str]:
        """简单中文 + 英文关键词切分（够用，不需要分词器）"""
        tokens: list[str] = []
        # 保留 6 位以内纯数字（可能是专业代码）
        for m in re.findall(r"\d{4,6}", q):
            tokens.append(m)
        # 连续 2~6 位汉字序列（大概率是词）
        for m in re.findall(r"[\u4e00-\u9fa5]{2,6}", q):
            tokens.append(m)
        # 常见复合词补：直接整句的子串
        return list(dict.fromkeys(tokens))  # 去重保序

    @staticmethod
    def _score(it: MajorItem, q: str, tokens: list[str]) -> int:
        score = 0
        q_lower = q
        # 完全命中专业名 → 最高权重
        if it.name and it.name in q_lower:
            score += 100
        # 专业类（计算机类、临床医学类 等）
        if it.cat2 and it.cat2 in q_lower:
            score += 40
        # 门类
        if it.cat and it.cat in q_lower:
            score += 12
        # 专业代码（用户可能问"080901 怎么样"）
        if it.code and it.code in q_lower:
            score += 80
        # 标签（高薪、考公、AI、芯片…）
        for t in it.tags or []:
            if t and t in q_lower:
                score += 15
        # note 文本命中
        for token in tokens:
            if token and len(token) >= 2:
                if token in (it.note or ""):
                    score += 5
                if token in it.name:
                    score += 40
        return score


# 单例：程序启动后载入一次
_catalog: MajorCatalog | None = None


def get_catalog() -> MajorCatalog:
    global _catalog
    if _catalog is None:
        _catalog = MajorCatalog.load()
    return _catalog
