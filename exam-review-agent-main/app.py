"""Streamlit 界面：多轮对话 + 展示每一步工具调用。

启动：streamlit run app.py
"""
import json

import streamlit as st

from agent import BASE_DIR, run_turn
from tools import list_skills

st.set_page_config(page_title="期末复习助手", page_icon="📚")
st.title("📚 期末复习助手")
st.caption("DeepSeek + LangChain Agent · MCP 笔记检索 · Skill 按需加载")

# ---------- 侧边栏：展示 Agent 拥有的能力 ----------
with st.sidebar:
    st.subheader("🧰 工具")
    st.markdown(
        "- **本地**：load_skill、exam_countdown、save_review_sheet\n"
        "- **MCP（notes_server）**：search_notes、read_note"
    )
    st.subheader("🎯 技能")
    for skill in list_skills():
        st.markdown(f"**{skill['name']}**：{skill['description']}")
    st.subheader("📒 笔记")
    for note in sorted((BASE_DIR / "notes").glob("*.*")):
        st.markdown(f"- {note.name}")
    if st.button("🗑️ 清空对话"):
        st.session_state.messages = []
        st.rerun()

# 对话历史存在 session_state 里，Streamlit 每次重跑脚本都不会丢失
# 每条消息：{"role": ..., "content": ..., "steps": [工具调用步骤]}
if "messages" not in st.session_state:
    st.session_state.messages = []


def render_step(step: dict, box) -> None:
    """把一个步骤画到容器 box 里（实时过程和历史回放共用）。"""
    if step["kind"] == "think":
        box.markdown(f"💭 {step['text']}")
    elif step["kind"] == "call":
        args = json.dumps(step["args"], ensure_ascii=False)
        box.markdown(f"🔧 调用 **`{step['name']}`**　参数：`{args[:200]}`")
    else:  # result
        text = step["text"]
        box.markdown(f"📄 **`{step['name']}`** 返回：")
        box.code(text[:300] + ("……（已截断）" if len(text) > 300 else ""), language="text", wrap_lines=True)


def render_downloads(steps: list[dict], key_prefix: str) -> None:
    """如果本轮调用了 save_review_sheet，就提供 HTML 下载按钮。"""
    for i, step in enumerate(steps):
        if step["kind"] == "result" and step["name"] == "save_review_sheet" and "已保存：" in step["text"]:
            path = BASE_DIR / step["text"].split("已保存：", 1)[1].strip()
            if path.exists():
                st.download_button(f"⬇️ 下载 {path.name}", path.read_bytes(), file_name=path.name,
                                   mime="text/html", key=f"{key_prefix}_{i}")


# ---------- 回放历史消息 ----------
for idx, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        if m.get("steps"):
            with st.expander(f"🔍 工具调用过程（{len(m['steps'])} 步）"):
                for step in m["steps"]:
                    render_step(step, st)
        st.markdown(m["content"])
        render_downloads(m.get("steps", []), key_prefix=f"hist{idx}")


def handle_turn(prompt: str) -> None:
    """处理一轮用户输入：调用 Agent，实时展示每一步，最后保存到历史。"""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        steps, answer = [], ""
        status = st.status("Agent 思考中…", expanded=True)

        def on_message(msg) -> None:
            """Agent 每产生一条消息就回调一次：区分 工具调用 / 工具结果 / 最终回答。"""
            nonlocal answer
            text = str(msg.text)
            if msg.type == "ai" and msg.tool_calls:
                if text.strip():  # 模型调用工具前说的话，当作"思考"展示
                    steps.append({"kind": "think", "text": text})
                    render_step(steps[-1], status)
                for call in msg.tool_calls:
                    steps.append({"kind": "call", "name": call["name"], "args": call["args"]})
                    render_step(steps[-1], status)
            elif msg.type == "tool":
                steps.append({"kind": "result", "name": msg.name, "text": text})
                render_step(steps[-1], status)
            elif msg.type == "ai":  # 没有工具调用的 AI 消息就是最终回答
                answer = text

        # 只把 role/content 传给 Agent（steps 是界面展示用的）
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        try:
            run_turn(history, on_message)
            calls = sum(s["kind"] == "call" for s in steps)
            status.update(label=f"✅ 完成，共调用 {calls} 次工具", state="complete", expanded=False)
        except Exception as e:  # 如未配置 key、网络错误等，直接在界面上提示
            while isinstance(e, ExceptionGroup):  # MCP 的异步任务组会把异常包一层，拆出真实原因
                e = e.exceptions[0]
            status.update(label="❌ 出错了", state="error")
            answer = f"运行出错：{e}"

        st.markdown(answer)
        render_downloads(steps, key_prefix="live")
    st.session_state.messages.append({"role": "assistant", "content": answer, "steps": steps})


if prompt := st.chat_input("例如：帮我出一份树与二叉树的复习卷并导出"):
    handle_turn(prompt)
