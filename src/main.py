"""End-to-end export: decrypted DBs -> target chat -> images -> HTML/PDF."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

from media import Media
from messages import load_messages
from pdf import html_to_pdf
from render import render_html

CONFIG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))
OUT = os.path.join(BASE, CONFIG["paths"]["output"])
DEC = os.path.join(OUT, "decrypted")


def normalize(msgs, media, account, include_system):
    items = []
    seen = set()
    for m in msgs:
        sid = m.get("server_id")
        key = sid if sid else (m["ts"], m["sender"], m["type"], m["text"], m["md5"])
        if key in seen:
            continue
        seen.add(key)
        ts = m["ts"]
        if not ts:
            continue
        dt = datetime.fromtimestamp(ts)
        t = m["type"]
        text = m.get("text", "")
        extra = m.get("extra", "")
        item = {
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M"),
            "sender": m["sender"],
            "name": account["target_display"] if m["sender"] == "other"
                    else account["self_display"],
            "type": "text",
            "text": text,
            "image_path": "",
        }
        if t == "text":
            pass
        elif t == "image":
            item["type"] = "image"
            item["image_path"] = media.export_image(m.get("md5", "")) or ""
        elif t == "voice":
            item["type"] = "voice"
            item["duration"] = m.get("duration", 0)
            item["transcript"] = ""
        elif t == "video":
            item["type"] = "video"
            dur = m.get("duration", 0)
            if not dur:
                vd = media.video_duration(m.get("md5", ""))
                dur = round(vd) if vd else 0
            item["duration"] = dur
        elif t == "file":
            item["type"] = "file"
            item["text"] = text or "文件"
        elif t == "sticker":
            img = media.export_image(m.get("md5", ""))
            if img:
                item["type"] = "image"
                item["image_path"] = img
            else:
                item["type"] = "text"
                item["text"] = "[表情]"
        elif t in ("link", "app", "miniprogram", "forward", "quote"):
            item["type"] = "link"
            item["text"] = text or "[应用消息]"
            item["extra"] = extra
        elif t in ("transfer", "redpacket"):
            item["type"] = "text"
            item["text"] = text
        elif t in ("call", "location_share", "system"):
            if not include_system:
                continue
            item["type"] = "system"
            item["text"] = ("[通话] " if t == "call" else "") + (text or "系统消息")
        elif t == "location":
            item["type"] = "text"
            item["text"] = "[位置] " + (text or "")
        elif t == "card":
            item["type"] = "text"
            item["text"] = "[名片] " + (text or "")
        else:
            if not text:
                continue
            item["type"] = "text"
            item["text"] = text
        items.append(item)
    items.sort(key=lambda x: (x["date"], x["time"]))
    return items


def main():
    account = CONFIG["account"]
    target_wxid = account["target_wxid"]
    include_system = CONFIG["export"].get("include_system_messages", False)
    media = Media(CONFIG["paths"]["target_attach"], CONFIG["paths"]["video_root"],
                  CONFIG["crypto"]["image_code"], account["self_wxid"],
                  os.path.join(OUT, "images"), max_px=760)

    all_msgs = []
    for db in ("message_message_0.db", "message_message_1.db"):
        path = os.path.join(DEC, db)
        if not os.path.exists(path):
            print("missing decrypted", path)
            continue
        msgs, stats = load_messages(path, target_wxid, account["self_wxid"])
        print(db, stats)
        all_msgs.extend(msgs)

    items = normalize(all_msgs, media, account, include_system)
    if not items:
        print("no messages")
        return 1
    stats = {
        "first_time": f"{items[0]['date']} {items[0]['time']}",
        "last_time": f"{items[-1]['date']} {items[-1]['time']}",
        "total": len(items),
        "text": sum(1 for m in items if m["type"] == "text"),
        "image": sum(1 for m in items if m["type"] == "image"),
        "voice": sum(1 for m in items if m["type"] == "voice"),
        "video": sum(1 for m in items if m["type"] == "video"),
    }
    print("stats", stats)
    assets = os.path.join(BASE, "assets")
    title = CONFIG["export"]["title"]
    subtitle = CONFIG["export"]["subtitle"]
    html_path = os.path.join(OUT, "chat.html")
    render_html(items, account, stats, html_path, assets, title, subtitle)
    print("HTML", html_path, os.path.getsize(html_path))

    from pypdf import PdfWriter

    parts_dir = os.path.join(OUT, "parts")
    os.makedirs(parts_dir, exist_ok=True)
    months = sorted({m["date"][:7] for m in items})
    parts = []
    for ym in months:
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
        render_html(sub, account, s, h, assets, f"{title} · {ym}", subtitle)
        html_to_pdf(h, p)
        parts.append(p)
        print("part", ym, len(sub), os.path.getsize(p), flush=True)

    pdf_path = os.path.join(OUT, "chat.pdf")
    writer = PdfWriter()
    for p in parts:
        writer.append(p)
    with open(pdf_path, "wb") as f:
        writer.write(f)
    print("PDF ", pdf_path, os.path.getsize(pdf_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
