# 东知道 · 企业内外双源制度问答智能体

> 大赛可演示原型 | LLM-Wiki 知识沉淀架构 | 内部私有制度库 + 外部公开采集库 双源隔离 | 强制溯源合规

## 一、项目简介

「东知道」是一个面向企业制度场景的问答智能体原型：

- **双源知识**：内部私有制度文档（PDF/Word）与外部公开网页采集信息**物理隔离**，各自独立存储、独立检索；
- **LLM-Wiki 知识沉淀**：每次问答后自动把有效知识抽取为结构化 Wiki 条目，管理员审核生效后**优先参与检索**，让系统"越用越聪明"；
- **强制溯源合规**：每条回答必须携带来源；外部信息强制提示"仅供参考"；无匹配知识时明确回复"暂无相关制度或公开资料"，禁止编造。

## 二、目录结构

```
dongzhidao/
├── README.md                  # 本文件：总览与快速开始
├── docs/
│   ├── 01-architecture.md     # ① 项目架构说明
│   ├── 02-demo-cases.md       # ④ 测试演示案例（含演示脚本）
│   └── 03-ppt-outline.md      # ⑤ 大赛答辩PPT大纲
├── frontend/                  # ② 前端（纯 HTML+CSS+JS，可部署 GitHub Pages）
│   ├── index.html             #    单页应用，4 个 Tab
│   ├── css/style.css
│   └── js/                    #    config / mock / app / chat / upload / wiki / collector
└── backend/                   # ③ 后端示例代码（FastAPI，演示级实现）
    ├── main.py                #    API 入口 + 静态托管前端
    ├── config.py              #    配置（LLM API、检索参数）
    ├── llm_client.py          #    大模型 API 客户端（OpenAI 兼容，可 MOCK 降级）
    ├── doc_parser.py          #    PDF/Word 解析、分块
    ├── vector_store.py        #    轻量向量库（TF-IDF 字符 n-gram，内外库物理隔离）
    ├── rag_engine.py          #    问题分类 + 双库检索 + 回答生成
    ├── wiki_engine.py         #    LLM-Wiki 知识抽取 / 审核 / 检索（核心）
    ├── web_collector.py       #    外部公开网页采集（robots 协议、登录墙检测、正文清洗）
    ├── compliance.py          #    合规过滤（溯源、外部提示、无匹配兜底）
    ├── requirements.txt
    └── data/                  #    JSON 数据目录（自动生成）
        ├── internal_store.json    # 内部库分块+向量（绝不参与外部检索）
        ├── external_store.json    # 外部库分块+向量（绝不参与内部检索）
        ├── wiki_entries.json      # Wiki 知识条目
        └── conversations.json     # 对话历史
```

## 三、快速开始

### 方式 A：一体化运行（推荐，完整功能）

```bash
cd backend
pip install -r requirements.txt
python seed_demo.py        # 装载演示种子数据（示例制度文档+已生效Wiki）
python main.py             # 启动服务 http://localhost:8000
```

浏览器打开 `http://localhost:8000`，四个 Tab 全功能可用（默认 MOCK 模式，无需 API Key）。

**自动化验证**：`python smoke_test.py` 一键跑通 14 项断言
（内部/外部问答、无匹配兜底、Wiki 沉淀闭环、内外隔离），全部通过再上台演示。

### 方式 B：接入真实大模型

```bash
# 任选 OpenAI 兼容服务：DeepSeek / 通义千问 / Kimi / GLM ...
export LLM_BASE_URL="https://api.deepseek.com/v1"
export LLM_API_KEY="sk-xxxx"
export LLM_MODEL="deepseek-chat"
python main.py
```

未配置 Key 时自动降级为 **MOCK 模式**（基于检索片段的模板回答），保证离线演示链路完整。

### 方式 C：纯前端部署 GitHub Pages

`frontend/` 目录为纯静态文件，直接推到 GitHub Pages 即可。启动时探测不到后端时
自动进入**演示模式**（内置 Mock 数据，可完整演示问答、溯源、Wiki 审核闭环的 UI 流程）。

## 四、核心 API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 提问：`{question, scope}`，返回回答+溯源+Wiki候选 |
| POST | `/api/documents/upload` | 上传内部制度文档（PDF/Word/TXT） |
| GET / DELETE | `/api/documents` | 文档列表 / 删除 |
| GET | `/api/wiki` | Wiki 条目列表（按状态/来源筛选） |
| POST | `/api/wiki/{id}/approve` `\|` `/reject` | 审核：通过生效 / 驳回 |
| PUT / DELETE | `/api/wiki/{id}` | 编辑 / 删除条目 |
| POST | `/api/collect` | 外部采集：`{keywords, max_pages}` |
| GET | `/api/collect/history` | 采集历史 |
| GET | `/api/health` | 健康检查 + 数据统计 |

## 五、硬性合规要求（已内置）

1. **强制溯源**：所有回答携带 `sources` 数组，前端逐条展示来源（文档名/网页URL）；
2. **外部提示**：回答引用外部信息时，强制附提示「该信息来源于公开网络，仅供参考，不作为企业内部制度依据」；
3. **禁止编造**：生成 Prompt 限定"仅依据给定资料回答"；检索无匹配时统一回复"暂无相关制度或公开资料"；
4. **内外隔离**：内部库与外部库为两个独立存储实例，检索按 scope 严格路由，外部采集数据永不进入内部库。

## 六、定位声明

本项目为**比赛演示原型**：JSON 文件存储、规则+LLM 混合分类、轻量 TF-IDF 检索，
均为演示级取舍（可讲清逻辑、可现场跑通）。生产化路线见架构文档第 6 节。
