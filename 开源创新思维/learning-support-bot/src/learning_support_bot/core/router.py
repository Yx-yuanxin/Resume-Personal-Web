"""转人工路由判断"""
from __future__ import annotations
from dataclasses import dataclass
from .classifier import ClassificationResult


@dataclass
class RoutingDecision:
    need_human: bool          # 是否需要转人工
    reason: str               # 判断理由
    assignee: str             # 建议接手人
    priority: str             # high / medium / low


# 置信度阈值：低于此值转人工
CONFIDENCE_THRESHOLD = 0.75


def route(question: str, result: ClassificationResult) -> RoutingDecision:
    """决定这个问题是 AI 直接回复还是转人工助教。

    规则：
    1. 高风险类别（学习进度掉队）→ 必转人工，高优先级
    2. 置信度低于阈值 → 转人工
    3. 技术问题 → 转技术支持
    4. 其余 → AI 直接回复草稿，助教可事后抽检

    Args:
        question: 学生原始问题
        result: 分类结果

    Returns:
        RoutingDecision
    """
    # 规则1：高风险
    if result.risk_level == "high":
        return RoutingDecision(
            need_human=True,
            reason=f"高风险类别（{result.category}），涉及学习掉队预警，必须人工介入",
            assignee="专属助教",
            priority="high",
        )

    # 规则2：置信度不足
    if result.confidence < CONFIDENCE_THRESHOLD:
        return RoutingDecision(
            need_human=True,
            reason=f"分类置信度 {result.confidence} 低于阈值 {CONFIDENCE_THRESHOLD}，怕答错",
            assignee="值班助教",
            priority="medium",
        )

    # 规则3：技术问题转技术支持
    if result.category == "technical_issue":
        return RoutingDecision(
            need_human=True,
            reason="平台技术问题需技术支持同学处理",
            assignee="平台技术支持",
            priority="medium",
        )

    # 规则4：AI 可直接回复
    return RoutingDecision(
        need_human=False,
        reason=f"分类置信度 {result.confidence}，低风险，AI 初答可直接发出，助教事后抽检",
        assignee="AI 自动回复（助教抽检）",
        priority="low",
    )
