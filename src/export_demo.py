"""Render the synthetic demo dataset to demo/demo.html and demo/demo.pdf."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

from pdf import html_to_pdf
from render import render_html

DEMO = os.path.join(BASE, "demo")
ASSETS = os.path.join(BASE, "assets")

ACCOUNT = {
    "self_wxid": "wxid_demo_self",
    "self_display": "我",
    "target_wxid": "wxid_demo_other",
    "target_alias": "demo_contact",
    "target_remark": "Demo Contact",
    "target_display": "Demo Contact",
}


def main():
    raw = json.load(open(os.path.join(DEMO, "export_items.json"), encoding="utf-8"))
    raw.sort(key=lambda m: m["ts"])
    msgs = []
    for m in raw:
        dt = datetime.fromtimestamp(m["ts"])
        item = {
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M"),
            "sender": m["sender"],
            "name": ACCOUNT["target_display"] if m["sender"] == "other"
                    else ACCOUNT["self_display"],
            "type": m["type"],
            "text": m.get("text", ""),
            "extra": m.get("extra", ""),
            "duration": m.get("duration", 0),
            "transcript": "",
            "image_path": "",
        }
        if m.get("sticker_name"):
            item["text"] = "[表情] " + m["sticker_name"]
            item["type"] = "text"
        if m.get("image_path"):
            item["image_path"] = os.path.join(DEMO, m["image_path"])
        if m["type"] == "file":
            item["text"] = m.get("text", "")
        msgs.append(item)

    stats = {
        "first_time": f"{msgs[0]['date']} {msgs[0]['time']}",
        "last_time": f"{msgs[-1]['date']} {msgs[-1]['time']}",
        "total": len(msgs),
        "text": sum(1 for m in msgs if m["type"] == "text"),
        "image": sum(1 for m in msgs if m["type"] == "image"),
        "voice": sum(1 for m in msgs if m["type"] == "voice"),
        "video": sum(1 for m in msgs if m["type"] == "video"),
    }
    html = os.path.join(DEMO, "demo.html")
    render_html(msgs, ACCOUNT, stats, html, ASSETS,
                "聊天记录导出示例（合成数据）",
                "Synthetic demo — no real chat data", template="chat.html.j2")
    pdf = os.path.join(DEMO, "demo.pdf")
    html_to_pdf(html, pdf)
    print("HTML", html)
    print("PDF", pdf, os.path.getsize(pdf))
    return 0


if __name__ == "__main__":
    sys.exit(main())
