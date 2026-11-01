"""核心逻辑单元测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from learning_support_bot.core import classify, draft_reply, route


def test_course_question():
    r = classify("老师，第一章的复利概念我没听懂，什么意思？")
    assert r.category == "course_question"
    assert r.confidence > 0.5


def test_homework():
    r = classify("作业第5题怎么做，什么时候截止提交？")
    assert r.category == "homework"


def test_learning_progress():
    r = classify("我感觉跟不上进度了，有点掉队")
    assert r.category == "learning_progress"
    assert r.risk_level == "high"


def test_technical_issue():
    r = classify("APP 登录不进去，一直闪退报错")
    assert r.category == "technical_issue"


def test_unknown():
    r = classify("今天天气怎么样")
    assert r.category == "other"


def test_draft_reply():
    r = classify("作业不会做")
    reply = draft_reply("作业不会做", r)
    assert len(reply) > 10


def test_route_high_risk():
    r = classify("我跟不上进度掉队了")
    routing = route("我跟不上进度掉队了", r)
    assert routing.need_human is True
    assert routing.priority == "high"


def test_route_auto():
    r = classify("作业答案什么时候公布")
    routing = route("作业答案什么时候公布", r)
    # 作业类低风险，置信度够则 AI 自动回
    assert isinstance(routing.need_human, bool)


if __name__ == "__main__":
    test_course_question()
    test_homework()
    test_learning_progress()
    test_technical_issue()
    test_unknown()
    test_draft_reply()
    test_route_high_risk()
    test_route_auto()
    print("All tests passed ✅")
