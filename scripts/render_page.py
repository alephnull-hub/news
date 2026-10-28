#!/usr/bin/env python3
"""Render briefings/*.json into one Artifact page at site/index.html.

The newest briefing shows first; older ones are reachable from the date picker
(and by #YYYY-MM-DD in the link). The briefing JSON format is described in
prompts/daily-briefing.md. Every string from the JSON is HTML-escaped here.

Standard library only. Usage: python3 scripts/render_page.py [--keep 60]
"""
import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_news import FEEDS  # noqa: E402  (feed names for the footer)

WEEKDAYS = "월화수목금토일"
WEEKDAYS_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def e(text):
    return html.escape(str(text or ""), quote=True)


def link(src, cls=""):
    """src: {"label", "url"}. Only http(s) URLs become links."""
    if not src:
        return ""
    label, url = e(src.get("label")), str(src.get("url") or "")
    if url.startswith(("https://", "http://")):
        c = f' class="{cls}"' if cls else ""
        return f'<a{c} href="{e(url)}" target="_blank" rel="noopener">{label}</a>'
    return label


def item(x):
    """A list entry: a plain string, or {"text", "source"}."""
    if isinstance(x, dict):
        src = f' ({link(x.get("source"))})' if x.get("source") else ""
        return f"{e(x.get('text'))}{src}"
    return e(x)


def sec_head(title, note="", level=2):
    note_html = f'<span class="note">{e(note)}</span>' if note else ""
    return f'<div class="sec-head"><h{level}>{e(title)}</h{level}>{note_html}</div>'


def market(day, m):
    out = [f'<section id="{day}-market">', sec_head("시장 스냅샷", m.get("note")), '<div class="board">']
    for t in m.get("tiles", []):
        d = t.get("dir", "flat")
        cls = d if d in ("up", "down", "flat", "na") else "flat"
        arrow = {"up": "▲ ", "down": "▼ "}.get(cls, "")
        out.append(f'<div class="tick"><span class="name">{e(t.get("name"))}</span>'
                   f'<span class="val{" na" if cls == "na" else ""}">{e(t.get("value"))}</span>'
                   f'<span class="chg {cls}">{arrow}{e(t.get("change"))}</span>'
                   + (f'<span class="asof">{e(t.get("note"))}</span>' if t.get("note") else "") + "</div>")
    out.append("</div>")
    srcs = ", ".join(link(s) for s in m.get("sources", []))
    if m.get("foot") or srcs:
        out.append(f'<p class="board-foot">{e(m.get("foot"))}{" 출처: " + srcs if srcs else ""}</p>')
    out.append("</section>")
    return "\n".join(out)


def issues(day, key, title, data):
    out = [f'<section id="{day}-{key}">', sec_head(title, "보도 건수 순")]
    if key == "domestic":
        out.append('<p class="rank-note">건수는 수집한 기사 가운데 제목에 해당 이슈의 핵심어가 들어간 기사 수입니다. '
                   "한 기사가 여러 이슈에 함께 잡힐 수 있습니다.</p>")
    out.append('<div class="issues">')
    for x in data:
        chips = "".join(f'<span class="chip">{e(t)}</span>' for t in x.get("tags", []))
        if x.get("count") is not None:
            chips += f'<span class="chip count">{e(x["count"])}건</span>'
        srcs = "".join(link(s) for s in x.get("sources", []))
        out.append(
            '<article class="issue"><div class="issue-body">'
            f'<h3>{e(x.get("title"))}</h3><div class="chips">{chips}</div>'
            f'<p>{e(x.get("summary"))}</p>'
            + (f'<p class="why"><b>왜 중요한가</b>{e(x.get("why"))}</p>' if x.get("why") else "")
            + f'<div class="src">{srcs}</div></div></article>')
    out.append("</div></section>")
    return "\n".join(out)


