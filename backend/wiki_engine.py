# -*- coding: utf-8 -*-
"""LLM-Wiki 知识沉淀引擎（本项目核心创新）。

职责：
1. extract_candidate：问答完成后，把 (问题, 回答, 来源) 抽取为结构化知识条目（默认待审核）；
2. 审核：approve（生效，参与检索）/ reject（驳回）；
3. 维护：edit / delete / list；
4. search_active：只检索【已生效】条目，供 rag_engine 优先调用。

知识条目 Schema 与需求文档完全一致：
{knowledge_title, knowledge_content, source_type, source_reference, create_time, status}
"""
import json
import time

import config
import llm_client

STATUS_PENDING = "待审核"
STATUS_ACTIVE = "已生效"


# ------------------------------------------------------------ 存储
def _load_all():
    if config.WIKI_ENTRIES_PATH.exists():
        return json.loads(config.WIKI_ENTRIES_PATH.read_text(encoding="utf-8"))
    return []


def _save_all(entries):
    config.WIKI_ENTRIES_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------ 查询
def list_entries(status=None, source_type=None):
    entries = _load_all()
    if status:
        entries = [e for e in entries if e["status"] == status]
    if source_type:
        entries = [e for e in entries if e["source_type"] == source_type]
    return sorted(entries, key=lambda e: e["create_time"], reverse=True)


def get_entry(entry_id):
    return next((e for e in _load_all() if e["id"] == entry_id), None)


def stats():
    entries = _load_all()
    return {
        "total": len(entries),
        STATUS_PENDING: sum(1 for e in entries if e["status"] == STATUS_PENDING),
        STATUS_ACTIVE: sum(1 for e in entries if e["status"] == STATUS_ACTIVE),
        "internal": sum(1 for e in entries if e["source_type"] == "internal"),
        "external": sum(1 for e in entries if e["source_type"] == "external"),
    }


# ------------------------------------------------------------ 审核 / 维护
def approve(entry_id):
    entries = _load_all()
    for e in entries:
        if e["id"] == entry_id:
            e["status"] = STATUS_ACTIVE
            e["approve_time"] = _now()
            _save_all(entries)
            return e
    return None


def reject(entry_id):
    entries = _load_all()
    for e in entries:
        if e["id"] == entry_id:
            e["status"] = STATUS_PENDING
            e["rejected"] = True
            _save_all(entries)
            return e
    return None


def edit_entry(entry_id, title=None, content=None, activate=False):
    entries = _load_all()
    for e in entries:
        if e["id"] == entry_id:
            if title is not None:
                e["knowledge_title"] = title
            if content is not None:
                e["knowledge_content"] = content
            if activate:
                e["status"] = STATUS_ACTIVE
                e["approve_time"] = _now()
            e["update_time"] = _now()
            _save_all(entries)
            return e
    return None


def delete_entry(entry_id):
    entries = _load_all()
    remain = [e for e in entries if e["id"] != entry_id]
    if len(remain) == len(entries):
        return False
    _save_all(remain)
    return True


# ------------------------------------------------------------ 知识抽取（核心）
_EXTRACT_PROMPT = """你是一个企业制度知识管理助手。请把下面这组【问答对】提炼为一条结构化知识条目。

要求：
1. knowledge_title：不超过 20 字的疑问式或名词式标题（如"出差住宿报销标准"）；
2. knowledge_content：80 字以内、自包含的结论性知识（脱离原文也能看懂，保留关键数字与条件）；
3. source_type 与 source_reference 直接沿用资料来源；
4. 只输出 JSON 对象，不要输出任何其他文字。

【用户问题】{question}
【系统回答】{answer}
【资料来源】{source_reference}
【来源类型】{source_type}

输出格式：
{{"knowledge_title": "...", "knowledge_content": "...", "source_type": "{source_type}", "source_reference": "{source_reference}"}}"""


