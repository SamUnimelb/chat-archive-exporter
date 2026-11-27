"""Generate the compact chat PDF with narrow bubbles (~20 messages/page)."""
from __future__ import annotations

import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

import main as M
from media import Media
from pdf import html_to_pdf
from render import render_html
from pypdf import PdfWriter

OUT = os.path.join(BASE, "output")
CONFIG = M.CONFIG
ACCOUNT = CONFIG["account"]


def main():
    raw = json.load(open(os.path.join(OUT, "export_items.json"), encoding="utf-8"))
    media = Media(CONFIG["paths"]["target_attach"], CONFIG["paths"]["video_root"],
                  CONFIG["crypto"]["image_code"], ACCOUNT["self_wxid"],
                  os.path.join(OUT, "images_compact"), max_px=340)
    items = M.normalize(raw, media, ACCOUNT, False)
    print("items", len(items), flush=True)
    stats = {
        "first_time": f"{items[0]['date']} {items[0]['time']}",
        "last_time": f"{items[-1]['date']} {items[-1]['time']}",
        "total": len(items),
        "text": sum(1 for m in items if m["type"] == "text"),
        "image": sum(1 for m in items if m["type"] == "image"),
        "voice": sum(1 for m in items if m["type"] == "voice"),
        "video": sum(1 for m in items if m["type"] == "video"),
    }
    html = os.path.join(OUT, "chat_compact.html")
    render_html(items, ACCOUNT, stats, html, os.path.join(BASE, "assets"),
                f"{CONFIG['export']['title']}（精简版）",
                CONFIG["export"]["subtitle"], template="compact2.html.j2")
    print("HTML", html, os.path.getsize(html), flush=True)

    parts_dir = os.path.join(OUT, "parts_compact")
    os.makedirs(parts_dir, exist_ok=True)
    parts = []
    for ym in sorted({m["date"][:7] for m in items}):
        sub = [m for m in items if m["date"].startswith(ym)]
        if not sub:
            continue
        s = {
            "first_time": f"{sub[0]['date']} {sub[0]['time']}",
            "last_time": f"{sub[-1]['date']} {sub[-1]['time']}",
            "total": len(sub),
            "text": sum(1 for m in sub if m["type"] == "text"),
            "image": sum(1 for m in sub if m["type"] == "image"),
            "voice": sum(1 for m in sub if m["type"] == "voice"),
            "video": sum(1 for m in sub if m["type"] == "video"),
        }
        h = os.path.join(parts_dir, f"chat_{ym}.html")
        p = os.path.join(parts_dir, f"chat_{ym}.pdf")
        render_html(sub, ACCOUNT, s, h, os.path.join(BASE, "assets"),
                    f"{CONFIG['export']['title']} · {ym}（精简版）",
                    CONFIG["export"]["subtitle"], template="compact2.html.j2")
        html_to_pdf(h, p)
        parts.append(p)
        print("part", ym, len(sub), os.path.getsize(p), flush=True)

    writer = PdfWriter()
    for p in parts:
        writer.append(p)
    final = os.path.join(OUT, "chat_compact.pdf")
    with open(final, "wb") as f:
        writer.write(f)
    print("merged", len(parts), os.path.getsize(final), flush=True)


if __name__ == "__main__":
    main()