def industry(day, rows):
    out = [f'<section id="{day}-industry">', sec_head("산업·기업 동향", "투자·M&A·규제"), '<ul class="rows">']
    for r in rows:
        out.append(f'<li><span><span class="who">{e(r.get("who"))}</span>{e(r.get("what"))}</span>'
                   f'<span class="from">{link(r.get("source"))}</span></li>')
    out.append("</ul></section>")
    return "\n".join(out)


def trends(day, cards, search):
    out = [f'<section id="{day}-trend">', sec_head("트렌드 인사이트", "여러 기사를 묶어 해석한 내용입니다")]
    for c in cards:
        ev = "".join(f"<li>{item(x)}</li>" for x in c.get("evidence", []))
        out.append(f'<article class="trend"><h3>{e(c.get("title"))}</h3><p class="label">근거</p><ul>{ev}</ul>'
                   f'<p class="insight"><b>분석</b>{e(c.get("insight"))}</p></article>')
    if search and search.get("items"):
        out.append(sec_head("오늘 아침 급상승 검색어", search.get("note"), level=3))
        out.append('<div class="kw">' + "".join(
            f'<span>{e(k.get("term"))}<small>{e(k.get("traffic"))}</small></span>' for k in search["items"]) + "</div>")
        if search.get("comment"):
            out.append(f'<p class="kw-note">{e(search["comment"])}</p>')
    out.append("</section>")
    return "\n".join(out)


def explainers(day, rows):
    out = [f'<section id="{day}-explain">', sec_head("쉽게 읽는 해설", "어피티 · 뉴닉"), '<ul class="explain">']
    for r in rows:
        src = r.get("source") or {}
        out.append(f'<li><span class="pub">{e(src.get("label"))}</span>'
                   f'<h3>{link({"label": r.get("title"), "url": src.get("url")})}</h3>'
                   + (f'<p>{e(r.get("summary"))}</p>' if r.get("summary") else "") + "</li>")
    out.append("</ul></section>")
    return "\n".join(out)


def schedule(day, s):
    out = [f'<section id="{day}-schedule">', sec_head("이번 주 일정", s.get("note", "모두 한국 시간")),
           '<div class="sched-wrap"><table class="sched"><thead><tr><th>날짜·시각</th><th>일정</th><th>볼 것</th></tr></thead><tbody>']
    for r in s.get("rows", []):
        hot = ' class="hot"' if r.get("hot") else ""
        out.append(f'<tr{hot}><td class="t">{e(r.get("when"))}</td><td>{e(r.get("event"))}</td><td>{e(r.get("watch"))}</td></tr>')
    out.append("</tbody></table></div>")
    srcs = ", ".join(link(x) for x in s.get("sources", []))
    if srcs or s.get("foot"):
        out.append(f'<p class="board-foot">{e(s.get("foot"))}{" 출처: " + srcs if srcs else ""}</p>')
    out.append("</section>")
    return "\n".join(out)


def watch(day, w):
    opp = "".join(f"<li>{item(x)}</li>" for x in w.get("opportunities", []))
    risk = "".join(f"<li>{item(x)}</li>" for x in w.get("risks", []))
    kws = "".join(f"<span>{e(k)}</span>" for k in w.get("keywords", []))
    return (f'<section id="{day}-watch">' + sec_head("생각해 볼 점", "분석 · 투자 권유가 아닙니다")
            + f'<div class="watch"><div class="opp"><h3>기회</h3><ul>{opp}</ul></div>'
            f'<div class="risk"><h3>리스크</h3><ul>{risk}</ul></div></div>'
            + (f'<div class="kw" aria-label="지켜볼 키워드">{kws}</div>' if kws else "") + "</section>")


