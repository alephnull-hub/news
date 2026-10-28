#!/usr/bin/env python3
"""Count how many collected headlines cover a story, for ranking issues by coverage.

Each pattern is a regular expression matched against titles in data/<date>/titles.txt;
a headline counts once even if several patterns match it.
Usage: python3 scripts/count_titles.py [--date YYYY-MM-DD] [--region domestic|global|trend|explainer] [--show 5] PATTERN [PATTERN ...]
Example: python3 scripts/count_titles.py --region domestic "하이닉스" "SK하닉"
"""
import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now(KST).strftime("%Y-%m-%d"))
    parser.add_argument("--region", choices=["domestic", "global", "trend", "explainer"])
    parser.add_argument("--show", type=int, default=5, help="print this many matching headlines")
    parser.add_argument("patterns", nargs="+")
    args = parser.parse_args()

    path = ROOT / "data" / args.date / "titles.txt"
    if not path.exists():
        print(f"{path.relative_to(ROOT)} not found; run scripts/fetch_news.py first", file=sys.stderr)
        return 1
    regexes = [re.compile(p, re.I) for p in args.patterns]
    hits = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) < 5 or (args.region and parts[1] != args.region):
            continue
        if any(r.search(parts[4]) for r in regexes):
            hits.append(parts)
    print(f"{len(hits)}건")
    for p in hits[:args.show]:
        print(f"  #{p[0]} {p[2]} {p[3]} | {p[4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
