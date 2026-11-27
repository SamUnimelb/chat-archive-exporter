"""Bilingual (redacted) chat split by month and by day into output/translations/."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

from export_bilingual import english_for, translate
from export_text import line_for
from pdf import html_to_pdf
from redact import redact
from render import render_html

OUT = os.path.join(BASE, "output")
TR = os.path.join(OUT, "translations")
ASSETS = os.path.join(BASE, "assets")
CONFIG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))
ACCOUNT = CONFIG["account"]
CACHE_PATH = os.path.join(OUT, "translations_zh_en.json")


def build_lines(raw, cache):
    def tr(s):
        k = redact(s or "")
        if k not in cache:
            cache[k] = translate(k)
        return cache[k]

    lines = []
    for m in raw:
        orig = redact(line_for(m))
        if not orig:
            continue
        en = english_for(m, tr)
        dt = datetime.fromtimestamp(m["ts"])
        lines.append({
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M"),
            "sender": m["sender"],
            "name": ACCOUNT["target_display"] if m["sender"] == "other"
                    else ACCOUNT["self_display"],
            "original": orig,
            "translation": en if en and en != orig else "",
        })
    return lines


def stats_for(ls):
    return {
        "first_time": f"{ls[0]['date']} {ls[0]['time']}",
        "last_time": f"{ls[-1]['date']} {ls[-1]['time']}",
        "total": len(ls),
        "text": sum(1 for x in ls if x["original"] and not x["original"].startswith("[")),
        "image": sum(1 for x in ls if x["original"].startswith("[图片]")),
        "voice": sum(1 for x in ls if x["original"].startswith("[语音]")),
        "video": sum(1 for x in ls if x["original"].startswith("[视频]")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="only this YYYY-MM-DD (pilot)")
    ap.add_argument("--month", help="only this YYYY-MM (pilot)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--missing", action="store_true")
    args = ap.parse_args()

    raw = json.load(open(os.path.join(OUT, "export_items.json"), encoding="utf-8"))
    raw.sort(key=lambda m: (m["ts"], m.get("server_id") or 0))
    cache = json.load(open(CACHE_PATH, encoding="utf-8")) if os.path.exists(CACHE_PATH) else {}
    lines = build_lines(raw, cache)
    print("lines", len(lines), flush=True)

    by_month = {}
    by_day = {}
    for x in lines:
        by_month.setdefault(x["date"][:7], []).append(x)
        by_day.setdefault(x["date"], []).append(x)

    jobs = []
    tmp = os.path.join(OUT, "_tr_tmp")
    os.makedirs(tmp, exist_ok=True)
    for ym, ls in sorted(by_month.items()):
        if args.month and ym != args.month:
            continue
        d = os.path.join(TR, ym)
        os.makedirs(d, exist_ok=True)
        h = os.path.join(d, ym + ".html")
        p = os.path.join(d, ym + ".pdf")
        render_html(ls, ACCOUNT, stats_for(ls), h, ASSETS,
                    f"{CONFIG['export']['title']} · {ym}（打码 · 中英对照）",
                    CONFIG["export"]["subtitle"], template="bilingual.html.j2")
        if not (args.missing and os.path.exists(p)):
            jobs.append((h, p))

    for date, ls in sorted(by_day.items()):
        if args.date and date != args.date:
            continue
        ym = date[:7]
        d = os.path.join(TR, ym)
        os.makedirs(d, exist_ok=True)
        h = os.path.join(d, date + ".html")
        p = os.path.join(d, date + ".pdf")
        render_html(ls, ACCOUNT, stats_for(ls), h, ASSETS,
                    f"{CONFIG['export']['title']} · {date}（打码 · 中英对照）",
                    CONFIG["export"]["subtitle"], template="bilingual.html.j2")
        if not (args.missing and os.path.exists(p)):
            jobs.append((h, p))

    print("print jobs", len(jobs), flush=True)
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(html_to_pdf, h, p): p for h, p in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                fut.result()
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                print("FAIL", futures[fut], exc, flush=True)
            if i % 50 == 0:
                print("printed", i, "/", len(jobs), flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print("done ok", ok, "fail", fail, flush=True)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
