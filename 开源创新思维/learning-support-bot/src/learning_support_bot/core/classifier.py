"""问题意图分类器 - 基于关键词规则"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ClassificationResult:
    category: str          # 分类标签
    confidence: float     # 置信度 0~1
    matched_keywords: List[str]
    risk_level: str       # low / medium / high


# 分类规则：类别 -> 关键词列表
DEFAULT_RULES: Dict[str, List[str]] = {
    "course_question": [
        "课程", "课件", "讲义", "第一章", "第二章", "知识点", "老师讲",
        "没听懂", "什么意思", "概念", "原理", "定义", "复习",
    ],
    "homework": [
        "作业", "习题", "练习", "题目", "答案", "提交", "截止", "ddl",
        "怎么写", "怎么做", "第几题", "作业不会",
    ],
    "learning_progress": [
        "进度", "跟不上", "掉队", "落后", "赶不上", "学习计划",
        "打卡", "学习记录", "进度条", "学到哪",
    ],
    "technical_issue": [
        "登录", "打不开", "闪退", "bug", "报错", "视频看不了",
        "APP", "app", "客户端", "网页", "加载", "白屏",
    ],
    "other": [],  # 兜底
}

# 高风险类别（必须人工处理）
HIGH_RISK_CATEGORIES = {"learning_progress"}


def classify(text: str, rules: Dict[str, List[str]] | None = None) -> ClassificationResult:
    """对学生问题做意图分类。

    Args:
        text: 学生输入的问题文本
        rules: 自定义规则，默认用 DEFAULT_RULES

    Returns:
        ClassificationResult
    """
    rules = rules or DEFAULT_RULES
    text_lower = text.lower()

    scores: Dict[str, List[str]] = {}
    for category, keywords in rules.items():
        if not keywords:
            continue
        hits = [kw for kw in keywords if kw.lower() in text_lower]
        if hits:
            scores[category] = hits

    if not scores:
        return ClassificationResult(
            category="other",
            confidence=0.3,
            matched_keywords=[],
            risk_level="low",
        )

    # 取得分最高的类别
    best_category = max(scores, key=lambda c: len(scores[c]))
    best_hits = scores[best_category]

    # 简单置信度：命中关键词数 / 4（命中4个以上认为很确定）
    confidence = min(1.0, 0.5 + len(best_hits) * 0.15)

    risk = "high" if best_category in HIGH_RISK_CATEGORIES else "low"

    return ClassificationResult(
        category=best_category,
        confidence=round(confidence, 2),
        matched_keywords=best_hits,
        risk_level=risk,
    )
