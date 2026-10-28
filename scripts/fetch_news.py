#!/usr/bin/env python3
"""Collect recent business/economy headlines from RSS/Atom feeds.

Writes data/<date>/news.json (full items) and data/<date>/titles.txt (one line per
item, for grouping stories and counting coverage). Standard library only.
Usage: python3 scripts/fetch_news.py [--hours 24] [--date YYYY-MM-DD]
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "news-briefing-script/1.0 (+https://github.com/alephnull-hub/news)"
ATOM = "{http://www.w3.org/2005/Atom}"
TRENDS = "{https://trends.google.com/trending/rss}"
SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
NEWNEEK_SITEMAP = "https://newneek.co/sitemap/article-sitemap.xml"

GNEWS = "https://news.google.com/rss"
FEEDS = [
    # (name, region, url) — region: domestic | global | trend | explainer
    ("Google 뉴스 비즈니스", "domestic", f"{GNEWS}/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"),
    ("연합뉴스 경제", "domestic", "https://www.yna.co.kr/rss/economy.xml"),
    ("연합뉴스 마켓", "domestic", "https://www.yna.co.kr/rss/market.xml"),
    ("한국경제 경제", "domestic", "https://www.hankyung.com/feed/economy"),
    ("한국경제 증권", "domestic", "https://www.hankyung.com/feed/finance"),
    ("한국경제 IT", "domestic", "https://www.hankyung.com/feed/it"),
    ("매일경제 경제", "domestic", "https://www.mk.co.kr/rss/30100041/"),
    ("매일경제 증권", "domestic", "https://www.mk.co.kr/rss/50200011/"),
    ("조선일보 경제", "domestic", "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/?outputType=xml"),
    ("서울경제", "domestic", "https://www.sedaily.com/rss/economy"),
    ("머니투데이", "domestic", "https://rss.mt.co.kr/mt_news.xml"),
    ("전자신문", "domestic", "https://rss.etnews.com/Section901.xml"),
    ("연합뉴스 국제", "global", "https://www.yna.co.kr/rss/international.xml"),
    ("한국경제 국제", "global", "https://www.hankyung.com/feed/international"),
    ("Google News US Business", "global", f"{GNEWS}/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en"),
    ("Reuters", "global", f"{GNEWS}/search?q=site:reuters.com+business+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("Bloomberg", "global", f"{GNEWS}/search?q=site:bloomberg.com+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("MarketWatch", "global", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("BBC Business", "global", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("FT", "global", "https://www.ft.com/rss/home"),
    ("Economist", "global", "https://www.economist.com/finance-and-economics/rss.xml"),
    ("Google 트렌드 한국", "trend", "https://trends.google.com/trending/rss?geo=KR"),
    ("모비인사이드", "trend", "https://www.mobiinside.co.kr/feed/"),
    ("벤처스퀘어", "trend", "https://www.venturesquare.net/feed"),
    ("TechCrunch", "trend", "https://techcrunch.com/feed/"),
    ("Hacker News", "trend", "https://hnrss.org/frontpage"),
    ("Product Hunt", "trend", "https://www.producthunt.com/feed"),
    ("어피티", "explainer", "https://uppity.co.kr/feed/"),
    ("뉴닉", "explainer", NEWNEEK_SITEMAP),  # no RSS; read via its public article sitemap
]


def fetch(url, attempts=2):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except urllib.error.HTTPError:
            raise  # the server answered; retrying won't change it
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(2)  # transient connection reset or timeout


def clean(text):
    text = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    if re.match(r"\d{4}-\d{2}-\d{2}T", value):  # Atom / ISO 8601
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        # Some feeds (e.g. mk.co.kr) write the offset as "+09:00", which email.utils reads as UTC.
        value = re.sub(r"([+-]\d{2}):(\d{2})\s*$", r"\1\2", value)
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


def entries(root):
    """Yield (title, link, summary, published, publisher, extra) for RSS items or Atom entries."""
    for item in root.iter("item"):
        source = item.find("source")  # Google News names the original publisher here
        extra = {}
        traffic = item.findtext(f"{TRENDS}approx_traffic")
        if traffic:
            extra["traffic"] = traffic.strip()
            news = item.find(f"{TRENDS}news_item")
            if news is not None:
                extra["related"] = clean(news.findtext(f"{TRENDS}news_item_title"))
                extra["related_url"] = (news.findtext(f"{TRENDS}news_item_url") or "").strip()
        categories = [c.text or "" for c in item.findall("category")]
        if any(re.search(r"(^|\s)AD$|광고", c) for c in categories):
            continue  # sponsored posts (e.g. uppity "머니레터 AD")
        yield (item.findtext("title"), item.findtext("link"), item.findtext("description"),
               item.findtext("pubDate"), source.text if source is not None else None, extra)
    for entry in root.iter(f"{ATOM}entry"):
        link = entry.find(f"{ATOM}link")
        yield (entry.findtext(f"{ATOM}title"), link.get("href") if link is not None else "",
               entry.findtext(f"{ATOM}summary") or entry.findtext(f"{ATOM}content"),
               entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated"), None, {})


def meta(page, key):
    m = re.search(rf'<meta (?:property|name)="{re.escape(key)}" content="([^"]*)"', page)
    return html.unescape(m.group(1)) if m else ""


def newneek_entries(root, cutoff):
    """Newneek's own articles (@newneek) modified since cutoff, with title and date from each page's meta tags."""
    since = cutoff.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    urls = [u.findtext(f"{SITEMAP}loc") for u in root.iter(f"{SITEMAP}url")
            if "/@newneek/article/" in (u.findtext(f"{SITEMAP}loc") or "") and (u.findtext(f"{SITEMAP}lastmod") or "") >= since]
    for url in urls[:60]:
        try:
            page = fetch(url).decode("utf-8", errors="replace")
        except Exception:
            continue
        time.sleep(0.3)  # be gentle: one page at a time
        yield (meta(page, "og:title"), url, meta(page, "og:description"), meta(page, "article:published_time"), "뉴닉", {})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=24, help="keep items published within this many hours")
    parser.add_argument("--date", default=datetime.now(KST).strftime("%Y-%m-%d"))
    args = parser.parse_args()

    now = datetime.now(KST)
    cutoff = now - timedelta(hours=args.hours)
    feeds, items, seen = [], [], set()

    for name, region, url in FEEDS:
        entry = {"name": name, "region": region, "url": url}
        try:
            root = ET.fromstring(fetch(url))
        except Exception as e:  # network or parse failure: record and move on
            entry.update(status="error", error=str(e)[:200], kept=0)
            feeds.append(entry)
            continue
        kept = 0
        source_entries = newneek_entries(root, cutoff) if url == NEWNEEK_SITEMAP else entries(root)
        for title, link, summary, pub, publisher, extra in source_entries:
            title = clean(title)
            published = parse_date(pub)
            if publisher:
                publisher = clean(publisher)
                title = re.sub(rf"\s+-\s+{re.escape(publisher)}$", "", title)
            if not title or published is None or published < cutoff or published > now + timedelta(hours=1):
                continue
            key = re.sub(r"\W+", "", title).lower()
            if key in seen:
                continue
            seen.add(key)
            kept += 1
            items.append({
                "id": 0,
                "source": name,
                "publisher": publisher or name,
                "region": region,
                "title": title,
                # WordPress feeds (e.g. uppity) append "The post … appeared first on …"
                "summary": re.sub(r"\s*The post .*? appeared first on .*$", "", clean(summary))[:300],
                "link": (link or "").strip(),
                "published": published.isoformat(timespec="minutes"),
                **extra,
            })
        entry.update(status="ok", kept=kept)
        feeds.append(entry)

    items.sort(key=lambda x: x["published"], reverse=True)
    for i, item in enumerate(items, 1):
        item["id"] = i

    out_dir = ROOT / "data" / args.date
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "news.json").write_text(json.dumps({
        "generated_at": now.isoformat(timespec="seconds"),
        "window": {"from": cutoff.isoformat(timespec="minutes"), "to": now.isoformat(timespec="minutes")},
        "feeds": feeds,
        "items": items,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"{x['id']}\t{x['region']}\t{x['published'][5:16].replace('T', ' ')}\t{x['publisher']}\t{x['title']}"
             + (f"\t[검색량 {x['traffic']}]" if "traffic" in x else "") for x in items]
    (out_dir / "titles.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok = sum(f["status"] == "ok" for f in feeds)
    by_region = {r: sum(x["region"] == r for x in items) for r in ("domestic", "global", "trend", "explainer")}
    print(f"data/{args.date}/news.json: {len(items)} items {by_region} from {ok}/{len(feeds)} feeds")
    for f in feeds:
        if f["status"] != "ok":
            print(f"  failed: {f['name']}: {f['error']}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
