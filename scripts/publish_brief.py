#!/usr/bin/env python3
"""把一篇 Markdown 論文導讀轉成本站 writing 頁並更新首頁索引。

用法：python3 scripts/publish_brief.py <brief.md> [--no-push]
  - 產出 writing/brief-YYYY-MM-DD.html（站上統一版型）
  - 在 index.html 的 writing 區最上方插入一張卡片
  - git commit + push（--no-push 只 commit）

Markdown 支援子集：# 標題、- 清單、**粗體**、[連結](url)、段落。夠用就好。
"""
import datetime
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Reynolds Liu</title>
<meta name="description" content="{desc}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='18' fill='%230d1117'/><text x='18' y='68' font-family='monospace' font-size='52' fill='%233fd68f'>&gt;_</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<div class="wrap">
<nav class="top">
  <a class="home" href="../index.html">reynoldsliu</a>
  <a href="../index.html#projects">projects</a>
  <a href="../index.html#writing">writing</a>
  <a href="../index.html#contact">contact</a>
</nav>
<article>
<h1>{title}</h1>
<p class="sub">{date} · 每週論文導讀（自動發佈）</p>
{body}
<p><a class="back" href="../index.html">← cd ~</a></p>
</article>
</div>
</body>
</html>
"""


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md_to_html(md: str) -> tuple[str, str]:
    """回傳 (title, body_html)。第一個 # 標題作為頁面標題。"""
    title, out, para, in_list = "", [], [], False

    def flush_para():
        nonlocal para
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for line in md.splitlines():
        s = line.strip()
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            flush_para(); close_list()
            level, text = len(m.group(1)), m.group(2)
            if level == 1 and not title:
                title = text
            else:
                out.append(f"<h2>{inline(text)}</h2>")
        elif s.startswith(("- ", "* ")):
            flush_para()
            if not in_list:
                out.append('<ul class="plain">')
                in_list = True
            out.append("<li>" + inline(s[2:]) + "</li>")
        elif not s:
            flush_para(); close_list()
        else:
            para.append(s)
    flush_para(); close_list()
    return title or "論文導讀", "\n".join(out)


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    push = "--no-push" not in sys.argv
    today = datetime.date.today().isoformat()
    title, body = md_to_html(src.read_text(encoding="utf-8"))
    desc = f"{today} 論文導讀：{title}"

    page = ROOT / "writing" / f"brief-{today}.html"
    page.write_text(PAGE.format(title=html.escape(title), desc=html.escape(desc),
                                date=today, body=body), encoding="utf-8")

    # 首頁 writing 區最上方插卡（idempotent：同日重跑先移除舊卡）
    idx = ROOT / "index.html"
    t = idx.read_text(encoding="utf-8")
    t = re.sub(rf'  <a class="post" href="writing/brief-{today}\.html">.*?</a>\n', "", t, flags=re.S)
    card = (f'  <a class="post" href="writing/brief-{today}.html">\n'
            f'    <b>{html.escape(title)}</b>\n'
            f'    <span>{today} · 每週論文導讀（自動發佈）</span>\n  </a>\n')
    marker = "<h2>技術寫作</h2>\n"
    if marker not in t:
        sys.exit("index.html 找不到 writing 區塊")
    t = t.replace(marker, marker + card, 1)
    idx.write_text(t, encoding="utf-8")

    subprocess.run(["git", "-C", str(ROOT), "add", "-A"], check=True)
    r = subprocess.run(["git", "-C", str(ROOT), "commit", "-m", f"每週論文導讀：{title}（自動發佈）"],
                       capture_output=True, text=True)
    if r.returncode != 0 and "nothing to commit" not in r.stdout:
        sys.exit(r.stdout + r.stderr)
    if push:
        subprocess.run(["git", "-C", str(ROOT), "push"], check=True)
    print(page)
    return 0


if __name__ == "__main__":
    sys.exit(main())
