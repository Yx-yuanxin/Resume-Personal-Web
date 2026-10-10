# -*- coding: utf-8 -*-
"""冒烟测试：不启动 HTTP 服务，直接验证 RAG + LLM-Wiki + 合规全链路逻辑。

运行：python smoke_test.py  （在 backend 目录下）
覆盖场景：
  1. 内部问答（应命中Wiki+文档，来源标注 internal）
  2. 外部问答（应附外部提示横幅）
  3. 无匹配（应返回"暂无相关制度或公开资料"）
  4. Wiki 沉淀（问答后生成待审核条目）→ 审核 → 再次提问命中
  5. scope 隔离（仅内部库检索时外部问题应无匹配）
"""
import importlib

import rag_engine
import wiki_engine


def check(name, cond, detail=""):
    status = "✅ PASS" if cond else "❌ FAIL"
    print(f"{status} | {name} {('- ' + str(detail)[:80]) if detail and not cond else ''}")
    return cond


def main():
    results = []

    # ---- ① 内部问答（Wiki 优先命中） ----
    r1 = rag_engine.answer_question("公司的工作时间是怎么规定的？", "auto")
    results.append(check("① 内部问答-自动分类为internal", r1["question_scope"] == "internal", r1["question_scope"]))
    results.append(check("① 内部问答-Wiki命中", r1.get("wiki_hit") is True))
    results.append(check("① 内部问答-回答含来源", len(r1["sources"]) >= 1 and
                         all(s["type"] == "internal" for s in r1["sources"])))
    results.append(check("① 内部问答-内部来源无外部提示", r1["external_disclaimer"] == ""))

    # ---- ② 外部问答 ----
    r2 = rag_engine.answer_question("弹性退休政策是什么？", "auto")
    results.append(check("② 外部问答-自动分类为external", r2["question_scope"] == "external", r2["question_scope"]))
    results.append(check("② 外部问答-强制外部提示", "公开网络" in r2["external_disclaimer"]))

    # ---- ③ 无匹配 ----
    r3 = rag_engine.answer_question("公司食堂菜单有哪些菜？", "internal")
    results.append(check("③ 无匹配-合规兜底", r3["no_match"] is True and
                         "暂无相关制度" in r3["answer"]))
    results.append(check("③ 无匹配-不沉淀知识", r3["wiki_candidate"] is None))

    # ---- ④ Wiki 沉淀闭环 ----
    before = len(wiki_engine.list_entries(status="待审核"))
    r4 = rag_engine.answer_question("婚假产假各有多少天？", "internal")
    results.append(check("④ Wiki沉淀-生成待审核候选", r4["wiki_candidate"] is not None and
                         r4["wiki_candidate"]["status"] == "待审核"))
    after = len(wiki_engine.list_entries(status="待审核"))
    results.append(check("④ Wiki沉淀-待审核数+1", after == before + 1, f"{before}->{after}"))

    # 审核通过 → 生效
    cid = r4["wiki_candidate"]["id"]
    wiki_engine.approve(cid)
    entry = wiki_engine.get_entry(cid)
    results.append(check("④ 审核通过-状态已生效", entry["status"] == "已生效"))

    # 再次提问同类问题 → Wiki 命中
    r5 = rag_engine.answer_question("请问婚假有多少天？", "internal")
    results.append(check("④ 生效后优先命中Wiki", r5.get("wiki_hit") is True))

    # ---- ⑤ 内外隔离 ----
    r6 = rag_engine.answer_question("弹性退休政策是什么？", "internal")
    results.append(check("⑤ 隔离-仅内部库检索外部问题无匹配", r6["no_match"] is True))
    r7 = rag_engine.answer_question("出差住宿报销标准？", "external")
    results.append(check("⑤ 隔离-仅外部库检索内部问题无匹配", r7["no_match"] is True))

    print("-" * 56)
    passed = sum(results)
    print(f"结果：{passed}/{len(results)} 通过")
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
