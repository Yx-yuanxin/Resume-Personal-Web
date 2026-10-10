# -*- coding: utf-8 -*-
"""外部公开信息采集模块（合规采集三道闸）。

第 1 道闸：robots.txt——urllib.robotparser.can_fetch() 不允许的 URL 直接跳过；
第 2 道闸：登录墙检测——页面含密码输入框/明显登录跳转的不采集；
第 3 道闸：正文清洗——剥离脚本样式导航广告，按文本密度抽取正文。

采集结果只写入 external_store（外部库），永不进入内部库。
"""
import json
import re
import time
import urllib.robotparser as robotparser
from pathlib import Path
from urllib.parse import urlparse

import requests

import config
import doc_parser
import wiki_engine
from vector_store import external_store

HISTORY_PATH = config.DATA_DIR / "collect_history.json"

_FORBIDDEN_TAGS = re.compile(
    r"<(script|style|nav|footer|aside|header|iframe|noscript)[^>]*>.*?</\1>",
    re.S | re.I)
_LOGIN_FORM_RE = re.compile(
    r"<input[^>]+type=[\"']password[\"']", re.I)
_AD_WORDS = ["点击查看", "广告", "赞助", "订阅", "登录后查看", "注册查看", "立即下载"]


# ---------------------------------------------------------------- 合规检查
def check_robots(url: str) -> bool:
    """检查目标站点的 robots.txt 是否允许抓取该 URL。"""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(config.USER_AGENT, url)
    except Exception:
        # robots.txt 不可读时保守起见放行公开页面（无 robots 视为不限制），
        # 但仍受第 2 道闸（登录墙检测）与只采公开页的约束
        return True


def is_login_wall(html: str) -> bool:
    """登录墙检测：含密码输入框或整页就是登录表单的页面不采集。"""
    return bool(_LOGIN_FORM_RE.search(html))


# ---------------------------------------------------------------- 抓取与清洗
def fetch_page(url: str):
    """抓取单页，返回 (html, error)。非 200 / 超时 / 登录墙均返回错误。"""
    try:
        resp = requests.get(
            url, timeout=config.FETCH_TIMEOUT,
            headers={"User-Agent": config.USER_AGENT},
            allow_redirects=True)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"
        html = resp.text
        if is_login_wall(html):
            return None, "检测到登录墙，按合规要求跳过"
        return html, None
    except Exception as exc:
        return None, f"抓取失败: {str(exc)[:80]}"


def clean_html(html: str) -> tuple:
    """清洗 HTML → (标题, 正文)。策略：去标签 → 段落切分 → 密度过滤 → 广告句剔除。"""
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    title = (title_m.group(1).strip() if title_m else "未命名页面")[:100]

    body = _FORBIDDEN_TAGS.sub(" ", html)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    body = re.sub(r"</p>|</div>|</li>|</h[1-6]>", "\n", body, flags=re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    # 反转义常见实体
    for entity, char in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                         ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")]:
        body = body.replace(entity, char)

    # 段落过滤：太短的（导航/广告碎屑）剔除
    paragraphs = []
    for line in body.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) >= 20 and not any(w in line for w in _AD_WORDS):
            paragraphs.append(line)
    return title, "\n".join(paragraphs)


# ---------------------------------------------------------------- 搜索入口
def search_urls(keywords: str, max_results: int):
    """关键词 → 公开网页 URL 列表（DuckDuckGo HTML 接口，无需 Key）。"""
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": keywords}, timeout=config.FETCH_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DongZhiDaoBot/0.1)"})
        urls = re.findall(r'href="(https?://[^"]+)"', resp.text)
        # 去掉搜索引擎自身的跳转链接
        urls = [u for u in urls if "duckduckgo.com" not in u]
        seen, result = set(), []
        for u in urls:
            if u not in seen:
                seen.add(u)
                result.append(u)
            if len(result) >= max_results:
                break
        return result
    except Exception:
        return []


# ---------------------------------------------------------------- 采集主流程
def collect(keywords: str, max_pages: int = None, manual_urls=None):
    """采集主入口：关键词搜索（或手动 URL 列表）→ 合规三道闸 → 入外部库 → 生成 Wiki 候选。

    :return: {"task_id", "results": [{url, title, status, chunks, reason}], "summary"}
    """
    max_pages = max_pages or config.MAX_PAGES_DEFAULT
    task_id = f"col_{int(time.time() * 1000)}"

    # URL 来源：手动粘贴（演示稳定优先）或关键词搜索
    urls = list(manual_urls or [])[:max_pages]
    if not urls and keywords:
        urls = search_urls(keywords, max_pages)

    results = []
    for url in urls:
        # 第 1 道闸：robots 协议
        if not check_robots(url):
            results.append({"url": url, "title": "-", "status": "跳过",
                            "chunks": 0, "reason": "robots.txt 不允许抓取"})
            continue

        # 抓取（含第 2 道闸：登录墙检测）
        html, err = fetch_page(url)
        if err:
            results.append({"url": url, "title": "-", "status": "跳过",
                            "chunks": 0, "reason": err})
            continue

        # 第 3 道闸：清洗
        title, content = clean_html(html)
        if len(content) < 60:
            results.append({"url": url, "title": title, "status": "跳过",
                            "chunks": 0, "reason": "清洗后有效正文过短"})
            continue

        # 分块入外部库（只进外部库，内外隔离）
        chunks = doc_parser.chunk_text(content, doc_name=title)
        external_store.add(chunks, source_ref=title)

        # 自动生成 Wiki 候选条目（待审核）
        wiki_engine.extract_candidate(
            f"关于「{keywords or title}」的公开资料要点",
            content[:400],
            [{"type": "external", "kind": "document", "ref": title,
              "score": 1.0, "snippet": content[:80]}],
        )
        results.append({"url": url, "title": title, "status": "已入库",
                        "chunks": len(chunks), "reason": ""})

    summary = {
        "task_id": task_id, "keywords": keywords,
        "total": len(results),
        "collected": sum(1 for r in results if r["status"] == "已入库"),
        "skipped": sum(1 for r in results if r["status"] == "跳过"),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _append_history(summary, results)
    return {"task_id": task_id, "results": results, "summary": summary}


def _append_history(summary, results):
    history = []
    if HISTORY_PATH.exists():
        history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    history.append({"summary": summary, "results": results})
    history = history[-50:]
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2),
                            encoding="utf-8")


def get_history():
    if HISTORY_PATH.exists():
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    return []