def _mock_extract(question, answer, source_type, source_ref):
    """MOCK 降级：无 LLM Key 时用规则抽取（演示链路完整可讲）。"""
    title = question.strip().rstrip("？?。").replace("请问", "").replace("一下", "")
    title = title[:20] if title else "未命名知识"
    # 取回答中最长的实质行作为知识内容（跳过"依据制度原文"类结构性短行）
    lines = [ln.strip().lstrip("·-").strip() for ln in answer.split("\n")]
    lines = [ln for ln in lines if len(ln) >= 10]
    content = max(lines, key=len) if lines else answer[:100]
    content = content[:100] + ("…" if len(content) > 100 else "")
    return {
        "knowledge_title": title,
        "knowledge_content": content,
        "source_type": source_type,
        "source_reference": source_ref,
    }


def extract_candidate(question, answer, sources):
    """问答完成后自动抽取知识候选条目，status 默认【待审核】。

    :param sources: compliance.build_sources 的输出
    :return: 新条目 dict；无有效来源或抽取失败返回 None
    """
    if not sources:
        return None  # 无溯源的回答（含无匹配兜底）不沉淀知识

    primary = sources[0]
    source_type = primary["type"]
    source_ref = primary["ref"]

    try:
        if llm_client.is_llm_ready():
            result = llm_client.llm_chat_json([{
                "role": "user",
                "content": _EXTRACT_PROMPT.format(
                    question=question, answer=answer,
                    source_type=source_type, source_reference=source_ref),
            }])
            if not result or "knowledge_title" not in result:
                raise ValueError("抽取结果不完整")
            result["source_type"] = source_type
            result["source_reference"] = source_ref
        else:
            result = _mock_extract(question, answer, source_type, source_ref)
    except llm_client.LLMUnavailable:
        result = _mock_extract(question, answer, source_type, source_ref)

    entry = {
        "id": f"wk_{int(time.time() * 1000)}",
        "knowledge_title": str(result["knowledge_title"])[:50],
        "knowledge_content": str(result["knowledge_content"])[:300],
        "source_type": result["source_type"],
        "source_reference": str(result.get("source_reference", source_ref))[:200],
        "create_time": _now(),
        "status": STATUS_PENDING,   # 新条目默认待审核，管理员确认后才参与检索
    }
    entries = _load_all()
    entries.append(entry)
    _save_all(entries)
    return entry


# ------------------------------------------------------------ 已生效条目检索（供 RAG 优先调用）
import re


def _bigrams(text: str) -> set:
    text = re.sub(r"[\s，。；：、！？!?.,;:]", "", text)
    return {text[i:i + 2] for i in range(len(text) - 1)} if len(text) > 1 else set()


def search_active(query, source_type=None, top_k=None):
    """只检索已生效条目。source_type 用于 scope 隔离（internal/external/None=全部）。

    评分：字符 2-gram 集合余弦（与文档检索口径一致），标题命中加权 ×2，
    保证"标题与问题高度相关"的条目优先浮出。
    """
    top_k = top_k or config.WIKI_TOP_K
    entries = [e for e in _load_all() if e["status"] == STATUS_ACTIVE]
    if source_type:
        entries = [e for e in entries if e["source_type"] == source_type]

    qbg = _bigrams(query)
    if not qbg:
        return []

    scored = []
    for e in entries:
        title_bg = _bigrams(e["knowledge_title"])
        text_bg = _bigrams(e["knowledge_title"] + e["knowledge_content"])
        if not text_bg:
            continue
        overlap = qbg & text_bg
        if len(overlap) < 2:
            continue  # 至少命中 2 个 bigram，防止单字面巧合导致误召回
        weighted = sum(2 if b in title_bg else 1 for b in overlap)
        denom = (len(qbg) * len(text_bg)) ** 0.5
        score = weighted / denom if denom else 0.0
        if score >= config.WIKI_SIM_THRESHOLD:
            scored.append({**e, "score": round(score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
