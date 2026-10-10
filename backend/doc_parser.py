# -*- coding: utf-8 -*-
"""文档解析与分块：PDF / Word(docx) / TXT。

流程：extract_text 提取全文 → chunk_text 按分隔符+滑动窗口分块
     （目标 400 字，重叠 80 字，保证语义连续性）
"""
import re
from pathlib import Path

import config


# ---------------------------------------------------------------- 文本提取
def extract_text(file_path: str) -> str:
    """按扩展名分发解析器，返回纯文本。"""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(file_path)
    if suffix in (".docx", ".doc"):
        return _extract_docx(file_path)
    if suffix == ".txt":
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"不支持的文件类型: {suffix}（支持 .pdf/.docx/.txt）")


def _extract_pdf(file_path: str) -> str:
    import pdfplumber  # 延迟导入，缺库时报错更友好

    texts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
    return "\n".join(texts)


def _extract_docx(file_path: str) -> str:
    from docx import Document

    doc = Document(file_path)
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    # 表格内容也要（制度文档常见"标准-金额"表格）
    for table in doc.tables:
        for row in table.rows:
            parts.append("\t".join(c.text.strip() for c in row.cells))
    return "\n".join(parts)


# ---------------------------------------------------------------- 分块
_SPLIT_RE = re.compile(r"[\n。；;!?！？]")


def chunk_text(text: str, doc_name: str = ""):
    """把长文本切成带来源元数据的分块列表。

    策略：先按句读切成句，再组装到 CHUNK_SIZE 附近，块间保留 CHUNK_OVERLAP 重叠。
    返回: [{"chunk_id": "...", "text": "...", "meta": {"doc_name": ..., "locator": ...}}]
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    sentences, buf = [], ""
    for part in _SPLIT_RE.split(text):
        part = part.strip()
        if not part:
            continue
        if len(buf) + len(part) + 1 <= config.CHUNK_SIZE:
            buf = f"{buf}。{part}" if buf else part
        else:
            sentences.append(buf)
            buf = part
    if buf:
        sentences.append(buf)

    chunks, start = [], 0
    idx = 0
    while start < len(sentences):
        group = sentences[start:]
        piece, total = "", 0
        for s in group:
            if total + len(s) > config.CHUNK_SIZE and piece:
                break
            piece = f"{piece}。{s}" if piece else s
            total = len(piece)
        chunks.append({
            "chunk_id": f"chk_{idx:05d}",
            "text": piece,
            "meta": {"doc_name": doc_name, "locator": f"第{start + 1}-{start + 1 + piece.count('。')}句"},
        })
        idx += 1
        # 用重叠字数估算下一块起点，保证相邻块有重叠
        consumed, acc = 0, 0
        for j, s in enumerate(sentences[start:]):
            acc += len(s)
            if acc >= max(len(piece) - config.CHUNK_OVERLAP, 1):
                consumed = j + 1
                break
        if consumed == 0:
            consumed = 1
        start += consumed

    return chunks


def parse_document(file_path: str, doc_name: str = ""):
    """对外统一入口：解析 + 分块。"""
    name = doc_name or Path(file_path).name
    text = extract_text(file_path)
    return chunk_text(text, doc_name=name)
