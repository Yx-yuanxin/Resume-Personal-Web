# -*- coding: utf-8 -*-
"""全局配置：环境变量优先，未配置时使用演示默认值。"""
import os
from pathlib import Path

# ---------- 大模型 API（OpenAI 兼容协议） ----------
# 任选：DeepSeek / 通义千问 / Kimi / GLM / OpenAI ...
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")          # 为空 => 自动 MOCK 降级
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# ---------- 数据目录 ----------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

INTERNAL_STORE_PATH = DATA_DIR / "internal_store.json"   # 内部私有库（物理隔离 1/2）
EXTERNAL_STORE_PATH = DATA_DIR / "external_store.json"   # 外部公开库（物理隔离 2/2）
WIKI_ENTRIES_PATH = DATA_DIR / "wiki_entries.json"       # LLM-Wiki 知识条目
CONVERSATIONS_PATH = DATA_DIR / "conversations.json"     # 对话历史
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ---------- 检索参数 ----------
CHUNK_SIZE = 400        # 文档分块目标字数
CHUNK_OVERLAP = 80      # 相邻块重叠字数
TOP_K = 5               # 原始文档检索返回条数
WIKI_TOP_K = 3          # 已生效 Wiki 条目检索条数
SIM_THRESHOLD = 0.05    # 文档检索相似度阈值：低于该值视为"无匹配"（合规兜底）
WIKI_SIM_THRESHOLD = 0.10  # Wiki 条目检索阈值（标题命中加权）

# ---------- 采集合规 ----------
FETCH_TIMEOUT = 10          # 单页抓取超时（秒）
MAX_PAGES_DEFAULT = 5       # 默认采集页数上限
USER_AGENT = "DongZhiDaoBot/0.1 (competition-demo; respects robots.txt)"

# ---------- 合规文案 ----------
NO_MATCH_REPLY = (
    "暂无相关制度或公开资料。"
    "您可以尝试更换关键词，或联系管理员上传相关制度文档后再试。"
)
EXTERNAL_DISCLAIMER = "该信息来源于公开网络，仅供参考，不作为企业内部制度依据"
