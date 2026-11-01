"""命令行 Demo - 直接看分类、初答、路由结果"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from learning_support_bot.core import classify, draft_reply, route


def main():
    print("=" * 55)
    print("  学习支持助手 · 命令行 Demo")
    print("  输入学生问题，回车查看 AI 处理结果；输入 q 退出")
    print("=" * 55)

    while True:
        try:
            q = input("\n学生问题> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q.lower() in ("q", "quit", "exit"):
            break

        cls = classify(q)
        reply = draft_reply(q, cls)
        routing = route(q, cls)

        print(f"\n  [分类] {cls.category}  (置信度 {cls.confidence}, 风险 {cls.risk_level})")
        print(f"  [命中关键词] {cls.matched_keywords}")
        print(f"  [AI 初答] {reply}")
        print(f"  [路由] {'转人工 → ' + routing.assignee if routing.need_human else 'AI 直接回复'}")
        print(f"         理由：{routing.reason}")
        print(f"         优先级：{routing.priority}")


if __name__ == "__main__":
    main()
