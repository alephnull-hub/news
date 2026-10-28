#!/usr/bin/env python3
"""Render briefings/*.md into one Artifact page at site/index.html.

The newest briefing shows first; older ones are reachable from the date picker
(and by #YYYY-MM-DD in the link). Handles only the Markdown that the briefing
template uses: headings, blockquotes, tables, lists, bold, links, inline code, rules.

Standard library only. Usage: python3 scripts/render_page.py [--keep 60]
"""
import argparse
import html
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEEKDAYS = "월화수목금토일"


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                  lambda m: f'<a href="{html.escape(m.group(2))}" target="_blank" rel="noopener">{m.group(1)}</a>',
                  text)


def change_class(cell):
    # Korean market convention: rises in red, falls in blue.
    s = cell.strip()
    if s.startswith("+"):
        return "up"
    if s.startswith(("−", "-")) and s not in ("—", "-"):
        return "down"
    return ""


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], [r for r in cells[1:] if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
    change_cols = {i for i, h in enumerate(head) if h == "등락"}
    out = ['<div class="table-wrap"><table><thead><tr>']
    out += [f"<th>{inline(h)}</th>" for h in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>")
        for i, c in enumerate(r):
            cls = change_class(c) if i in change_cols else ""
            if c == "확인 불가":
                cls = "na"
            out.append(f'<td class="{cls}">{inline(c)}</td>' if cls else f"<td>{inline(c)}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def blocks(lines):
    """Convert a list of Markdown lines to HTML."""
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("|"):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            out.append(table(lines[i:j]))
            i = j
        elif line.startswith(">"):
            j = i
            while j < len(lines) and lines[j].startswith(">"):
                j += 1
            text = " ".join(l.lstrip("> ").strip() for l in lines[i:j])
            out.append(f"<blockquote>{inline(text)}</blockquote>")
            i = j
        elif re.match(r"(\d+\.|-) ", line):
            ordered = line[0].isdigit()
            j, items = i, []
            while j < len(lines) and re.match(r"(\d+\.|-) ", lines[j]):
                items.append(re.sub(r"^(\d+\.|-) ", "", lines[j]))
                j += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t)}</li>" for t in items) + f"</{tag}>")
            i = j
        elif line.startswith("### "):
            out.append(f"<h4>{inline(line[4:])}</h4>")
            i += 1
        else:
            j = i
            while j < len(lines) and lines[j].strip() and not re.match(r"(\||>|#|\d+\. |- )", lines[j]):
                j += 1
            out.append(f"<p>{inline(' '.join(l.strip() for l in lines[i:max(j, i + 1)]))}</p>")
            i = max(j, i + 1)
    return "\n".join(out)


def render_briefing(day, text):
    lines = text.splitlines()
    # Everything after the closing rule is collection metadata and notes.
    if "---" in lines:
        cut = len(lines) - 1 - lines[::-1].index("---")
        lines, footer = lines[:cut], lines[cut + 1:]
    else:
        footer = []

    lede, sections, current = "", [], None
    for line in lines:
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            current = [line[3:].strip(), []]
            sections.append(current)
        elif current is None:
            if line.startswith(">"):
                lede += " " + re.sub(r"^>\s*(한 줄 총평:)?\s*", "", line)
        else:
            current[1].append(line)

    d = date.fromisoformat(day)
    parts = [f'<article class="briefing" id="{day}" data-day="{day}" hidden>',
             '<header class="masthead">',
             f'<p class="dateline"><time datetime="{day}">{d.year}년 {d.month}월 {d.day}일</time>'
             f' <span class="weekday">{WEEKDAYS[d.weekday()]}요일</span></p>']
    if lede.strip():
        parts.append(f'<p class="lede">{inline(lede.strip())}</p>')
    parts.append("</header>")
    parts.append('<div class="sections">')
    for title, body in sections:
        kind = "market" if "시장" in title else "news" if "뉴스" in title else "note"
        parts.append(f'<section class="{kind}"><h2>{inline(title)}</h2>{blocks(body)}</section>')
    parts.append("</div>")
    if footer:
        parts.append(f'<footer class="meta">{blocks(footer)}</footer>')
    parts.append("</article>")
    return "\n".join(parts)


PAGE = """<title>아침 경제 브리핑</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Sans+KR:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a morning sheet. Dateline and one-line verdict up top, then market tables and news in paired columns. */
:root {
  --bg: #f4f6f4; --surface: #ffffff; --fg: #18211d; --muted: #5b6761; --rule: #d6dcd8;
  --accent: #2c5c4b; --up: #c62828; --down: #1d5fc4; --na: #8a6d1f;
  --display: "Gowun Batang", "Noto Serif KR", "Apple SD Gothic Neo", serif;
  --body: "IBM Plex Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  --data: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #101412; --surface: #171c19; --fg: #e4eae6; --muted: #98a49e; --rule: #2a322e;
  --accent: #82c2a9; --up: #ff6b6b; --down: #6aa6ff; --na: #d8b55a; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #101412; --surface: #171c19; --fg: #e4eae6; --muted: #98a49e; --rule: #2a322e;
  --accent: #82c2a9; --up: #ff6b6b; --down: #6aa6ff; --na: #d8b55a; color-scheme: dark; }

body { background: var(--bg); color: var(--fg); font: 400 15px/1.7 var(--body); }
.page { max-width: 72rem; margin: 0 auto; padding-block: 20px 48px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }

.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; justify-content: space-between;
  padding-bottom: 12px; border-bottom: 1px solid var(--rule); }
.brand { font: 600 12px/1 var(--body); letter-spacing: .08em; color: var(--muted); }
.nav { display: flex; align-items: center; gap: 6px; }
.nav button, .nav select { font: 500 13px/1 var(--body); color: var(--fg); background: var(--surface);
  border: 1px solid var(--rule); border-radius: 6px; padding: 7px 10px; }
.nav button { cursor: pointer; min-width: 2.25rem; }
.nav button:disabled { opacity: .4; cursor: default; }
.nav button:focus-visible, .nav select:focus-visible, a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.masthead { padding-block: 28px 24px; display: grid; gap: 10px; }
.dateline { margin: 0; font: 400 clamp(26px, 4.2vw, 40px)/1.2 var(--display); text-wrap: balance; }
.weekday { color: var(--muted); font-size: .6em; margin-left: .3em; }
.lede { margin: 0; max-width: 46rem; font: 500 17px/1.65 var(--body); text-wrap: pretty;
  padding-left: 14px; border-left: 3px solid var(--accent); }

.sections { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 30rem), 1fr)); gap: 28px 40px; }
section { min-width: 0; }
h2 { font: 700 19px/1.3 var(--display); margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--fg); text-wrap: balance; }
section p, section li { max-width: 65ch; }
section p { margin: 12px 0 0; color: var(--fg); }
ol, ul { margin: 0; padding-left: 1.3em; display: grid; gap: 10px; }
li::marker { color: var(--muted); font: 500 13px var(--data); }
strong { font-weight: 600; }
a { color: var(--accent); text-underline-offset: 2px; }
code { font: 13px var(--data); }

.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
th { text-align: left; font: 600 11.5px/1.4 var(--body); letter-spacing: .04em; color: var(--muted);
  padding: 6px 8px; border-bottom: 1px solid var(--rule); white-space: nowrap; }
td { padding: 7px 8px; border-bottom: 1px solid var(--rule); vertical-align: top; }
td:nth-child(2), td:nth-child(3), td:nth-child(4) { font: 13px/1.5 var(--data); font-variant-numeric: tabular-nums; white-space: nowrap; }
td:first-child { font-weight: 500; white-space: nowrap; }
td:last-child { font-size: 12.5px; color: var(--muted); }
td.up { color: var(--up); } td.down { color: var(--down); }
td.na { color: var(--na); font-family: var(--body); }
@media (max-width: 640px) {
  table { font-size: 13px; }
  td:last-child { white-space: nowrap; }  /* the table scrolls sideways instead of growing tall rows */
}

.meta { margin-top: 40px; padding-top: 14px; border-top: 1px solid var(--rule); color: var(--muted); font-size: 13px; }
.meta p { margin: 0 0 8px; max-width: 70ch; }
.meta blockquote { margin: 8px 0 0; padding: 10px 12px; background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; }
.legend { color: var(--muted); font-size: 12px; }
.legend .up { color: var(--up); } .legend .down { color: var(--down); }
</style>

<div class="page">
  <div class="toolbar">
    <span class="brand">아침 경제 브리핑 · 매일 07:40 KST</span>
    <div class="nav">
      <button type="button" id="prev-day" aria-label="이전 브리핑">‹</button>
      <select id="date-picker" aria-label="브리핑 날짜">__OPTIONS__</select>
      <button type="button" id="next-day" aria-label="다음 브리핑">›</button>
    </div>
  </div>
__ARTICLES__
  <p class="legend">등락 색상은 국내 관례를 따릅니다: <span class="up">상승은 빨강</span>, <span class="down">하락은 파랑</span>.</p>
</div>

<script>
(function () {
  var articles = Array.prototype.slice.call(document.querySelectorAll(".briefing"));
  var days = articles.map(function (a) { return a.dataset.day; });
  var picker = document.getElementById("date-picker");
  var prev = document.getElementById("prev-day");
  var next = document.getElementById("next-day");

  function show(day) {
    if (days.indexOf(day) < 0) day = days[0];
    articles.forEach(function (a) { a.hidden = a.dataset.day !== day; });
    picker.value = day;
    var i = days.indexOf(day);  // days are newest first
    next.disabled = i <= 0;
    prev.disabled = i >= days.length - 1;
  }
  function go(day) {
    if (day === days[0]) history.replaceState(null, "", location.pathname + location.search);
    else location.hash = day;
    show(day);
  }
  picker.addEventListener("change", function () { go(picker.value); });
  prev.addEventListener("click", function () { go(days[Math.min(days.indexOf(picker.value) + 1, days.length - 1)]); });
  next.addEventListener("click", function () { go(days[Math.max(days.indexOf(picker.value) - 1, 0)]); });
  window.addEventListener("hashchange", function () { show(location.hash.slice(1)); });
  show(location.hash.slice(1));
})();
</script>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=int, default=60, help="number of most recent briefings to include")
    args = parser.parse_args()

    files = sorted((ROOT / "briefings").glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md"), reverse=True)[:args.keep]
    if not files:
        print("no briefings found", file=sys.stderr)
        return 1
    articles, options = [], []
    for f in files:
        day = f.stem
        d = date.fromisoformat(day)
        articles.append(render_briefing(day, f.read_text(encoding="utf-8")))
        options.append(f'<option value="{day}">{d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})</option>')
    # Without JS the newest briefing should still show.
    articles[0] = articles[0].replace(" hidden>", ">", 1)

    out = ROOT / "site" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(PAGE.replace("__OPTIONS__", "".join(options)).replace("__ARTICLES__", "\n".join(articles)),
                   encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} with {len(files)} briefing(s), newest {files[0].stem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
