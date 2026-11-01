"""初答草稿生成器 - 基于模板的回复"""
from __future__ import annotations
from .classifier import ClassificationResult


# 各类别的初答模板（占位符 {question} 会被替换）
RESPONSE_TEMPLATES = {
    "course_question": (
        "同学你好，关于你问的「{question}」，建议先回看对应章节的课件视频"
        "（定位到相关知识点时间戳），如果看完仍有疑问，我会请主讲老师在下次直播"
        "时统一讲解，或安排助教一对一答疑。"
    ),
    "homework": (
        "你好，关于作业问题「{question}」：请先参考讲义第对应章节的例题解法思路。"
        "如果是具体某道题卡住了，我把它转给助教老师看一下，他会给你详细的解题步骤。"
    ),
    "learning_progress": (
        "同学你好，注意到你提到「{question}」。学习节奏的问题我们很重视，"
        "我马上通知你的专属助教跟进，他会帮你梳理当前进度、制定追赶计划，"
        "请留意稍后的消息。"
    ),
    "technical_issue": (
        "你好，关于你反馈的「{question}」技术问题：建议先尝试退出重进 / 清除缓存。"
        "如果仍未解决，我把问题转给平台技术同学，会在工作时间内回复你。"
    ),
    "other": (
        "你好，你的问题「{question}」我已经收到，正在转给对应老师查看，"
        "请稍等片刻。"
    ),
}


def draft_reply(question: str, result: ClassificationResult) -> str:
    """根据分类结果生成初答草稿。

    Args:
        question: 学生原始问题
        result: 分类结果

    Returns:
        AI 初答草稿文本
    """
    template = RESPONSE_TEMPLATES.get(result.category, RESPONSE_TEMPLATES["other"])
    # 截断问题避免模板过长
    short_q = question.strip()[:50]
    return template.format(question=short_q)