def footer(b):
    names = {r: [n for n, reg, _ in FEEDS if reg == r] for r in ("domestic", "global", "trend", "explainer")}
    c = b.get("collection", {})
    failed = c.get("failed") or []
    notes = "".join(f"<p><b>메모</b> {e(n)}</p>" for n in b.get("notes", []))
    return (
        "<footer>"
        f"<p><b>수집 방법</b> 국내 {len(names['domestic'])}개({e(', '.join(names['domestic']))}), "
        f"해외 {len(names['global'])}개({e(', '.join(names['global']))}), "
        f"트렌드 {len(names['trend'])}개({e(', '.join(names['trend']))}), "
        f"해설 {len(names['explainer'])}개({e(', '.join(names['explainer']))})에서 직전 24시간 기사를 모았습니다. "
        "뉴닉은 RSS가 없어 공개 사이트맵과 기사 메타 정보(제목·요약)만 읽었고, 어피티의 광고 글은 제외했습니다."
        + (f" 이번에 열리지 않은 피드: {e(', '.join(failed))}." if failed else "")
        + " 시장 지표는 한국은행 ECOS·FRED(키가 있을 때)와 시황 기사 본문에서, 일정은 공개 캘린더 기사에서 확인했습니다.</p>"
        "<p><b>읽을 때 참고</b> Claude가 기사 제목·공개 요약·본문을 바탕으로 작성했습니다. 유료 기사는 헤드라인만 썼습니다. "
        "모든 숫자에는 기준일과 출처를 붙였고, 확인하지 못한 값은 ‘확인 불가’로 남겼습니다. "
        "이 리포트를 쓴 Claude는 Anthropic이 만든 AI이며, 앤트로픽 관련 기사도 다른 기사와 같은 기준(보도 건수)으로 골랐습니다.</p>"
        f"{notes}"
        "<p>투자 판단의 근거로 쓰지 마세요. 개별 종목·자산에 대한 매매 권유가 아닙니다. "
        '등락 색은 국내 관례를 따릅니다: <span class="up">상승 빨강</span>, <span class="down">하락 파랑</span>.</p>'
        "</footer>")


def render(b, options):
    day = b["date"]
    d = date.fromisoformat(day)
    c = b.get("collection", {})
    stats = " · ".join(x for x in [
        f"수집 {c['window']}" if c.get("window") else "",
        f"피드 {c['feeds_ok']}/{c['feeds_total']}개" if c.get("feeds_total") else "",
        f"기사 {c['articles']:,}건" if c.get("articles") else "",
    ] if x)
    toc = [("market", "시장"), ("domestic", "국내 TOP 5"), ("global", "글로벌 TOP 5"), ("industry", "산업·기업"),
           ("trend", "트렌드"), ("explain", "쉽게 읽기"), ("schedule", "일정"), ("watch", "생각해 볼 점")]
    parts = [
        f'<article class="wrap briefing" data-day="{day}" hidden>',
        '<header class="mast"><div class="mast-top">'
        f'<span>MORNING BRIEF · {d:%Y.%m.%d} {WEEKDAYS_EN[d.weekday()]}</span><span>{e(stats)}</span></div>'
        f'<h1>{e(b.get("title") or "오늘의 비즈니스·경제 브리핑")}</h1>'
        f'<p class="lead">{e(b.get("lead"))}</p>'
        '<ul class="toc" aria-label="목차">' + "".join(f'<li><a href="#{day}-{k}">{label}</a></li>' for k, label in toc) + "</ul>"
        "</header>",
    ]
    if b.get("market"):
        parts.append(market(day, b["market"]))
    if b.get("domestic"):
        parts.append(issues(day, "domestic", "국내 경제·비즈니스 TOP 5", b["domestic"]))
    if b.get("global"):
        parts.append(issues(day, "global", "글로벌 경제 TOP 5", b["global"]))
    if b.get("industry"):
        parts.append(industry(day, b["industry"]))
    if b.get("trends") or b.get("search_trends"):
        parts.append(trends(day, b.get("trends", []), b.get("search_trends")))
    if b.get("explainers"):
        parts.append(explainers(day, b["explainers"]))
    if b.get("schedule"):
        parts.append(schedule(day, b["schedule"]))
    if b.get("watch"):
        parts.append(watch(day, b["watch"]))
    parts.append(footer(b))
    parts.append("</article>")
    return "\n".join(parts)


