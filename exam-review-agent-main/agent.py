"""Agent 组装：DeepSeek 模型 + 本地工具 + MCP 笔记工具 + Skill 清单。

命令行调试：python agent.py
"""
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent  # LangChain 1.x 推荐的 ReAct agent 入口
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI

from tools import exam_countdown, list_skills, load_skill, save_review_sheet

load_dotenv()  # 从 .env 读取 DEEPSEEK_API_KEY 等配置
BASE_DIR = Path(__file__).parent

# MCP 服务配置：以 stdio 子进程方式启动 notes_server.py
# 用 sys.executable 保证子进程和当前程序使用同一个 Python（即 .venv 里的）
MCP_SERVERS = {
    "notes": {
        "command": sys.executable,
        "args": [str(BASE_DIR / "notes_server.py")],
        "transport": "stdio",
    }
}


def build_model(http_client: httpx.AsyncClient) -> ChatOpenAI:
    """DeepSeek 兼容 OpenAI 接口，所以直接用 ChatOpenAI，改 base_url 即可。"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY：请把 .env.example 复制为 .env 并填入你的 key")
    return ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        api_key=api_key,
        temperature=0.3,
        http_async_client=http_client,  # 使用本轮自己的 HTTP 客户端，见 _run 中的说明
    )


def build_system_prompt() -> str:
    """系统提示词里只放技能的名称和描述，完整说明由 load_skill 按需加载。"""
    skills = "\n".join(f"- {s['name']}：{s['description']}" for s in list_skills())
    return f"""你是「期末复习助手」，帮助学生基于自己的课程笔记复习。今天是 {datetime.now():%Y-%m-%d}。

必须遵守的规则（每一条都是硬性要求）：
1. 日期与倒计时：凡是涉及"还有几天""距离考试多久"等日期计算，必须调用 exam_countdown，禁止自己心算。
2. 笔记问答：回答任何与课程内容相关的问题，必须先调用 search_notes 检索；需要细节时再用 read_note 读全文。
   回答只能依据检索到的笔记内容，并注明出自哪篇笔记。
3. 检索不到：如果 search_notes 没有找到相关内容，直接如实回答"你的笔记中没有涉及这部分内容"，
   不得用你自己的知识补充或推测，也不要编造笔记里没有的内容。
4. 技能：当任务与下列某个技能匹配时，先调用 load_skill 加载完整说明，再严格按说明执行。
   特别地：生成复习卷、模拟题、练习题之前，必须先调用 load_skill("exam-review")。

可用技能（这里只有简介，完整说明需用 load_skill 加载）：
{skills}"""


async def _run(messages: list[dict], on_message) -> None:
    """跑一轮对话：每产生一条新消息（模型回复 / 工具结果）就回调 on_message。"""
    # 为什么每轮都新建 httpx 客户端？
    # run_turn 每轮会新建一个事件循环，本轮结束后关闭。而 langchain-openai 默认会用一个
    # 进程级缓存（lru_cache）的 AsyncClient，它的 keep-alive 连接绑定在第一轮的事件循环上；
    # 第二轮复用这些连接时就会报 "Event loop is closed"。
    # 解决办法：客户端跟着本轮走，async with 结束时自动关闭，生命周期和事件循环保持一致。
    async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=10)) as http_client:
        model = build_model(http_client)  # 先建模型：key 缺失时尽早报错，不必启动 MCP 子进程
        client = MultiServerMCPClient(MCP_SERVERS)
        # 在一个 session 内完成整轮对话：MCP 子进程只启动一次，而不是每次工具调用都重启
        async with client.session("notes") as session:
            mcp_tools = await load_mcp_tools(session)  # 把 MCP 工具转换成 LangChain 工具
            agent = create_agent(
                model=model,
                tools=[load_skill, exam_countdown, save_review_sheet, *mcp_tools],
                system_prompt=build_system_prompt(),
            )
            # stream_mode="updates"：每执行完一个节点（model 推理 / tools 执行）就产出一次增量
            async for update in agent.astream({"messages": messages}, stream_mode="updates"):
                for node_output in update.values():
                    for msg in (node_output or {}).get("messages", []):
                        on_message(msg)


def run_turn(messages: list[dict], on_message) -> None:
    """同步入口（Streamlit 和命令行都用它）。messages 形如 [{"role": "user", "content": "..."}]。"""
    # Windows 下 MCP 要启动 stdio 子进程，只有 ProactorEventLoop 支持子进程，
    # SelectorEventLoop 不支持。这里显式指定，避免全局策略被其他库改掉后出问题。
    loop_factory = asyncio.ProactorEventLoop if sys.platform == "win32" else None
    # 回调 on_message 会直接操作 Streamlit 界面，所以 agent 必须在当前脚本线程里运行，
    # 不能放到后台线程（后台线程里调用 st.* 不会渲染）
    with asyncio.Runner(loop_factory=loop_factory) as runner:
        runner.run(_run(messages, on_message))


if __name__ == "__main__":
    # 命令行多轮对话，便于脱离界面调试
    history: list[dict] = []

    def show(msg):
        for call in getattr(msg, "tool_calls", None) or []:
            print(f"  🔧 {call['name']}({call['args']})")
        if msg.type == "tool":
            print(f"  📄 {msg.name} → {str(msg.text)[:120]!r}")
        elif msg.type == "ai" and not msg.tool_calls:
            history.append({"role": "assistant", "content": str(msg.text)})
            print(f"助手：{msg.text}")

    while (question := input("\n你：").strip()) not in ("", "exit"):
        history.append({"role": "user", "content": question})
        run_turn(history, show)
