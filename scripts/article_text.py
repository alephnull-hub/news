#!/usr/bin/env python3
"""Print the body paragraphs of a news article, for quoting market figures.

Standard library only. Usage: python3 scripts/article_text.py URL [URL ...]
"""
import html
import re
import sys
import urllib.request

USER_AGENT = "news-briefing-script/1.0 (+https://github.com/alephnull-hub/news)"
# Text after these markers is copyright notices, related links and ads.
END_MARKERS = ("저작권자", "무단 전재", "무단전재", "ⓒ", "©")


def paragraphs(page):
    page = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    # Articles put body text either in <p> tags or as <br>-separated text in one container.
    chunks = re.split(r"<br\s*/?>|</p>|</div>", page, flags=re.I)
    out = []
    for chunk in chunks:
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", chunk))).strip()
        if any(m in text for m in END_MARKERS):
            if out:
                break
            continue
        if len(text) >= 40 and text not in out:
            out.append(text)
    return out


def main(urls):
    if not urls:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    status = 0
    for url in urls:
        print(f"===== {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                page = resp.read().decode(charset, errors="replace")
        except Exception as e:
            print(f"ERROR: {e}")
            status = 1
            continue
        print("\n".join(paragraphs(page)) or "(본문을 찾지 못함)")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
