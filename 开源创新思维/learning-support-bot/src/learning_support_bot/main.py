"""Flask Web Demo 入口 - 学习支持助手 MVP"""
from __future__ import annotations
from flask import Flask, request, jsonify, render_template_string

from .core import classify, draft_reply, route
from .utils.logger import log_interaction

app = Flask(__name__)


INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>学习支持助手 · Demo</title>
<style>
  body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
         max-width: 720px; margin: 40px auto; padding: 0 20px; background: #f7f8fa; color: #333; }
  h1 { font-size: 22px; color: #2c5f8a; }
  .sub { color: #888; font-size: 13px; margin-bottom: 24px; }
  textarea { width: 100%; height: 90px; padding: 12px; border: 1px solid #d0d7de;
             border-radius: 8px; font-size: 15px; resize: vertical; box-sizing: border-box; }
  button { background: #2c5f8a; color: #fff; border: none; padding: 10px 28px;
           border-radius: 6px; font-size: 15px; cursor: pointer; margin-top: 12px; }
  button:hover { background: #1f4a6e; }
  .result { margin-top: 24px; background: #fff; border-radius: 8px; padding: 20px;
            border: 1px solid #e5e9ee; }
  .tag { display: inline-block; padding: 2px 10px; border-radius: 12px;
         font-size: 12px; margin-right: 8px; }
  .tag-cat { background: #e3f2fd; color: #1565c0; }
  .tag-conf { background: #f3e5f5; color: #7b1fa2; }
  .tag-human { background: #ffebee; color: #c62828; }
  .tag-auto { background: #e8f5e9; color: #2e7d32; }
  .block { margin: 12px 0; }
  .label { font-weight: 600; color: #555; font-size: 13px; }
  .reply-box { background: #f5f7fa; padding: 12px; border-radius: 6px; line-height: 1.7; }
</style>
</head>
<body>
  <h1>🎓 学习支持助手 · 北辰在线学院</h1>
  <div class="sub">MVP Demo：输入学生问题，看 AI 如何分类、生成初答、判断是否转助教</div>
  <textarea id="q" placeholder="例如：老师，第三章的复利计算公式我没听懂，作业第5题也不会做..."></textarea>
  <br>
  <button onclick="ask()">提交问题</button>
  <div id="result"></div>

<script>
async function ask() {
  const q = document.getElementById('q').value.trim();
  if (!q) return alert('请输入问题');
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: q})
  });
  const data = await res.json();
  const r = data.result;
  let html = '<div class="result">';
  html += '<div class="block"><span class="tag tag-cat">分类：' + r.category + '</span>';
  html += '<span class="tag tag-conf">置信度：' + r.confidence + '</span>';
  html += '<span class="tag ' + (r.routing.need_human ? 'tag-human' : 'tag-auto') + '">'
        + (r.routing.need_human ? '需转人工' : 'AI 自动回复') + '</span></div>';
  html += '<div class="block"><div class="label">AI 初答草稿：</div><div class="reply-box">' + r.reply + '</div></div>';
  html += '<div class="block"><div class="label">路由判断：</div>' + r.routing.reason + '<br>建议接手：<b>'
        + r.routing.assignee + '</b> · 优先级：' + r.routing.priority + '</div>';
  html += '</div>';
  document.getElementById('result').innerHTML = html;
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/api/ask", methods=["POST"])
def api_ask():
    data = request.get_json(force=True)
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is empty"}), 400

    cls = classify(question)
    reply = draft_reply(question, cls)
    routing = route(question, cls)

    # 留痕
    log_interaction(
        question=question,
        classification={
            "category": cls.category,
            "confidence": cls.confidence,
            "matched_keywords": cls.matched_keywords,
            "risk_level": cls.risk_level,
        },
        reply=reply,
        routing={
            "need_human": routing.need_human,
            "reason": routing.reason,
            "assignee": routing.assignee,
            "priority": routing.priority,
        },
    )

    return jsonify({
        "result": {
            "category": cls.category,
            "confidence": cls.confidence,
            "matched_keywords": cls.matched_keywords,
            "reply": reply,
            "routing": {
                "need_human": routing.need_human,
                "reason": routing.reason,
                "assignee": routing.assignee,
                "priority": routing.priority,
            },
        }
    })


def main():
    print("=" * 50)
    print("  学习支持助手 Demo 启动中...")
    print("  浏览器打开: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
