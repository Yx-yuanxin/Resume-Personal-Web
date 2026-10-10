# -*- coding: utf-8 -*-
"""合规过滤模块（上架硬性要求全部在此收口）。

四条硬性规则：
1. 每条回答必须携带来源溯源 sources；
2. 外部信息强制提示【该信息来源于公开网络，仅供参考，不作为企业内部制度依据】；
3. 禁止编造：无匹配知识时统一回复"暂无相关制度或公开资料"；
4. 内外隔离由 vector_store 双实例 + rag_engine 的 scope 路由共同保证。
"""
import config


def build_sources(hits, source_type: str, kind: str = "document"):
    """把检索命中结果规整为前端溯源卡片结构。

    hits: wiki 命中自带 source_type 字段；文档命中带 type 字段；
    优先使用命中自身的真实类型，source_type 仅作兜底（保证 mixed 检索时类型准确）。
    """
    out = []
    for h in hits:
        real_type = h.get("source_type") or h.get("type") or source_type
        if real_type not in ("internal", "external"):
            real_type = source_type if source_type in ("internal", "external") else "internal"
        if kind == "wiki" and h.get("knowledge_title"):
            ref = f"{h['knowledge_title']}（{h.get('source_reference', '')}）"
        else:
            ref = h.get("source_ref") or h.get("source_reference") or "未知来源"
        out.append({
            "type": real_type,
            "kind": kind,                 # document | wiki
            "ref": ref,
            "score": h.get("score", 0),
            "snippet": (h.get("text") or h.get("knowledge_content", ""))[:80] + "…",
        })
    return out


def has_external_source(sources) -> bool:
    return any(s["type"] == "external" for s in sources)


def no_match_response(question: str, scope: str) -> dict:
    """合规兜底：无匹配知识时的标准回复（禁止模型编造）。"""
    return {
        "answer": config.NO_MATCH_REPLY,
        "sources": [],
        "question_scope": scope,
        "no_match": True,
        "external_disclaimer": "",
        "compliance_note": "未检索到匹配知识，已按合规要求拒绝编造内容",
    }


def apply_compliance(question: str, answer: str, sources, scope: str, no_match=False) -> dict:
    """最终出口：组装合规回答体。"""
    external_disclaimer = config.EXTERNAL_DISCLAIMER if has_external_source(sources) else ""
    if not sources and not no_match:
        # 任何情况下 sources 为空都不允许输出"有内容"的回答
        return no_match_response(question, scope)
    return {
        "answer": answer,
        "sources": sources,
        "question_scope": scope,
        "no_match": no_match,
        "external_disclaimer": external_disclaimer,
        "compliance_note": "已通过合规检查：来源可溯" + ("，外部信息已附提示" if external_disclaimer else ""),
    }
