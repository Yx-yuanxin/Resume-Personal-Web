# 📚 期末复习助手

> 路径 A：技术栈较完整的智能体应用

一句话介绍：把课程笔记放进 `notes/`，Agent 会检索笔记、回答问题，并按「复习卷」技能出题、导出为可打印的 HTML。

**解决的问题**：期末复习时笔记分散，自己出题费时，网上的题和自己课上讲的内容对不上。本项目只基于**自己的笔记**出题，每道题注明出处；笔记里没有的内容会如实说明，不会编造。

## 技术栈

| 层 | 技术 |
|---|---|
| 模型 | DeepSeek（`deepseek-chat`），通过 OpenAI 兼容接口调用 |
| Agent 框架 | LangChain 1.4 `create_agent`（ReAct 循环，底层运行在 LangGraph 上） |
| 界面 | Streamlit 多轮对话，实时展示每一步工具调用 |
| 自定义工具 | `exam_countdown`（考试倒计时）、`save_review_sheet`（导出 HTML 复习卷）、`load_skill`（按需加载技能） |
| MCP | `notes_server.py`（FastMCP，stdio），提供 `search_notes`、`read_note`，通过 `langchain-mcp-adapters` 接入 |
| Skill | `skills/exam-review/SKILL.md`，系统提示词只放名称和描述，正文按需加载 |

## 架构

```
用户 ──▶ app.py（Streamlit）
           │  多轮历史 + 每步工具调用展示
           ▼
       agent.py ── create_agent(DeepSeek, 工具, 系统提示词)
           │          系统提示词只列出 skill 的 name + description
           ├── 本地工具（tools.py）
           │     ├─ load_skill        → 读取 skills/<name>/SKILL.md 正文
           │     ├─ exam_countdown    → 距考试天数 + 复习节奏建议
           │     └─ save_review_sheet → Markdown 转 HTML，保存到 output/
           └── MCP 工具（stdio 子进程，每轮对话启动一次）
                 notes_server.py
                   ├─ search_notes(keyword)  → 命中行 + 上下文
                   └─ read_note(filename)    → 全文（带路径穿越防护）
                         ▲
                       notes/*.md / *.txt
```

## 目录结构

```
├─ app.py                 Streamlit 界面
├─ agent.py               Agent 组装（模型、MCP、Skill 清单、系统提示词），也可在命令行运行
├─ tools.py               本地自定义工具
├─ notes_server.py        FastMCP 笔记检索服务
├─ skills/exam-review/    复习卷技能（SKILL.md）
├─ notes/                 课程笔记（示例：数据结构 3 篇）
├─ output/                生成的复习卷 HTML（运行后自动创建，不提交）
├─ requirements.txt
└─ .env.example
```

## 环境要求

- Windows 10/11
- Python 3.12（3.11 及以上均可）
- 一个 DeepSeek API Key（https://platform.deepseek.com）

## 安装与启动（Windows PowerShell）

```powershell
# 1. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate
# 如果提示"禁止运行脚本"，先执行一次：Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 key：复制模板，然后用记事本打开 .env 填入 DEEPSEEK_API_KEY
copy .env.example .env
notepad .env

# 4. 启动网页界面（浏览器会自动打开 http://localhost:8501）
streamlit run app.py
```

不想激活虚拟环境时，也可以直接运行：`.venv\Scripts\python -m streamlit run app.py`

命令行调试模式（不启动网页）：`python agent.py`，输入 `exit` 退出。

> 终端里出现的 `INFO Starting MCP server 'notes'` 是 MCP 子进程的正常日志，不是报错。

## 推荐演示话术

| # | 输入 | 预期的工具调用链 | 演示点 |
|---|---|---|---|
| 1 | 距离 2026-12-28 的数据结构考试还有几天？该怎么安排复习？ | `exam_countdown` | 自定义工具 |
| 2 | 我笔记里 BST 的删除操作是怎么讲的？ | `search_notes` → `read_note` | MCP 检索，回答注明出处 |
| 3 | 帮我出一份《树与二叉树》的复习卷并导出 | `load_skill` → `search_notes` → `read_note` → `save_review_sheet` | Skill 按需加载 + 完整链路，可下载 HTML |
| 4 | 把刚才那份卷子的选择题改成 8 道，再导出一次 | `save_review_sheet` | 多轮对话上下文 |
| 5 | 笔记里讲红黑树的旋转了吗？ | `search_notes`（无结果，可能会换关键词再搜一次） | 边界：如实回答"笔记中没有涉及"，不用模型自身知识补充 |

