# 东知道 · 项目架构说明

## 1. 总体架构

```
┌─────────────────────────────── 前端（GitHub Pages 可部署）───────────────────────────────┐
│  ① 对话问答页        ② 文档上传页       ③ LLM-Wiki 知识库页      ④ 外部采集配置页       │
│  回答+溯源展示       PDF/Word 上传      条目浏览/编辑/审核       关键词抓取公开网页      │
└──────────────────────────────────────┬───────────────────────────────────────────────┘
                                       │ REST API（JSON）
┌──────────────────────────────────────▼───────────────────────────────────────────────┐
│                                   后端 FastAPI                                        │
│                                                                                      │
│  /api/chat ──► rag_engine（问答主链路）                                               │
│                  1. 问题分类（规则优先 + LLM 辅助）                                     │
│                  2. 双库检索：先「已生效 Wiki 条目」，再「原始文档分块」                  │
│                  3. LLM 生成（无 Key 则模板降级）                                       │
│                  4. compliance 合规过滤：溯源 + 外部提示 + 无匹配兜底                    │
│                  5. wiki_engine 异步抽取知识候选（默认待审核）                           │
│                                                                                      │
│  /api/documents ──► doc_parser（解析/分块）──► 内部向量库（internal_store）             │
│  /api/collect   ──► web_collector（robots 检查/抓取/清洗）──► 外部向量库（external_store）│
│  /api/wiki      ──► wiki_engine（抽取/审核/编辑/删除）                                  │
└──────────────────────────────────────┬───────────────────────────────────────────────┘
                                       │
                ┌──────────────────────┼──────────────────────┐
                ▼                      ▼                      ▼
        内部私有知识库          LLM-Wiki 知识条目库          外部公开知识库
     internal_store.json      wiki_entries.json          external_store.json
     （企业制度文档分块）      （待审核/已生效双状态）      （公开网页采集分块）
```

## 2. 问答主链路数据流（核心）

```
用户提问 "出差住宿标准是多少？"
   │
   ▼
① 问题分类 classify_question()
   规则：命中内部语料关键词（报销/考勤/我们公司…）→ internal
        命中外部语料关键词（国家/行业/公开政策…）  → external
        均命中或均未命中                          → mixed / auto
   │
   ▼
② 双库检索（scope 严格路由，内外永不相混）
   a. 先查「已生效 Wiki 条目」→ 命中：标记 wiki_hit，作为最高优先级上下文
   b. 再查「原始文档分块」     → TF-IDF 字符 n-gram 余弦相似度 Top-K
   c. 相似度全部低于阈值 → 无匹配 → 直接走合规兜底（禁止编造）
   │
   ▼
③ 回答生成
   有 LLM Key：Prompt 强约束"仅依据以下资料回答，逐条标注来源，资料中没有则明确说明"
   无 Key：MOCK 模板回答（"根据《XX制度》：…"，由检索片段拼接，演示链路完整）
   │
   ▼
④ 合规过滤 compliance
   - sources 数组必填（来源名/URL + 类型 internal/external + 相似度）
   - 含外部来源 → 追加提示「该信息来源于公开网络，仅供参考，不作为企业内部制度依据」
   - 无匹配 → 「暂无相关制度或公开资料…」
   │
   ▼
⑤ LLM-Wiki 知识沉淀（问答完成后触发）
   把 (问题, 回答, 来源) 交给 wiki_engine.extract_candidate()
   → 抽取 JSON 知识条目 {knowledge_title, knowledge_content, source_type,
                          source_reference, create_time, status:"待审核"}
   → 写入 wiki_entries.json，等待管理员在 ③ Tab 审核
```

## 3. 模块设计

### 3.1 前端（frontend/）

| 文件 | 职责 |
|---|---|
| `js/config.js` | API 地址、演示模式探测开关 |
| `js/mock.js` | 演示模式内置数据与模拟 API（GitHub Pages 上可完整演示 UI 闭环） |
| `js/chat.js` | Tab1：聊天流、溯源卡片、外部提示横幅、scope 选择 |
| `js/upload.js` | Tab2：拖拽上传、文档列表、删除 |
| `js/wiki.js` | Tab3：条目卡片、状态/来源筛选、审核通过/驳回、编辑弹窗 |
| `js/collector.js` | Tab4：关键词采集、采集结果、历史 |

**双模式设计**：启动时探测 `/api/health`，成功 → LIVE 模式（真后端）；失败 → 演示模式（Mock）。
同一套 UI、同一套接口签名，评委看到的交互完全一致。

### 3.2 后端（backend/）

