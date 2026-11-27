"""Build an enriched, reusable export dataset from decrypted WeChat DBs."""
from __future__ import annotations

import glob
import json
import os
import sqlite3
import sys

from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

import main as M
from media import mp4_duration
from messages import load_messages

OUT = os.path.join(BASE, "output")
DEC = os.path.join(OUT, "decrypted")
CONFIG = M.CONFIG
ACCOUNT = CONFIG["account"]
ATTACH = CONFIG["paths"]["target_attach"]
VIDEO = CONFIG["paths"]["video_root"]


def _s(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return v or ""


def sticker_captions():
    p = os.path.join(DEC, "emoticon_emoticon.db")
    caps = {}
    if not os.path.exists(p):
        return caps
    conn = sqlite3.connect(p)
    conn.text_factory = bytes
    for md5, caption in conn.execute(
            "SELECT md5_, caption_ FROM kStoreEmoticonCaptionsTable"):
        md5, caption = _s(md5).lower(), _s(caption)
        if md5 and caption:
            caps.setdefault(md5, caption)
    for md5, caption in conn.execute(
            "SELECT md5, caption FROM kNonStoreEmoticonTable"):
        md5, caption = _s(md5).lower(), _s(caption)
        if md5 and caption:
            caps.setdefault(md5, caption)
    conn.close()
    return caps


def contact_names():
    p = os.path.join(DEC, "contact_contact.db")
    names = set()
    if not os.path.exists(p):
        return []
    conn = sqlite3.connect(p)
    conn.text_factory = bytes
    skip = {"filehelper", "weixin", "qqmail", "fmessage", "medianote",
            "floatbottle", "newsapp", "notifymessage", "weibo", "qqsafe"}
    for row in conn.execute(
            "SELECT username, remark, nick_name, alias FROM contact"):
        username, remark, nick, alias = [_s(x) for x in row]
        if username in (ACCOUNT["self_wxid"], ACCOUNT["target_wxid"]):
            continue
        if username in skip or username.startswith(("wxid_", "gh_")) or "@" in username:
            continue
        for n in (remark, nick, alias):
            n = n.strip()
            if 2 <= len(n) <= 30 and n not in ("微信", "WeChat", "微信团队"):
                names.add(n)
    conn.close()
    return sorted(names, key=len, reverse=True)


def image_info(md5):
    if not md5:
        return "", 0, ""
    p = os.path.join(OUT, "images", f"{md5}.jpg")
    if os.path.exists(p):
        dims = ""
        try:
            with Image.open(p) as im:
                dims = f"{im.width}×{im.height}"
        except Exception:
            pass
        return p, os.path.getsize(p), dims
    hits = glob.glob(os.path.join(ATTACH, "**", "Img", f"{md5}*.dat"),
                     recursive=True)
    if hits:
        p = hits[0]
        return p, os.path.getsize(p), ""
    return "", 0, ""


def video_info(md5):
    if not md5:
        return "", 0
    hits = glob.glob(os.path.join(VIDEO, "**", f"{md5}*.mp4"), recursive=True)
    if hits:
        p = hits[0]
        return p, os.path.getsize(p)
    return "", 0


def main():
    caps = sticker_captions()
    names = contact_names()
    json.dump(names, open(os.path.join(OUT, "contact_names.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=2)
    items = []
    for db in ("message_message_0.db", "message_message_1.db"):
        msgs, stats = load_messages(os.path.join(DEC, db),
                                    ACCOUNT["target_wxid"], ACCOUNT["self_wxid"])
        print(db, stats["count"])
        items.extend(msgs)
    seen = set()
    uniq = []
    for m in items:
        key = m.get("server_id") or (m["ts"], m["sender"], m["type"],
                                     m["text"], m["md5"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(m)
    uniq.sort(key=lambda m: (m["ts"], m.get("server_id") or 0))
    print("unique", len(uniq))

    for m in uniq:
        t = m["type"]
        md5 = m.get("md5", "")
        if t == "image":
            p, size, dims = image_info(md5)
            m["image_path"], m["image_size"], m["image_dims"] = p, size, dims
        elif t == "video":
            p, size = video_info(md5)
            m["video_path"], m["video_size"] = p, size
            if not m.get("duration") and p:
                d = mp4_duration(p)
                m["duration"] = round(d) if d else 0
        elif t == "sticker":
            m["sticker_name"] = caps.get(md5.lower(), "")
        m.pop("raw", None)

    with open(os.path.join(OUT, "export_items.json"), "w", encoding="utf-8") as f:
        json.dump(uniq, f, ensure_ascii=False)
    print("saved", len(uniq), "items; sticker captions", len(caps),
          "contacts", len(names))


if __name__ == "__main__":
    main()