STYLE = """<title>아침 경제 브리핑</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=Noto+Serif+KR:wght@600;700&display=swap">
<style>
/* Layout: 증권사 모닝노트 — 한 줄 요약과 시세판을 먼저, 이어서 읽기 좋은 단일 칼럼 */
:root {
  --bg: #f3f5f8; --surface: #ffffff; --ink: #16202b; --muted: #5a6574; --line: #dce1e8;
  --accent: #1d3f72; --accent-soft: #e6edf7;
  --up: #d22f3c; --down: #1f62d0; --flat: #6b7480; --na: #8a6d1f;  /* 한국 증시 관례: 상승 빨강, 하락 파랑 */
  --font-display: "Noto Serif KR", "Nanum Myeongjo", "Batang", serif;
  --font-body: "IBM Plex Sans KR", "Malgun Gothic", "Apple SD Gothic Neo", system-ui, sans-serif;
  --font-data: "IBM Plex Mono", ui-monospace, "Consolas", monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0e131a; --surface: #151c25; --ink: #e5eaf0; --muted: #95a0ad; --line: #26303b;
  --accent: #9dbdf0; --accent-soft: #1b2738; --up: #ff6b70; --down: #6ea3ff; --flat: #8c96a3; --na: #d8b55a;
  color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #0e131a; --surface: #151c25; --ink: #e5eaf0; --muted: #95a0ad; --line: #26303b;
  --accent: #9dbdf0; --accent-soft: #1b2738; --up: #ff6b70; --down: #6ea3ff; --flat: #8c96a3; --na: #d8b55a;
  color-scheme: dark; }

* { box-sizing: border-box; }
body { background: var(--bg); color: var(--ink); font-family: var(--font-body); font-size: 16px; line-height: 1.7;
  word-break: keep-all; overflow-wrap: anywhere; }
a { color: var(--accent); text-underline-offset: 3px; }
a:focus-visible, button:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }

.wrap { max-width: 820px; margin: 0 auto; padding-block: 24px 64px; display: grid; gap: 48px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }

/* Archive picker */
.archive { max-width: 820px; margin: 0 auto; padding-top: 16px; display: flex; justify-content: flex-end; align-items: center; gap: 6px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.archive span { font-size: 12.5px; color: var(--muted); margin-right: auto; }
.archive button, .archive select { font: 500 13px/1 var(--font-body); color: var(--ink); background: var(--surface);
  border: 1px solid var(--line); border-radius: 6px; padding: 7px 10px; }
.archive button { cursor: pointer; min-width: 2.25rem; }
.archive button:disabled { opacity: .4; cursor: default; }

/* Masthead */
.mast { display: grid; gap: 14px; border-bottom: 2px solid var(--ink); padding-bottom: 20px; }
.mast-top { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; font-family: var(--font-data); font-size: 12.5px; color: var(--muted); letter-spacing: 0.04em; }
.mast h1 { font-family: var(--font-display); font-size: clamp(30px, 6vw, 42px); line-height: 1.2; margin: 0; text-wrap: balance; letter-spacing: -0.01em; }
.lead { font-family: var(--font-display); font-weight: 600; font-size: clamp(18px, 3.2vw, 21px); line-height: 1.65; margin: 0; max-width: 40em; }
.toc { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 14px; padding: 0; margin: 0; list-style: none; }
.toc a { text-decoration: none; color: var(--muted); }
.toc a:hover { color: var(--accent); text-decoration: underline; }

/* Section heads */
section { display: grid; gap: 18px; scroll-margin-top: 16px; }
.sec-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; border-bottom: 1px solid var(--line); padding-bottom: 8px; }
.sec-head h2 { font-size: 20px; margin: 0; letter-spacing: -0.01em; }
.sec-head h3 { font-size: 17px; margin: 0; }
.sec-head .note { font-size: 13px; color: var(--muted); }

/* Market board */
.board { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
.tick { background: var(--surface); padding: 14px 14px 12px; display: grid; gap: 2px; min-width: 0; align-content: start; }
.tick .name { font-size: 13px; color: var(--muted); }
.tick .val { font-family: var(--font-data); font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.tick .val.na { font-family: var(--font-body); font-size: 15px; font-weight: 500; color: var(--na); padding-block: 4px; }
.tick .chg { font-family: var(--font-data); font-size: 13.5px; font-variant-numeric: tabular-nums; }
.tick .asof { font-size: 11.5px; color: var(--muted); margin-top: 4px; }
.up { color: var(--up); } .down { color: var(--down); } .flat { color: var(--flat); } .chg.na { color: var(--muted); }
.board-foot { font-size: 13px; color: var(--muted); margin: 0; }

/* Issue list */
.issues { display: grid; gap: 0; counter-reset: rank; }
.issue { display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 4px 12px; padding-block: 20px; border-bottom: 1px solid var(--line); }
.issue:first-child { padding-top: 4px; }
.issue::before { counter-increment: rank; content: counter(rank); font-family: var(--font-data); font-size: 15px; font-weight: 600; color: var(--accent); padding-top: 3px; }
.issue-body { display: grid; gap: 8px; min-width: 0; }
.issue h3 { font-family: var(--font-display); font-size: 19px; line-height: 1.45; margin: 0; text-wrap: balance; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 12px; line-height: 1; padding: 5px 8px; border-radius: 4px; background: var(--accent-soft); color: var(--accent); white-space: nowrap; }
.chip.count { background: transparent; border: 1px solid var(--line); color: var(--muted); font-family: var(--font-data); }
.issue p { margin: 0; }
.why { border-left: 3px solid var(--accent); padding: 2px 0 2px 12px; color: var(--ink); }
.why b { font-size: 13px; letter-spacing: 0.02em; color: var(--accent); margin-right: 6px; }
.src { font-size: 13px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 4px 12px; }
.src a { color: var(--muted); }
.src a:hover { color: var(--accent); }
.rank-note { font-size: 13px; color: var(--muted); margin: -6px 0 0; }

/* Industry rows */
.rows { list-style: none; margin: 0; padding: 0; display: grid; }
.rows li { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 16px; padding-block: 11px; border-bottom: 1px dashed var(--line); align-items: baseline; }
.rows li:last-child { border-bottom: 0; }
.rows .who { font-weight: 600; margin-right: 6px; }
.rows .from { font-size: 12.5px; color: var(--muted); white-space: nowrap; }
.rows .from a { color: var(--muted); }

/* Trends */
.trend { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 20px; display: grid; gap: 12px; }
.trend h3 { font-family: var(--font-display); font-size: 18px; margin: 0; line-height: 1.45; text-wrap: balance; }
.trend .label { font-size: 12.5px; font-weight: 600; color: var(--muted); letter-spacing: 0.04em; margin: 0; }
.trend ul { margin: 0; padding-left: 18px; display: grid; gap: 4px; }
.trend .insight { margin: 0; padding: 12px 14px; background: var(--accent-soft); border-radius: 6px; }
.trend .insight b { color: var(--accent); margin-right: 6px; font-size: 13px; }
.kw { display: flex; flex-wrap: wrap; gap: 8px; }
.kw span { font-size: 14px; border: 1px solid var(--line); background: var(--surface); border-radius: 999px; padding: 5px 12px; }
.kw small { font-family: var(--font-data); color: var(--muted); margin-left: 6px; font-size: 12px; }
.kw-note { margin: 0; font-size: 14px; color: var(--muted); }

/* Explainers */
.explain { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.explain li { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px; display: grid; gap: 6px; align-content: start; min-width: 0; }
.explain .pub { font-size: 12px; font-weight: 600; color: var(--muted); letter-spacing: 0.04em; }
.explain h3 { font-size: 16px; line-height: 1.5; margin: 0; text-wrap: pretty; }
.explain h3 a { color: var(--ink); text-decoration: none; }
.explain h3 a:hover { color: var(--accent); text-decoration: underline; }
.explain p { margin: 0; font-size: 14px; color: var(--muted); }

/* Schedule */
.sched-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); }
table.sched { border-collapse: collapse; width: 100%; min-width: 520px; font-size: 14.5px; }
.sched th, .sched td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--line); vertical-align: top; }
.sched tr:last-child td { border-bottom: 0; }
.sched th { font-size: 12.5px; color: var(--muted); font-weight: 600; background: var(--bg); }
.sched td.t { font-family: var(--font-data); font-variant-numeric: tabular-nums; white-space: nowrap; font-size: 13.5px; }
.sched tr.hot td.t { color: var(--up); font-weight: 600; }

/* Watch */
.watch { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.watch > div { border-top: 3px solid var(--line); padding-top: 12px; display: grid; gap: 8px; align-content: start; min-width: 0; }
.watch .opp { border-top-color: var(--up); }
.watch .risk { border-top-color: var(--down); }
.watch h3 { font-size: 16px; margin: 0; }
.watch ul { margin: 0; padding-left: 18px; display: grid; gap: 6px; }

/* Footer */
footer { border-top: 2px solid var(--ink); padding-top: 16px; font-size: 13px; color: var(--muted); display: grid; gap: 8px; }
footer p { margin: 0; }

@media (max-width: 640px) {
  .wrap { gap: 40px; padding-block: 20px 48px; }
  .board { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .watch, .explain { grid-template-columns: minmax(0, 1fr); }
  .rows li { grid-template-columns: minmax(0, 1fr); }
  .issue { grid-template-columns: 26px minmax(0, 1fr); }
}
@media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
</style>
"""

