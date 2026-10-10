# -*- coding: utf-8 -*-
"""轻量向量库（演示级）：字符 2-gram TF-IDF + 余弦相似度。

为什么不用真向量库（答辩要点）：
- 比赛环境不可控（无网络下载模型/无 GPU），TF-IDF 纯 Python 零依赖、离线可跑；
- 中文友好（字符 n-gram 天然规避分词依赖）；
- 接口与真向量库同构（add/search），生产化只需把本文件换成 pgvector/Milvus 实现。

内外隔离设计：每个 VectorStore 实例对应一个独立 JSON 文件，
内部库与外部库各自实例化，物理隔离、互不可见。
"""
import json
import math
import re
from collections import Counter
from pathlib import Path

_TOKEN_RE = re.compile(r"[\u4e00-\u9fa5a-zA-Z0-9]+")


def _tokenize(text: str):
    """字符 2-gram 分词：中文按字、英文/数字按词，再取 bigram。"""
    tokens = []
    for word in _TOKEN_RE.findall(text.lower()):
        if len(word) == 1:
            tokens.append(word)
        elif re.match(r"^[a-z0-9]+$", word):
            tokens.append(word)  # 英文单词整体作为一个 token
        else:
            tokens += [word[i:i + 2] for i in range(len(word) - 1)]
    return tokens


class VectorStore:
    """单源向量库：add 入库 / search 相似检索 / save-load JSON 持久化。"""

    def __init__(self, store_path: Path, source_type: str):
        self.store_path = Path(store_path)
        self.source_type = source_type  # internal / external（用于来源标注）
        self.docs = []       # [{"id","text","source_ref","meta"}]
        self._df = Counter()  # 文档频率，用于 IDF
        if self.store_path.exists():
            self._load()

    # ------------------------------------------------------------ 持久化
    def _load(self):
        data = json.loads(self.store_path.read_text(encoding="utf-8"))
        self.docs = data.get("docs", [])
        self._rebuild_df()

    def save(self):
        self.store_path.write_text(
            json.dumps({"source_type": self.source_type, "docs": self.docs},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")

    def _rebuild_df(self):
        self._df = Counter()
        for d in self.docs:
            self._df.update(set(_tokenize(d["text"])))

    # ------------------------------------------------------------ 写入
    def add(self, chunks, source_ref: str):
        """chunks: doc_parser.chunk_text 的输出。source_ref: 文档名/网页URL。"""
        for c in chunks:
            self.docs.append({
                "id": f"{self.source_type}_{len(self.docs):06d}",
                "text": c["text"],
                "source_ref": source_ref,
                "meta": c.get("meta", {}),
            })
        self._rebuild_df()
        self.save()

    def remove_by_source(self, source_ref: str) -> int:
        before = len(self.docs)
        self.docs = [d for d in self.docs if d["source_ref"] != source_ref]
        self._rebuild_df()
        self.save()
        return before - len(self.docs)

    # ------------------------------------------------------------ 检索
    def _idf(self, token: str) -> float:
        n = len(self.docs) or 1
        return math.log((n + 1) / (self._df.get(token, 0) + 1)) + 1.0

    def _vectorize(self, text: str):
        tf = Counter(_tokenize(text))
        if not tf:
            return {}
        total = sum(tf.values())
        return {t: (c / total) * self._idf(t) for t, c in tf.items()}

    @staticmethod
    def _cosine(v1: dict, v2: dict) -> float:
        common = set(v1) & set(v2)
        if not common:
            return 0.0
        dot = sum(v1[t] * v2[t] for t in common)
        n1 = math.sqrt(sum(x * x for x in v1.values()))
        n2 = math.sqrt(sum(x * x for x in v2.values()))
        return dot / (n1 * n2) if n1 and n2 else 0.0

    def search(self, query: str, top_k: int = 5, threshold: float = 0.0):
        """返回 [{text, source_ref, meta, score}]，按相似度降序，低于 threshold 过滤。"""
        qv = self._vectorize(query)
        scored = []
        for d in self.docs:
            dv = self._vectorize(d["text"])
            score = self._cosine(qv, dv)
            if score >= threshold:
                scored.append({
                    "text": d["text"],
                    "source_ref": d["source_ref"],
                    "meta": d["meta"],
                    "score": round(score, 4),
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def stats(self) -> dict:
        sources = {d["source_ref"] for d in self.docs}
        return {"source_type": self.source_type, "chunks": len(self.docs), "sources": len(sources)}


# ------------------------------------------------------------ 全局单例（内外双库，物理隔离）
import config  # noqa: E402

internal_store = VectorStore(config.INTERNAL_STORE_PATH, "internal")  # 内部私有库
external_store = VectorStore(config.EXTERNAL_STORE_PATH, "external")  # 外部公开库
