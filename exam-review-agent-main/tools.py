"""本地自定义工具：load_skill（按需加载技能）、exam_countdown、save_review_sheet。"""
import html
import re
from datetime import datetime
from pathlib import Path

import markdown
import yaml
from langchain_core.tools import tool

BASE_DIR = Path(__file__).parent
SKILLS_DIR = BASE_DIR / "skills"
OUTPUT_DIR = BASE_DIR / "output"


# ---------- Skill：渐进式加载 ----------

def _split_skill(path: Path) -> tuple[dict, str]:
    """把 SKILL.md 拆成 (frontmatter 字典, 正文)。文件以 --- 包裹的 YAML 开头。"""
    _, front, body = path.read_text(encoding="utf-8").split("---", 2)
    return yaml.safe_load(front), body.strip()


def list_skills() -> list[dict]:
    """扫描 skills/*/SKILL.md，只取 name 和 description —— 系统提示词里只放这些。"""
    skills = []
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        meta, _ = _split_skill(path)
        skills.append({"name": meta["name"], "description": meta["description"]})
    return skills


@tool
def load_skill(name: str) -> str:
    """加载指定技能的完整操作说明。当任务与系统提示词中列出的某个技能匹配时，先调用本工具。

    Args:
        name: 技能名称，如 "exam-review"
    """
    for path in SKILLS_DIR.glob("*/SKILL.md"):
        meta, body = _split_skill(path)
        if meta["name"] == name:
            return body  # 正文只在需要时才进入上下文，节省 token
    names = "、".join(s["name"] for s in list_skills())
    return f"没有名为 {name} 的技能，可用技能：{names}"


# ---------- 考试倒计时 ----------

@tool
def exam_countdown(exam_date: str, subject: str = "期末考试") -> str:
    """计算距离考试还有多少天，并给出复习节奏建议。凡涉及日期、倒计时的问题都必须调用本工具，不要自己计算。

    Args:
        exam_date: 考试日期，格式 YYYY-MM-DD，如 "2026-12-28"
        subject: 科目名称，如 "数据结构"
    """
    try:
        target = datetime.strptime(exam_date, "%Y-%m-%d").date()
    except ValueError:
        return f"日期格式错误：{exam_date}，请使用 YYYY-MM-DD"
    today = datetime.now().date()  # 以运行时的系统时间为准
    days = (target - today).days
    if days < 0:
        return f"今天是 {today}，{subject}（{exam_date}）已经过去 {-days} 天了"
    if days == 0:
        return f"今天就是{subject}考试日，放轻松，看看自己的疑问清单就好"
    # 按剩余天数给出不同的复习节奏
    if days > 30:
        tip = "时间充裕：每周复习一章，每章做一份复习卷"
    elif days > 7:
        tip = "进入冲刺期：每 2~3 天过一章，重点做复习卷和错题"
    else:
        tip = "考前一周：只看重点结论和笔记里的「我的疑问」"
    return f"今天是 {today}，距离{subject}（{exam_date}）还有 {days} 天。建议：{tip}"


# ---------- 导出复习卷 ----------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ max-width: 820px; margin: 40px auto; padding: 0 20px; color: #222;
       font-family: "Microsoft YaHei", "PingFang SC", sans-serif; line-height: 1.75; }}
h1 {{ border-bottom: 3px solid #2b6cb0; padding-bottom: 8px; }}
h2 {{ color: #2b6cb0; margin-top: 32px; }}
pre {{ background: #f5f5f5; padding: 12px; border-radius: 6px; overflow-x: auto; }}
code {{ background: #f5f5f5; padding: 1px 4px; border-radius: 3px; }}
table {{ border-collapse: collapse; }} th, td {{ border: 1px solid #ccc; padding: 6px 10px; }}
.meta {{ color: #888; font-size: 14px; }}
@media print {{ body {{ margin: 0 auto; }} }}
</style></head><body>
<h1>{title}</h1>
<p class="meta">生成时间：{time} · 期末复习助手</p>
{body}
</body></html>"""


@tool
def save_review_sheet(title: str, markdown_content: str) -> str:
    """把复习卷（Markdown 格式）转换为 HTML 文件，保存到 output/ 目录并返回文件路径。

    Args:
        title: 复习卷标题，如 "数据结构·树与二叉树 复习卷"
        markdown_content: 复习卷正文（Markdown 格式，不用再写一级标题）
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    # Markdown → HTML，开启表格和代码块扩展
    body = markdown.markdown(markdown_content, extensions=["tables", "fenced_code"])
    now = datetime.now()
    page = HTML_TEMPLATE.format(title=html.escape(title), time=f"{now:%Y-%m-%d %H:%M}", body=body)
    # 去掉 Windows 文件名中的非法字符，并加时间戳避免重名覆盖
    safe_title = re.sub(r'[\\/:*?"<>|\s]+', "_", title)[:40]
    path = OUTPUT_DIR / f"{safe_title}_{now:%Y%m%d_%H%M%S}.html"
    path.write_text(page, encoding="utf-8")
    return f"已保存：{path.relative_to(BASE_DIR).as_posix()}"