SCRIPT = """<script>
(function () {
  var articles = Array.prototype.slice.call(document.querySelectorAll(".briefing"));
  var days = articles.map(function (a) { return a.dataset.day; });  // newest first
  var picker = document.getElementById("date-picker");
  var prev = document.getElementById("prev-day");
  var next = document.getElementById("next-day");

  function show(day) {
    if (days.indexOf(day) < 0) day = days[0];
    articles.forEach(function (a) { a.hidden = a.dataset.day !== day; });
    picker.value = day;
    var i = days.indexOf(day);
    next.disabled = i <= 0;
    prev.disabled = i >= days.length - 1;
  }
  // The hash is either a day (2026-10-28) or a section within a day (2026-10-28-market).
  function route() {
    var h = location.hash.slice(1);
    show(h.slice(0, 10));
    if (h.length > 10) {
      var el = document.getElementById(h);
      if (el) el.scrollIntoView();
    }
  }
  function go(day) {
    if (day === days[0]) history.replaceState(null, "", location.pathname + location.search);
    else location.hash = day;
    show(day);
    window.scrollTo(0, 0);
  }
  picker.addEventListener("change", function () { go(picker.value); });
  prev.addEventListener("click", function () { go(days[Math.min(days.indexOf(picker.value) + 1, days.length - 1)]); });
  next.addEventListener("click", function () { go(days[Math.max(days.indexOf(picker.value) - 1, 0)]); });
  window.addEventListener("hashchange", route);
  route();
})();
</script>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=int, default=60, help="number of most recent briefings to include")
    args = parser.parse_args()

    files = sorted((ROOT / "briefings").glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"), reverse=True)[:args.keep]
    if not files:
        print("no briefings found", file=sys.stderr)
        return 1
    articles, options = [], []
    for f in files:
        b = json.loads(f.read_text(encoding="utf-8"))
        b.setdefault("date", f.stem)
        d = date.fromisoformat(b["date"])
        articles.append(render(b, options))
        options.append(f'<option value="{b["date"]}">{d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})</option>')
    articles[0] = articles[0].replace(" hidden>", ">", 1)  # without JS the newest still shows

    picker = ('<nav class="archive" aria-label="지난 브리핑"><span>아침 경제 브리핑 · 매일 07:40 KST</span>'
              '<button type="button" id="prev-day" aria-label="이전 브리핑">‹</button>'
              f'<select id="date-picker" aria-label="브리핑 날짜">{"".join(options)}</select>'
              '<button type="button" id="next-day" aria-label="다음 브리핑">›</button></nav>')
    out = ROOT / "site" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(STYLE + picker + "\n".join(articles) + SCRIPT, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} with {len(files)} briefing(s), newest {files[0].stem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
