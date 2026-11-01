"""日志与留痕工具"""
from __future__ import annotations
import json
import time
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parents[3] / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_interaction(question: str, classification: dict, reply: str, routing: dict) -> Path:
    """把一次学生问答完整留痕，写入 JSONL 文件。

    对应 FDE 要求的"审计留痕·六要素"：
    业务编号 / 资料版本 / 事实引用 / 建议结果 / 人工改动 / 签核人
    """
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "classification": classification,
        "ai_draft_reply": reply,
        "routing": routing,
        "human_modified": False,   # 人工是否改过
        "human_signoff": None,     # 人工签核人
    }
    log_file = LOG_DIR / f"{time.strftime('%Y%m%d')}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return log_file
