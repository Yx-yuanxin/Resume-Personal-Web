# 接口说明 · API

## POST /api/ask

提交学生问题，返回 AI 分类、初答草稿和路由决策。

### 请求

```json
{
  "question": "老师，第三章的复利公式我没听懂，作业第5题也不会做"
}
```

### 响应

```json
{
  "result": {
    "category": "course_question",
    "confidence": 0.85,
    "matched_keywords": ["第三章", "没听懂", "作业"],
    "reply": "同学你好，关于你问的「...」，建议先回看对应章节的课件视频...",
    "routing": {
      "need_human": false,
      "reason": "分类置信度 0.85，低风险，AI 初答可直接发出，助教事后抽检",
      "assignee": "AI 自动回复（助教抽检）",
      "priority": "low"
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| category | string | 问题分类：`course_question` / `homework` / `learning_progress` / `technical_issue` / `other` |
| confidence | float | 分类置信度 0~1 |
| matched_keywords | string[] | 命中的关键词 |
| reply | string | AI 生成的初答草稿 |
| routing.need_human | bool | 是否需要转人工 |
| routing.reason | string | 路由判断理由 |
| routing.assignee | string | 建议接手人 |
| routing.priority | string | 优先级：high / medium / low |

### 错误码

| HTTP 状态码 | 说明 |
|---|---|
| 200 | 成功 |
| 400 | question 为空 |
