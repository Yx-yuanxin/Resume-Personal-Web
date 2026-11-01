# Learning Support Bot · 学习支持助手

> 北辰在线学院 · 学习支持与辅导协作项目 MVP
>
> 学生问题多渠道汇聚 → AI 分类与初答 → 助教人工复核 → 知识沉淀闭环

## 项目是什么

在线教育场景下，学生问题散落在微信群、作业评论区、私信等多个渠道，助教容易漏看连续求助、重复回答相似问题。本项目用一个最小闭环演示：

1. 学生提问统一进入一个入口
2. AI 自动做意图分类（课程疑问 / 作业问题 / 学习进度 / 技术问题 / 其他）
3. 高置信问题直接生成初答草稿，低置信或高风险问题转人工助教
4. 所有问答留痕，沉淀为知识库

## 怎么装

```bash
# 1. 克隆后进入目录
cd learning-support-bot

# 2. 建议用虚拟环境
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

# 3. 装依赖
pip install -r requirements.txt
```

## 怎么跑

### 方式一：启动 Web Demo（推荐）

```bash
python -m src.learning_support_bot.main
# 浏览器打开 http://127.0.0.1:5000
```

页面上输入学生问题，点提交即可看到：分类结果、AI 初答草稿、是否转人工助教。

### 方式二：命令行 Demo

```bash
python examples/demo.py
```

### 方式三：跑测试

```bash
python -m pytest tests/ -v
```

## 目录结构

```
learning-support-bot/
├── README.md              # 本文件
├── LICENSE                # MIT 开源协议
├── .gitignore
├── CHANGELOG.md           # 版本记录
├── requirements.txt       # Python 依赖
├── config/
│   └── default.yaml       # 默认配置（分类规则、阈值等）
├── src/
│   └── learning_support_bot/
│       ├── __init__.py
│       ├── main.py        # Flask Web 入口
│       ├── core/
│       │   ├── classifier.py   # 问题意图分类
│       │   ├── responder.py    # 初答草稿生成
│       │   └── router.py       # 转人工判断
│       └── utils/
│           └── logger.py   # 日志与留痕
├── docs/
│   ├── design.md          # 设计思路
│   └── api.md             # 接口说明
├── tests/
│   └── test_core.py       # 核心逻辑测试
├── examples/
│   └── demo.py            # 命令行 demo
├── scripts/
│   ├── build.sh
│   └── deploy.sh
├── data/                  # 样例数据
└── .github/
    └── workflows/          # CI/CD
```

## 当前状态

- [x] 问题分类（关键词规则版）
- [x] 初答草稿生成（模板版）
- [x] 转人工判断（阈值规则）
- [x] Web Demo 页面
- [ ] 接入真实大模型 API
- [ ] 多渠道消息接入（微信群 / 作业评论）
- [ ] 知识库持久化

## License

MIT
