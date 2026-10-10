# -*- coding: utf-8 -*-
"""RAG 问答主链路：问题分类 → 双库检索 → 生成 → 合规出口 → Wiki 知识沉淀。

检索优先级（LLM-Wiki 核心机制）：
  ① 已生效 Wiki 条目（结构化、精炼、经管理员审核）
  ② 原始文档分块（内部制度 PDF/Word 或外部采集网页）
"""
import json

import compliance
import config
import llm_client
import wiki_engine
from vector_store import internal_store, external_store

# ---------------------------------------------------------------- 问题分类
# 演示级规则词典（答辩点：规则可解释、零延迟；生产可叠加 LLM 分类）
INTERNAL_HINTS = ["公司", "我们", "本单位", "报销", "考勤", "请假", "差旅", "出差",
                  "加班", "工资", "薪资", "福利", "部门", "员工手册", "内部", "制度",
                  "作息", "休假", "年假", "试用期", "离职"]
EXTERNAL_HINTS = ["国家", "法规", "法律", "政策", "行业", "公开", "最新",
                  "劳动法", "税法", "社保局", "官方", "国家标准", "行业标准",
                  "发布", "趋势", "新闻报道"]


def classify_question(question: str, use_llm: bool = True) -> str:
    """返回 internal / external / mixed。用户指定 scope 时不走本函数。"""
    q = question.lower()
    internal_score = sum(1 for k in INTERNAL_HINTS if k in q)
    external_score = sum(1 for k in EXTERNAL_HINTS if k in q)

    if internal_score and external_score:
        return "mixed"
    if internal_score:
        return "internal"
    if external_score:
        return "external"

    # 规则无法判断时尝试 LLM 分类（可选）
    if use_llm and llm_client.is_llm_ready():
        try:
            result = llm_client.llm_chat_json([{
                "role": "user",
                "content": (
                    "判断以下问题应检索哪类知识库，只输出 JSON："
                    '{"scope": "internal|external|mixed"}。\n'
                    "internal=企业内部制度（考勤/报销/办公规范等）；"
                    "external=公开网络信息（法规/行业/新闻等）；"
                    "mixed=两者都需要。\n问题：" + question),
            }])
            if result and result.get("scope") in ("internal", "external", "mixed"):
                return result["scope"]
        except llm_client.LLMUnavailable:
            pass
    return "mixed"


# ---------------------------------------------------------------- 双库检索（scope 严格路由，内外隔离）
def retrieve(question: str, scope: str):
    """按 scope 检索，返回 (wiki_hits, doc_hits, sources)。

    scope: internal → 只查内部库；external → 只查外部库；mixed → 两库都查。
    """
    wiki_hits, doc_hits = [], []

    wiki_scope = None if scope == "mixed" else scope
    wiki_hits = wiki_engine.search_active(question, source_type=wiki_scope)

    stores = []
    if scope in ("internal", "mixed"):
        stores.append((internal_store, "internal"))
    if scope in ("external", "mixed"):
        stores.append((external_store, "external"))

    for store, stype in stores:
        doc_hits += [(h, stype) for h in
                     store.search(question, top_k=config.TOP_K,
                                  threshold=config.SIM_THRESHOLD)]

    # 合并去重后按分数排序，统一打上来源类型
    merged = [{"text": h["text"], "source_ref": h["source_ref"],
               "score": h["score"], "type": stype} for h, stype in doc_hits]
    merged.sort(key=lambda x: x["score"], reverse=True)
    merged = merged[:config.TOP_K]

    # 组装溯源（Wiki 优先展示）
    sources = compliance.build_sources(wiki_hits, wiki_scope or "mixed", kind="wiki")
    for m in merged:
        sources.append({
            "type": m["type"], "kind": "document",
            "ref": m["source_ref"], "score": m["score"],
            "snippet": m["text"][:80] + "…",
        })
    return wiki_hits, merged, sources


# ---------------------------------------------------------------- 回答生成
_ANSWER_PROMPT = """你是企业制度问答助手"东知道"。请严格依据【参考资料】回答用户问题。

硬性要求：
1. 只使用参考资料中的信息，禁止编造；资料不足以回答时明确说明；
2. 回答末尾单独一行列出引用来源（文档名/网页标题）；
3. 涉及外部公开资料时注明"（公开网络资料）"；
4. 语言简洁、条理清晰，关键数字与条件务必保留。

【参考资料】
{context}

【用户问题】{question}"""


def _build_context(wiki_hits, doc_hits, scope):
    lines = []
    for w in wiki_hits:
        lines.append(f"[Wiki已生效知识|{w['source_type']}] {w['knowledge_title']}：{w['knowledge_content']}")
    for d in doc_hits:
        lines.append(f"[{'内部制度文档' if d['type'] == 'internal' else '公开网络资料'}|{d['source_ref']}] {d['text']}")
    return "\n".join(lines)


def _mock_answer(question, wiki_hits, doc_hits, scope):
    """MOCK 模板回答：无 LLM Key 时由检索片段拼接，保证演示链路完整。"""
    parts = []
    if wiki_hits:
        parts.append("根据已审核知识库：")
        for w in wiki_hits[:2]:
            parts.append(f"· {w['knowledge_title']}——{w['knowledge_content']}")
    if doc_hits:
        parts.append("依据制度原文：")
        for d in doc_hits[:3]:
            parts.append(f"· 《{d['source_ref']}》：{d['text'][:150]}")
    answer = "\n".join(parts)
    answer += "\n\n（当前为 MOCK 演示模式：配置 LLM_API_KEY 后可获得大模型生成回答）"
    return answer


def answer_question(question: str, scope: str = "auto") -> dict:
    """问答主入口。

    :param scope: auto(自动分类) / internal / external / mixed
    :return: compliance.apply_compliance 的合规回答体 + wiki_candidate
    """
    # ① 分类
    if scope == "auto":
        scope = classify_question(question)

    # ② 双库检索：已生效 Wiki 优先 + 原始文档
    wiki_hits, doc_hits, sources = retrieve(question, scope)

    # ③ 无匹配 → 合规兜底（禁止编造）
    if not wiki_hits and not doc_hits:
        return {**compliance.no_match_response(question, scope), "wiki_candidate": None}

    # ④ 生成回答
    context = _build_context(wiki_hits, doc_hits, scope)
    try:
        if llm_client.is_llm_ready():
            answer_text = llm_client.llm_chat([{
                "role": "user",
                "content": _ANSWER_PROMPT.format(context=context, question=question),
            }])
        else:
            answer_text = _mock_answer(question, wiki_hits, doc_hits, scope)
    except llm_client.LLMUnavailable:
        answer_text = _mock_answer(question, wiki_hits, doc_hits, scope)

    # ⑤ 合规出口
    result = compliance.apply_compliance(question, answer_text, sources, scope)

    # ⑥ LLM-Wiki 知识沉淀：问答完成自动抽取候选（待审核）
    candidate = wiki_engine.extract_candidate(question, answer_text, sources)
    result["wiki_hit"] = bool(wiki_hits)
    result["wiki_candidate"] = candidate
    return result


# ---------------------------------------------------------------- 对话历史
def save_conversation(question, result):
    import time
    history = []
    if config.CONVERSATIONS_PATH.exists():
        history = json.loads(config.CONVERSATIONS_PATH.read_text(encoding="utf-8"))
    history.append({
        "id": f"cv_{int(time.time() * 1000)}",
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"],
        "scope": result.get("question_scope", "auto"),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    # 只保留最近 200 条
    history = history[-200:]
    config.CONVERSATIONS_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return history
