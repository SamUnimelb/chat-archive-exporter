"""Generate the text-only (copyable) chat PDF/TXT."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

from pdf import html_to_pdf
from render import render_html

OUT = os.path.join(BASE, "output")
CONFIG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))
ACCOUNT = CONFIG["account"]


def hs(n):
    if not n:
        return ""
    n = float(n)
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def line_for(m):
    t = m.get("type", "other")
    text = (m.get("text") or "").strip()
    extra = (m.get("extra") or "").strip()
    if t == "text":
        return text
    if t == "image":
        p = m.get("image_path") or ""
        name = os.path.basename(p) if p else (m.get("md5", "") + ".dat")
        info = "，".join(x for x in (m.get("image_dims", ""),
                                    hs(m.get("image_size", 0))) if x)
        return f"[图片] {name}（{info}）" if info else f"[图片] {name}"
    if t == "voice":
        return f"[语音] {m.get('duration', 0)} 秒（音频未缓存）"
    if t == "video":
        p = m.get("video_path") or ""
        name = os.path.basename(p) if p else (m.get("md5", "") + ".mp4")
        dur = m.get("duration", 0)
        sz = hs(m.get("video_size", 0))
        info = f"{dur} 秒" + (f"，{sz}" if sz else "，文件未缓存")
        return f"[视频] {name}（{info}）"
    if t == "file":
        sz = hs(m.get("file_size", 0))
        return f"[文件] {text}（{sz}）" if sz else f"[文件] {text}"
    if t == "sticker":
        name = m.get("sticker_name", "")
        return f"[表情] {name}" if name else "[表情]"
    if t in ("link", "app", "miniprogram", "forward", "quote",
             "transfer", "redpacket", "location_share"):
        prefix = {"link": "链接", "app": "应用", "miniprogram": "小程序",
                  "forward": "转发", "quote": "引用", "transfer": "转账",
                  "redpacket": "红包", "location_share": "位置"}[t]
        s = f"[{prefix}] {text}"
        if extra:
            s += f"（{extra}）"
        return s
    if t == "location":
        return f"[位置] {text}"
    if t == "card":
        return f"[名片] {text}"
    if t in ("call", "system"):
        return ""
    return text


def main():
    raw = json.load(open(os.path.join(OUT, "export_items.json"), encoding="utf-8"))
    raw.sort(key=lambda m: (m["ts"], m.get("server_id") or 0))
    lines = []
    for m in raw:
        content = line_for(m)
        if not content:
            continue
        dt = datetime.fromtimestamp(m["ts"])
        lines.append({
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M"),
            "sender": m["sender"],
            "name": ACCOUNT["target_display"] if m["sender"] == "other"
                    else ACCOUNT["self_display"],
            "type": m["type"],
            "text": content,
        })
    if not lines:
        print("no lines")
        return 1
    stats = {
        "first_time": f"{lines[0]['date']} {lines[0]['time']}",
        "last_time": f"{lines[-1]['date']} {lines[-1]['time']}",
        "total": len(lines),
        "text": sum(1 for x in raw if x["type"] == "text"),
        "image": sum(1 for x in raw if x["type"] == "image"),
        "voice": sum(1 for x in raw if x["type"] == "voice"),
        "video": sum(1 for x in raw if x["type"] == "video"),
    }
    html = os.path.join(OUT, "chat_text.html")
    render_html(lines, ACCOUNT, stats, html, os.path.join(BASE, "assets"),
                f"{CONFIG['export']['title']}（纯文字版）",
                CONFIG["export"]["subtitle"], template="text.html.j2")
    pdf = os.path.join(OUT, "chat_text.pdf")
    html_to_pdf(html, pdf)
    txt = os.path.join(OUT, "chat_text.txt")
    with open(txt, "w", encoding="utf-8") as f:
        last = None
        for x in lines:
            if x["date"] != last:
                f.write(f"\n===== {x['date']} =====\n")
                last = x["date"]
            f.write(f"{x['time']}  {x['name']}：{x['text']}\n")
    print("lines", len(lines))
    print("HTML", html, os.path.getsize(html))
    print("PDF ", pdf, os.path.getsize(pdf))
    print("TXT ", txt, os.path.getsize(txt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