| 模块 | 核心类/函数 | 演示级取舍 |
|---|---|---|
| `llm_client.py` | `llm_chat(messages)` | OpenAI 兼容 `POST /chat/completions`；Key 为空时抛出降级信号 |
| `doc_parser.py` | `parse_document(path)` → `chunk_text(text)` | pdfplumber / python-docx；400 字分块 + 80 字重叠 |
| `vector_store.py` | `VectorStore`（每源一个实例） | 字符 2-gram TF-IDF + 余弦相似度，纯 Python 无重依赖 |
| `rag_engine.py` | `classify_question / retrieve / answer` | 检索优先级：已生效 Wiki > 原始分块 |
| `wiki_engine.py` | `extract_candidate / approve / edit / search_active` | 知识条目 JSON Schema 与需求文档一致 |
| `web_collector.py` | `check_robots / fetch_page / clean_html` | urllib.robotparser 校验；密码表单=登录墙即跳过；密度法抽正文 |
| `compliance.py` | `apply_compliance` | 溯源必带、外部提示、无匹配兜底 |

### 3.3 LLM-Wiki 知识条目 Schema

```json
{
  "id": "wk_1699000001",
  "knowledge_title": "出差住宿报销标准",
  "knowledge_content": "员工出差住宿：一线城市 ≤600 元/晚，其他城市 ≤450 元/晚，超标部分自理…",
  "source_type": "internal",
  "source_reference": "差旅报销管理制度.pdf",
  "create_time": "2026-10-08 21:00:00",
  "status": "待审核"
}
```

**生命周期**：`待审核`（不参与检索）→ 管理员通过 → `已生效`（优先参与检索）；
驳回/删除则移除。编辑可修正标题与内容后直接生效。

### 3.4 内外双源隔离设计（合规硬要求）

1. **物理隔离**：`internal_store.json` 与 `external_store.json` 是两个独立的
   `VectorStore` 实例，无任何交叉引用；
2. **路由隔离**：`retrieve(question, scope)` 中 `scope=external` 时内部库代码路径完全不可达，反之亦然；
3. **入库隔离**：文档上传只写内部库；网页采集只写外部库，两处代码无共享写入口；
4. **展示隔离**：前端所有来源卡片显式标注【内部制度】/【公开网络】双色标签。

### 3.5 外部采集合规设计

```
输入关键词
   ▼
DuckDuckGo HTML 搜索（或手动粘贴公开 URL 列表）
   ▼
逐 URL 合规检查：
   ① robots.txt：urllib.robotparser.can_fetch() 不允许 → 跳过并记录
   ② 登录墙检测：页面含 password 类型输入框 / 明显登录跳转 → 跳过并记录
   ③ 非 200 响应 / 超时 → 跳过
   ▼
正文清洗：剥离 script/style/nav/footer/aside → 按文本密度抽正文 → 去广告短句
   ▼
分块入外部库 + 自动生成 Wiki 候选条目（待审核）
   ▼
回答引用外部信息时强制携带：「该信息来源于公开网络，仅供参考，不作为企业内部制度依据」
```

## 4. 关键流程时序（Wiki 闭环）

```
用户Q ──► 检索(已生效Wiki优先) ──► 回答A(带溯源) ──► 自动抽取知识候选K(待审核)
                                                              │
管理员在Tab3审核 K ──通过──► K.status=已生效                     │
                                                              ▼
用户再次提类似问题 ◄── 检索优先命中K（更精炼、更快、答案更稳定）◄──┘
```

## 5. 技术选型理由（答辩要点）

| 选型 | 理由 |
|---|---|
| 纯 HTML/CSS/JS 前端 | 零构建、可直接 GitHub Pages、评委零环境打开 |
| FastAPI | 异步、自带文档（/docs）、演示 Swagger 调试加分 |
| TF-IDF 字符 n-gram | 无模型下载、离线可跑；中文友好；换 embedding 只改 vector_store 一个文件 |
| OpenAI 兼容 LLM 接口 | 一套代码适配 DeepSeek/通义/Kimi/GLM，比赛现场哪家有 Key 用哪家 |
| JSON 文件存储 | 演示透明可直查；接口与 SQLite/向量库同构，迁移成本低 |

## 6. 生产化路线（商用价值答辩用）

- 存储：JSON → SQLite/PostgreSQL + pgvector / 专用向量库（Milvus、Qdrant）
- 检索：TF-IDF → BGE/text-embedding 向量检索 + BM25 混合召回 + Rerank
- 权限：管理员/员工角色体系，Wiki 审核工作流（多人会签）
- 采集：任务队列化、增量更新、死链监测、定时巡检
- 安全：内部文档脱敏、水印、审计日志、等保合规
