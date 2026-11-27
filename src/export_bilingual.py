"""Redacted + Chinese-English bilingual text PDF."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

from export_text import hs, line_for
from pdf import html_to_pdf
from redact import redact
from render import render_html

OUT = os.path.join(BASE, "output")
CONFIG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))
ACCOUNT = CONFIG["account"]
CACHE_PATH = os.path.join(OUT, "translations_zh_en.json")
CJK = re.compile(r"[\u4e00-\u9fff]")

try:
    from argostranslate import translate as argos
    LANGS = {l.code for l in argos.get_installed_languages()}
    HAS_MODEL = "zh" in LANGS and "en" in LANGS
except Exception as e:
    print("argos unavailable", e)
    argos = None
    HAS_MODEL = False


def translate(text):
    if not text or not CJK.search(text) or not HAS_MODEL:
        return text
    try:
        return argos.translate(text, "zh", "en")
    except Exception:
        return text


def english_for(m, tr):
    t = m.get("type", "other")
    text = (m.get("text") or "").strip()
    extra = (m.get("extra") or "").strip()
    if t == "text":
        return tr(redact(text))
    if t == "image":
        p = m.get("image_path") or ""
        name = os.path.basename(p) if p else (m.get("md5", "") + ".dat")
        info = ", ".join(x for x in (m.get("image_dims", ""),
                                     hs(m.get("image_size", 0))) if x)
        return f"[Image] {name}" + (f" ({info})" if info else "")
    if t == "voice":
        return f"[Voice] {m.get('duration', 0)}s (audio not cached)"
    if t == "video":
        p = m.get("video_path") or ""
        name = os.path.basename(p) if p else (m.get("md5", "") + ".mp4")
        sz = hs(m.get("video_size", 0))
        return f"[Video] {name} ({m.get('duration', 0)}s" + (f", {sz})" if sz else ", file not cached)")
    if t == "file":
        sz = hs(m.get("file_size", 0))
        return f"[File] {text}" + (f" ({sz})" if sz else "")
    if t == "sticker":
        name = m.get("sticker_name", "")
        return f"[Sticker] {name}" if name else "[Sticker]"
    if t in ("link", "app", "miniprogram", "forward", "quote",
             "transfer", "redpacket", "location_share"):
        label = {"link": "Link", "app": "App", "miniprogram": "Mini Program",
                 "forward": "Forward", "quote": "Quote", "transfer": "Transfer",
                 "redpacket": "Red Packet", "location_share": "Location Share"}[t]
        s = f"[{label}] {tr(redact(text))}"
        if extra:
            s += f" ({tr(redact(extra))})"
        return s
    if t == "location":
        return f"[Location] {tr(redact(text))}"
    if t == "card":
        return f"[Contact Card] {tr(redact(text))}"
    return ""


def main():
    raw = json.load(open(os.path.join(OUT, "export_items.json"), encoding="utf-8"))
    raw.sort(key=lambda m: (m["ts"], m.get("server_id") or 0))
    cache = {}
    if os.path.exists(CACHE_PATH):
        cache = json.load(open(CACHE_PATH, encoding="utf-8"))

    sources = set()
    for m in raw:
        if m["type"] in ("text", "link", "app", "miniprogram", "forward",
                         "quote", "transfer", "redpacket", "location_share",
                         "location", "card"):
            s = redact(m.get("text") or "")
            if CJK.search(s):
                sources.add(s)
            e = redact(m.get("extra") or "")
            if CJK.search(e):
                sources.add(e)
    todo = [s for s in sources if s not in cache]
    print("sources", len(sources), "todo", len(todo), "model", HAS_MODEL, flush=True)
    for i, s in enumerate(todo, 1):
        cache[s] = translate(s)
        if i % 200 == 0:
            print("translated", i, "/", len(todo), flush=True)
            json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"),
                      ensure_ascii=False)
    json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"), ensure_ascii=False)

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
    stats = {
        "first_time": f"{lines[0]['date']} {lines[0]['time']}",
        "last_time": f"{lines[-1]['date']} {lines[-1]['time']}",
        "total": len(lines),
        "text": sum(1 for x in raw if x["type"] == "text"),
        "image": sum(1 for x in raw if x["type"] == "image"),
        "voice": sum(1 for x in raw if x["type"] == "voice"),
        "video": sum(1 for x in raw if x["type"] == "video"),
    }
    html = os.path.join(OUT, "chat_text_redacted_bilingual.html")
    render_html(lines, ACCOUNT, stats, html, os.path.join(BASE, "assets"),
                f"{CONFIG['export']['title']}（打码 · 中英对照）",
                CONFIG["export"]["subtitle"], template="bilingual.html.j2")
    pdf = os.path.join(OUT, "chat_text_redacted_bilingual.pdf")
    html_to_pdf(html, pdf)
    txt = os.path.join(OUT, "chat_text_redacted_bilingual.txt")
    with open(txt, "w", encoding="utf-8") as f:
        last = None
        for x in lines:
            if x["date"] != last:
                f.write(f"\n===== {x['date']} =====\n")
                last = x["date"]
            f.write(f"{x['time']}  {x['name']}：{x['original']}\n")
            if x["translation"]:
                f.write(f"    {x['translation']}\n")
    print("lines", len(lines))
    print("PDF", pdf, os.path.getsize(pdf))
    print("TXT", txt, os.path.getsize(txt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
