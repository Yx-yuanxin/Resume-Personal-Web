"""笔记检索 MCP 服务：通过 stdio 提供 search_notes / read_note 两个工具。

由 agent.py 以子进程方式启动，也可单独运行：python notes_server.py
注意：stdio 模式下 stdout 是 MCP 协议通道，这里不能 print 任何内容。
"""
from pathlib import Path

from fastmcp import FastMCP

NOTES_DIR = (Path(__file__).parent / "notes").resolve()
ALLOWED_SUFFIXES = {".md", ".txt"}  # 只支持 Markdown 和纯文本

mcp = FastMCP("notes")


def _note_files() -> list[Path]:
    """列出 notes/ 下所有支持的笔记文件。"""
    return sorted(p for p in NOTES_DIR.iterdir() if p.suffix.lower() in ALLOWED_SUFFIXES)


@mcp.tool
def search_notes(keyword: str) -> str:
    """按关键词检索课程笔记，返回命中的文件名、行号及上下文片段。

    Args:
        keyword: 要搜索的关键词，如 "BST"、"Dijkstra"、"循环队列"
    """
    hits = []
    for path in _note_files():
        # Windows 默认编码是 GBK，这里必须显式指定 UTF-8
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                # 取命中行的前后各 1 行作为上下文
                snippet = "\n".join(lines[max(0, i - 1): i + 2])
                hits.append(f"【{path.name} 第{i + 1}行】\n{snippet}")
    if not hits:
        files = "、".join(p.name for p in _note_files())
        return f"笔记中没有找到「{keyword}」。现有笔记：{files}"
    return "\n\n".join(hits[:10])  # 最多返回 10 条，避免撑爆上下文


@mcp.tool
def read_note(filename: str) -> str:
    """读取一篇笔记的全文。

    Args:
        filename: 笔记文件名，如 "02_树与二叉树.md"（可先用 search_notes 找到）
    """
    path = (NOTES_DIR / filename).resolve()
    # 安全检查：防止 "../.env" 之类的路径穿越读到 notes/ 以外的文件
    if path.parent != NOTES_DIR or path.suffix.lower() not in ALLOWED_SUFFIXES:
        return f"拒绝访问：{filename} 不是 notes/ 目录下的 .md/.txt 文件"
    if not path.exists():
        files = "、".join(p.name for p in _note_files())
        return f"文件不存在：{filename}。现有笔记：{files}"
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
