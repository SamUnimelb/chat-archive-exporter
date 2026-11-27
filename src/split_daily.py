"""Split the monthly chat PDFs into one PDF per day.

Re-renders each day from export_items.json with the same templates used by
main.py / export_compact.py, so day boundaries are exact (no page overlap).
Images are resolved from output/images/YYYY-MM/.
"""
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

import main as M
from pdf import html_to_pdf
from render import render_html

OUT = os.path.join(BASE, "output")
ACCOUNT = M.CONFIG["account"]
ASSETS = os.path.join(BASE, "assets")

KINDS = [
    ("chat.html.j2", "parts", ""),
    ("compact2.html.j2", "parts_compact", "（精简版）"),
]


class ImageProxy:
    """Resolve images from the month folders without re-exporting .dat files."""

    def __init__(self, month_map):
        self.month_map = month_map

    def export_image(self, md5):
        ym = self.month_map.get(md5)
        if not ym:
            return ""
        p = os.path.join(OUT, "images", ym, md5 + ".jpg")
        return p if os.path.exists(p) else ""

    def video_duration(self, md5):
        return 0


def build_month_map(raw):
    month_map = {}
    for m in raw:
        md5 = m.get("md5")
        if not md5 or not m.get("image_path"):
            continue
        ym = datetime.fromtimestamp(m["ts"]).strftime("%Y-%m")
        if md5 not in month_map or ym < month_map[md5]:
            month_map[md5] = ym
    return month_map


def stats_for(sub):
    return {
        "first_time": sub[0]["date"] + " " + sub[0]["time"],
        "last_time": sub[-1]["date"] + " " + sub[-1]["time"],
        "total": len(sub),
        "text": sum(1 for m in sub if m["type"] == "text"),
        "image": sum(1 for m in sub if m["type"] == "image"),
        "voice": sum(1 for m in sub if m["type"] == "voice"),
        "video": sum(1 for m in sub if m["type"] == "video"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="only this YYYY-MM-DD (pilot run)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--missing", action="store_true",
                    help="只补齐还没有 PDF 的日子（断点续跑）")
    args = ap.parse_args()

    raw = json.load(open(os.path.join(OUT, "export_items.json"), encoding="utf-8"))
    items = M.normalize(raw, ImageProxy(build_month_map(raw)), ACCOUNT, False)
    by_day = {}
    for m in items:
        by_day.setdefault(m["date"], []).append(m)

    jobs = []
    tmp_root = os.path.join(OUT, "_daily_tmp")
    os.makedirs(tmp_root, exist_ok=True)
    for template, folder, suffix in KINDS:
        tmp_dir = os.path.join(tmp_root, folder)
        os.makedirs(tmp_dir, exist_ok=True)
        for date, sub in sorted(by_day.items()):
            if args.date and date != args.date:
                continue
            dest = os.path.join(OUT, folder, date[:7], date + ".pdf")
            if args.missing and os.path.exists(dest):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            h = os.path.join(tmp_dir, date + ".html")
            render_html(
                sub, ACCOUNT, stats_for(sub), h, ASSETS,
                M.CONFIG["export"]["title"] + " · " + date + suffix,
                M.CONFIG["export"]["subtitle"], template=template,
            )
            jobs.append((h, dest))

    print("render jobs", len(jobs), flush=True)
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(html_to_pdf, h, d): d for h, d in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            dest = futures[fut]
            try:
                fut.result()
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                print("FAIL", dest, exc, flush=True)
            if i % 50 == 0:
                print("printed", i, "/", len(jobs), flush=True)

    shutil.rmtree(tmp_root, ignore_errors=True)
    print("done ok", ok, "fail", fail, flush=True)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