## 关键设计（答辩讲解要点）

1. **Skill 渐进式加载**：系统提示词里只放技能的一行描述；模型判断需要时才调用 `load_skill` 读取完整流程，这样能节省上下文。以后增加新技能，只需新建一个 `skills/<名称>/SKILL.md`，代码不用改。
2. **MCP 解耦**：笔记检索做成独立的 MCP 服务，任何支持 MCP 的客户端都能复用。一轮对话共用一个 session，子进程只启动一次。
3. **安全**：key 只放在 `.env` 里，不进代码和 git；`read_note` 会校验路径，防止通过 `../.env` 读到笔记目录以外的文件。
4. **可观察性**：界面实时展示每一步调用了哪个工具、传了什么参数、返回了什么结果，Agent 的决策过程一目了然。

## 相对课堂 demo 的改动

本项目主要参考 **demo_5（LangChain Deep Agents 课程助教）**。Streamlit 界面、OpenAI 兼容接口和工具调用这些基础，对应课程 demo_1、demo_2 的内容。

| 方面 | demo_5 的做法 | 本项目 | 变化 |
|---|---|---|---|
| 模型接入 | 阿里百炼 qwen3.7-plus，`ChatOpenAI` + OpenAI 兼容接口 | DeepSeek，同样用 `ChatOpenAI`，只改 `base_url` | 沿用 |
| Agent 框架 | `create_deep_agent`：任务规划、文件系统、子代理、长期记忆 | `create_agent`：单个 ReAct Agent | 有意简化：场景只是"检索笔记 + 出卷"，不需要子代理和文件系统 |
| MCP | `mcp_server.py`（course-info）查询课程信息，`mcp_servers.json` 管理多个服务 | `notes_server.py` 检索用户自己的笔记；一轮对话共用一个 session | 服务内容新写；`read_note` 增加路径穿越防护 |
| Skill | Deep Agents 内置：系统提示词放 name/description，Agent 用 `read_file` 读取 SKILL.md | 没有文件系统工具，自己扫描 frontmatter 拼系统提示词，用 `load_skill` 工具加载正文 | 在普通 `create_agent` 上自己实现了同样的渐进式加载 |
| 自定义工具 | `get_current_time`、`calculator` | `exam_countdown`、`save_review_sheet` | 换成复习场景的工具，加入参数校验（日期格式、Windows 文件名非法字符） |
| 安全 | `FilesystemPermission` 规则：禁止读写 `.env`，只允许写 `workspace/` | `read_note` 只能读取 `notes/` 下的 .md/.txt；导出文件只写 `output/` | 思路相同，实现更轻量 |
| 异步与界面 | `web.py` 开一个常驻后台事件循环线程，Agent 只创建一次，页面线程通过队列接收事件 | 每轮用 `asyncio.Runner`（Windows 下指定 Proactor）跑一次；每轮新建 `httpx.AsyncClient` | 换了一种做法：回调直接在脚本线程更新界面，不需要队列；用每轮新建的 HTTP 客户端解决了"第二轮报 Event loop is closed"的问题 |
| 多轮记忆 | `AsyncSqliteSaver` 检查点 + `sessions.db`，可以恢复历史会话 | `st.session_state` 保存历史，刷新后清空 | 简化，列入"已知局限" |
| 输出 | 报告写入 `workspace/`，可预览 Markdown 并下载 | 复习卷转成带样式、可打印的 HTML，界面提供下载按钮 | 新增 |

**从 demo_5 学到并保留的**：用 OpenAI 兼容接口切换模型、用 langchain-mcp-adapters 把 MCP 工具转换成 LangChain 工具、Skill 的渐进式披露、密钥只放在 `.env` 里。

## 数据来源

`notes/` 目录下的 3 篇《数据结构》笔记（线性表与栈队列、树与二叉树、图）为 **AI 生成、经本人校对的示例笔记**，仅用于演示，模仿学生课堂笔记的风格，刻意保留了一些"我的疑问"和未完成的内容。使用时可以替换成自己的 `.md` / `.txt` 笔记。

## 已知局限

- 只支持 `.md` / `.txt` 笔记，不支持 PDF / Word
- 检索是关键词匹配，不是向量语义检索，近义词可能搜不到
- 对话历史只保存在浏览器会话中，刷新页面后清空
