import logging
from datetime import datetime

import markdown

logger = logging.getLogger(__name__)

CSS = """
body {
    font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
    max-width: 680px;
    margin: 0 auto;
    padding: 20px;
    color: #333;
    background: #fafafa;
    line-height: 1.8;
}
h1 { font-size: 22px; border-bottom: 3px solid #4A90D9; padding-bottom: 10px; }
h2 { font-size: 18px; color: #4A90D9; margin-top: 28px; }
h3 { font-size: 15px; color: #666; margin-top: 16px; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }
th, td { padding: 8px 10px; border-bottom: 1px solid #e0e0e0; text-align: left; }
th { background: #f0f4f8; font-weight: bold; }
tr:hover { background: #f5f8fb; }
blockquote {
    border-left: 3px solid #4A90D9;
    margin: 8px 0;
    padding: 4px 12px;
    color: #555;
    background: #f0f4f8;
}
code { background: #e8e8e8; padding: 1px 4px; border-radius: 3px; font-size: 13px; }
.highlight { color: #e67e22; font-weight: bold; }
.muted { color: #999; font-size: 12px; }
.meta { color: #999; font-size: 13px; margin-top: 4px; }
.footer {
    margin-top: 30px;
    padding-top: 15px;
    border-top: 1px solid #e0e0e0;
    color: #999;
    font-size: 12px;
}
.error-note { color: #c0392b; font-style: italic; }
.tag {
    display: inline-block;
    background: #e8f0fe;
    color: #4A90D9;
    padding: 2px 8px;
    border-radius: 3px;
    margin: 2px 4px 2px 0;
    font-size: 12px;
}
"""

HTML_TEMPLATE = """<html>
<head><meta charset="utf-8"><style>{css}</style></head>
<body>
{body}
</body>
</html>"""


def build_briefing(groups_summary, date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y年%m月%d日")

    md = _build_markdown(groups_summary, date_str)
    html_body = markdown.markdown(md, extensions=["extra", "nl2br"])
    html = HTML_TEMPLATE.format(css=CSS, body=html_body)
    return html


def _build_markdown(groups_summary, date_str):
    lines = [
        f"# 每日简报 — {date_str}",
        "",
        "## QQ群聊摘要",
        "",
    ]
    has_valid = False

    for g in groups_summary:
        lines.append(f"### {g['group_name']} ({g['group_id']})")
        lines.append("")

        if g.get("error"):
            lines.append(f'<span class="error-note"> 无法获取: {g["error"]}</span>')
            lines.append("")
            continue

        has_valid = True
        lines.append(f"- **消息数**: {g['message_count']} 条 | **活跃成员**: {g['active_members']} 人")
        lines.append("")

        if g.get("top_talkers"):
            tags = " ".join(f'<span class="tag">{t}</span>' for t in g["top_talkers"])
            lines.append(f"- **活跃成员**: {tags}")
            lines.append("")

        if g.get("keyword_highlights"):
            tags = " ".join(f'<span class="tag">{k}</span>' for k in g["keyword_highlights"])
            lines.append(f"- **热点关键词**: {tags}")
            lines.append("")

        if g.get("sample_messages"):
            lines.append("- **精选消息**:")
            lines.append("")
            for msg in g["sample_messages"]:
                lines.append(f"> **{msg['sender']}** ({msg['time']}): {msg['content']}")
                lines.append("")
            lines.append("")

    if not has_valid and not groups_summary:
        lines.append("今日暂无 QQ 群聊数据。")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f'<div class="footer"> 本简报由 daily-briefing 自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>')

    return "\n".join(lines)
