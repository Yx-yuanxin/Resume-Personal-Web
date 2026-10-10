# -*- coding: utf-8 -*-
"""东知道后端入口：FastAPI + 静态托管前端。

启动：python main.py  →  http://localhost:8000
接口文档（答辩演示加分项）：http://localhost:8000/docs
"""
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import doc_parser
import rag_engine
import web_collector
import wiki_engine
from vector_store import internal_store, external_store

app = FastAPI(title="东知道 · 企业内外双源制度问答智能体", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 演示原型放开跨域；生产应收紧为前端域名
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================================================================ 健康检查
@app.get("/api/health")
def health():
    """前端启动探测：成功 → LIVE 模式；失败 → 前端转演示模式。"""
    return {
        "status": "ok",
        "app": "东知道",
        "llm_mode": "LLM" if config.LLM_API_KEY else "MOCK",
        "internal_store": internal_store.stats(),
        "external_store": external_store.stats(),
        "wiki": wiki_engine.stats(),
    }


# ================================================================ Tab1 对话问答
class ChatRequest(BaseModel):
    question: str
    scope: str = "auto"  # auto / internal / external / mixed


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(400, "问题不能为空")
    if req.scope not in ("auto", "internal", "external", "mixed"):
        req.scope = "auto"

    result = rag_engine.answer_question(req.question.strip(), req.scope)
    rag_engine.save_conversation(req.question.strip(), result)
    return result


@app.get("/api/conversations")
def conversations():
    if config.CONVERSATIONS_PATH.exists():
        import json
        return json.loads(config.CONVERSATIONS_PATH.read_text(encoding="utf-8"))
    return []


# ================================================================ Tab2 文档上传（内部库）
@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传内部制度文档：PDF/Word/TXT → 解析分块 → 入内部库。"""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".docx", ".doc", ".txt"):
        raise HTTPException(400, f"不支持的类型 {suffix}，请上传 PDF/Word/TXT")

    save_path = config.UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        chunks = doc_parser.parse_document(str(save_path), doc_name=file.filename)
    except Exception as exc:
        raise HTTPException(422, f"文档解析失败：{exc}")
    if not chunks:
        raise HTTPException(422, "未能从文档中提取到有效文本")

    # 内部文档若曾上传过，先移除旧版再入库
    internal_store.remove_by_source(file.filename)
    internal_store.add(chunks, source_ref=file.filename)
    return {"filename": file.filename, "chunks": len(chunks),
            "store": "internal", "message": "已解析入库（内部私有库）"}


@app.get("/api/documents")
def list_documents():
    docs = {}
    for d in internal_store.docs:
        docs.setdefault(d["source_ref"], 0)
        docs[d["source_ref"]] += 1
    return [{"name": name, "chunks": n, "store": "internal",
             "type": "内部制度文档"} for name, n in sorted(docs.items())]


@app.delete("/api/documents/{name}")
def delete_document(name: str):
    removed = internal_store.remove_by_source(name)
    if not removed:
        raise HTTPException(404, "文档不存在")
    return {"removed_chunks": removed, "message": f"已从内部库删除《{name}》全部分块"}


# ================================================================ Tab3 LLM-Wiki 知识库
@app.get("/api/wiki")
def list_wiki(status: str = None, source_type: str = None):
    return wiki_engine.list_entries(status=status, source_type=source_type)


@app.get("/api/wiki/stats")
def wiki_stats():
    return wiki_engine.stats()


@app.post("/api/wiki/{entry_id}/approve")
def wiki_approve(entry_id: str):
    entry = wiki_engine.approve(entry_id)
    if not entry:
        raise HTTPException(404, "条目不存在")
    return {"entry": entry, "message": "已生效，将优先参与问答检索"}


@app.post("/api/wiki/{entry_id}/reject")
def wiki_reject(entry_id: str):
    entry = wiki_engine.reject(entry_id)
    if not entry:
        raise HTTPException(404, "条目不存在")
    return {"entry": entry, "message": "已驳回（保留待审核标记，可编辑后再审）"}


class WikiEdit(BaseModel):
    knowledge_title: str = None
    knowledge_content: str = None
    activate: bool = False


@app.put("/api/wiki/{entry_id}")
def wiki_edit(entry_id: str, body: WikiEdit):
    entry = wiki_engine.edit_entry(
        entry_id, title=body.knowledge_title,
        content=body.knowledge_content, activate=body.activate)
    if not entry:
        raise HTTPException(404, "条目不存在")
    return {"entry": entry, "message": "已保存"}


@app.delete("/api/wiki/{entry_id}")
def wiki_delete(entry_id: str):
    if not wiki_engine.delete_entry(entry_id):
        raise HTTPException(404, "条目不存在")
    return {"message": "已删除"}


# ================================================================ Tab4 外部采集
class CollectRequest(BaseModel):
    keywords: str = ""
    max_pages: int = 5
    manual_urls: list = None  # 演示稳态：可手动粘贴公开 URL 列表


@app.post("/api/collect")
def collect(req: CollectRequest):
    if not req.keywords.strip() and not req.manual_urls:
        raise HTTPException(400, "请输入关键词或提供公开网页 URL")
    return web_collector.collect(req.keywords.strip(), req.max_pages,
                                 manual_urls=req.manual_urls)


@app.get("/api/collect/history")
def collect_history():
    return web_collector.get_history()


@app.get("/api/collect/external-docs")
def external_docs():
    docs = {}
    for d in external_store.docs:
        docs.setdefault(d["source_ref"], 0)
        docs[d["source_ref"]] += 1
    return [{"name": name, "chunks": n, "store": "external",
             "type": "公开网络采集"} for name, n in sorted(docs.items())]


# ================================================================ 前端静态托管
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print(" 东知道 · 企业内外双源制度问答智能体")
    print(f" LLM 模式: {'LLM API' if config.LLM_API_KEY else 'MOCK（未配置 LLM_API_KEY）'}")
    print(" 页面: http://localhost:8000   接口文档: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
