#!/usr/bin/env python3
"""Collect recent economy headlines from RSS feeds into data/<date>/news.json.

Standard library only. Usage: python3 scripts/fetch_news.py [--hours 30] [--date YYYY-MM-DD]
"""
import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "news-briefing-script/1.0 (+https://github.com/alephnull-hub/news)"

FEEDS = [
    # (name, region, url)
    ("연합뉴스 경제", "domestic", "https://www.yna.co.kr/rss/economy.xml"),
    ("연합뉴스 마켓", "domestic", "https://www.yna.co.kr/rss/market.xml"),
    ("연합뉴스 국제", "global", "https://www.yna.co.kr/rss/international.xml"),
    ("한국경제 경제", "domestic", "https://www.hankyung.com/feed/economy"),
    ("한국경제 증권", "domestic", "https://www.hankyung.com/feed/finance"),
    ("한국경제 국제", "global", "https://www.hankyung.com/feed/international"),
    ("매일경제 경제", "domestic", "https://www.mk.co.kr/rss/30100041/"),
    ("매일경제 증권", "domestic", "https://www.mk.co.kr/rss/50200011/"),
    ("MarketWatch Top Stories", "global", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("BBC Business", "global", "https://feeds.bbci.co.uk/news/business/rss.xml"),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def clean(text):
    text = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def parse_date(value):
    # Some feeds (e.g. mk.co.kr) write the offset as "+09:00", which email.utils reads as UTC.
    value = re.sub(r"([+-]\d{2}):(\d{2})\s*$", r"\1\2", (value or "").strip())
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=30, help="keep items published within this many hours")
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
        for item in root.iter("item"):
            title = clean(item.findtext("title"))
            published = parse_date(item.findtext("pubDate"))
            if not title or published is None or published < cutoff or title in seen:
                continue
            seen.add(title)
            kept += 1
            items.append({
                "source": name,
                "region": region,
                "title": title,
                "summary": clean(item.findtext("description"))[:300],
                "link": (item.findtext("link") or "").strip(),
                "published": published.isoformat(timespec="minutes"),
            })
        entry.update(status="ok", kept=kept)
        feeds.append(entry)

    items.sort(key=lambda x: x["published"], reverse=True)
    out_dir = ROOT / "data" / args.date
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "news.json"
    out.write_text(json.dumps({
        "generated_at": now.isoformat(timespec="seconds"),
        "window_hours": args.hours,
        "feeds": feeds,
        "items": items,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = sum(f["status"] == "ok" for f in feeds)
    print(f"{out.relative_to(ROOT)}: {len(items)} items from {ok}/{len(feeds)} feeds")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
