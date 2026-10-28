#!/usr/bin/env python3
"""Collect official market indicators into data/<date>/market.json.

Sources need free API keys in environment variables; a source without its key is skipped,
not guessed:
  ECOS_API_KEY  Bank of Korea ECOS  https://ecos.bok.or.kr/api/
  FRED_API_KEY  St. Louis Fed FRED  https://fred.stlouisfed.org/docs/api/api_key.html

Standard library only. Usage: python3 scripts/fetch_market.py [--date YYYY-MM-DD]
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "news-briefing-script/1.0 (+https://github.com/alephnull-hub/news)"
LOOKBACK_DAYS = 14

# (label, stat_code, item_code, unit)
ECOS_SERIES = [
    ("KOSPI", "802Y001", "0001000", "pt"),
    ("KOSDAQ", "802Y001", "0089000", "pt"),
    ("외국인 순매수(유가증권)", "802Y001", "0030000", "억원"),
    ("원/달러 환율(매매기준율)", "731Y001", "0000001", "원"),
    ("국고채 10년", "817Y002", "010210000", "%"),
]

# (label, series_id, unit)
FRED_SERIES = [
    ("S&P 500", "SP500", "pt"),
    ("나스닥 종합", "NASDAQCOM", "pt"),
    ("다우존스", "DJIA", "pt"),
    ("VIX", "VIXCLS", "pt"),
    ("미 국채 10년", "DGS10", "%"),
    ("WTI 유가", "DCOILWTICO", "$/bbl"),
]


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def summarize(label, unit, source, observations):
    """observations: list of (YYYY-MM-DD, float), oldest first."""
    if not observations:
        return {"label": label, "source": source, "status": "no_data"}
    date, value = observations[-1]
    row = {"label": label, "source": source, "status": "ok", "unit": unit, "date": date, "value": value}
    # Net flows (억원) are a daily amount, so a day-over-day change means nothing; rates (%) change in %p only.
    if len(observations) > 1 and unit != "억원":
        prev_date, prev = observations[-2]
        row.update(prev_date=prev_date, change=round(value - prev, 4))
        if prev and unit != "%":
            row["change_pct"] = round((value - prev) / prev * 100, 2)
    return row


def fetch_ecos(key, start, end):
    rows = []
    for label, stat, item, unit in ECOS_SERIES:
        url = (f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/100/"
               f"{stat}/D/{start:%Y%m%d}/{end:%Y%m%d}/{item}")
        try:
            resp = get_json(url)
            if "StatisticSearch" not in resp:  # ECOS reports errors as {"RESULT": {...}} with HTTP 200
                result = resp.get("RESULT", {})
                rows.append({"label": label, "source": "ECOS", "status": "error",
                             "error": f"{result.get('CODE')}: {result.get('MESSAGE', '')[:150]}"})
                continue
            obs = [(f"{r['TIME'][:4]}-{r['TIME'][4:6]}-{r['TIME'][6:]}", float(r["DATA_VALUE"]))
                   for r in resp["StatisticSearch"].get("row", []) if r.get("DATA_VALUE")]
            rows.append(summarize(label, unit, "ECOS", obs))
        except Exception as e:
            rows.append({"label": label, "source": "ECOS", "status": "error", "error": str(e)[:200]})
    return rows


def fetch_fred(key, start, end):
    rows = []
    for label, series, unit in FRED_SERIES:
        query = urllib.parse.urlencode({
            "series_id": series, "api_key": key, "file_type": "json",
            "observation_start": f"{start:%Y-%m-%d}", "observation_end": f"{end:%Y-%m-%d}",
        })
        try:
            data = get_json(f"https://api.stlouisfed.org/fred/series/observations?{query}")
            obs = [(o["date"], float(o["value"])) for o in data.get("observations", []) if o["value"] != "."]
            rows.append(summarize(label, unit, "FRED", obs))
        except Exception as e:
            rows.append({"label": label, "source": "FRED", "status": "error", "error": str(e)[:200]})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now(KST).strftime("%Y-%m-%d"))
    args = parser.parse_args()

    end = datetime.now(KST)
    start = end - timedelta(days=LOOKBACK_DAYS)
    sources = {}
    for name, env, fetcher in (("ECOS", "ECOS_API_KEY", fetch_ecos), ("FRED", "FRED_API_KEY", fetch_fred)):
        key = os.environ.get(env)
        if key:
            sources[name] = {"status": "ok", "series": fetcher(key, start, end)}
        else:
            sources[name] = {"status": "skipped", "reason": f"{env} not set"}

    out_dir = ROOT / "data" / args.date
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "market.json"
    out.write_text(json.dumps({"generated_at": end.isoformat(timespec="seconds"), "sources": sources},
                              ensure_ascii=False, indent=1), encoding="utf-8")

    for name, src in sources.items():
        if src["status"] == "skipped":
            print(f"{name}: skipped ({src['reason']})")
        else:
            ok = sum(s["status"] == "ok" for s in src["series"])
            print(f"{name}: {ok}/{len(src['series'])} series")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
