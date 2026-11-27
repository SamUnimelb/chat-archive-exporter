"""Parse decrypted WeChat 4.2 message databases into a normalized model."""
from __future__ import annotations

import hashlib
import html as html_mod
import re
import sqlite3

import zstandard as zstd

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
HEX32 = re.compile(rb"[0-9a-fA-F]{32}")
APP_KIND = {
    4: "link", 5: "link", 6: "file", 8: "sticker", 17: "location_share",
    19: "forward", 33: "app", 36: "miniprogram", 51: "app", 57: "quote",
    2000: "transfer", 2001: "redpacket",
}


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.text_factory = bytes
    return conn


def tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return [r[0].decode("utf-8", "replace") if isinstance(r[0], bytes) else r[0]
            for r in rows]


def columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info([{table}])").fetchall()
    return [r[1].decode("utf-8", "replace") if isinstance(r[1], bytes) else r[1]
            for r in rows]


def find_msg_table(conn: sqlite3.Connection, wxid: str) -> str | None:
    digest = hashlib.md5(wxid.encode()).hexdigest().lower()
    names = tables(conn)
    for n in names:
        if n.lower().startswith("msg_") and digest in n.lower():
            return n
    return None


def decode_content(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    raw = bytes(value)
    if raw[:4] == ZSTD_MAGIC:
        try:
            raw = zstd.ZstdDecompressor().decompress(raw)
        except Exception:
            pass
    return raw.decode("utf-8", "replace")


def xml_attr(xml: str, name: str) -> str:
    m = re.search(rf'{re.escape(name)}\s*=\s*"([^"]*)"', xml)
    return m.group(1) if m else ""


def xml_field(xml: str, tag: str) -> str:
    m = re.search(rf"<{tag}>(?:<!\[CDATA\[(.*?)\]\]>|(.*?))</{tag}>", xml, re.S)
    if not m:
        return ""
    return (m.group(1) or m.group(2) or "").strip()


def cdata_text(xml: str) -> str:
    m = re.search(r"<!\[CDATA\[(.*?)\]\]>", xml, re.S)
    return m.group(1).strip() if m else ""


def clean_xml_text(s: str) -> str:
    s = html_mod.unescape(s or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = html_mod.unescape(s)
    s = " ".join(s.split())
    if re.fullmatch(r"[A-Za-z0-9+/=_-]{80,}", s):
        return ""
    if len(s) > 500:
        s = s[:500] + "…"
    return s


def packed_md5(packed) -> str:
    if not packed:
        return ""
    if isinstance(packed, str):
        packed = packed.encode("utf-8", "replace")
    m = HEX32.search(bytes(packed))
    return m.group().decode().lower() if m else ""


def split_type(local_type: int) -> tuple[int, int]:
    base = int(local_type) & 0xFFFFFFFF
    sub = int(local_type) >> 32 if base == 49 else 0
    return base, sub


def load_messages(db_path: str, wxid: str, self_wxid: str):
    conn = connect(db_path)
    table = find_msg_table(conn, wxid)
    if not table:
        conn.close()
        return [], {"error": "table not found"}
    cols = columns(conn, table)
    senders = {}
    if "Name2Id" in tables(conn):
        for rid, name in conn.execute("SELECT rowid, user_name FROM Name2Id"):
            if isinstance(name, bytes):
                name = name.decode("utf-8", "replace")
            senders[int(rid)] = name
    wanted = [c for c in ("local_id", "server_id", "local_type", "create_time",
                          "message_content", "compress_content", "real_sender_id",
                          "packed_info_data") if c in cols]
    rows = conn.execute(
        f"SELECT {', '.join('['+c+']' for c in wanted)} FROM [{table}]").fetchall()
    conn.close()

    out = []
    for row in rows:
        d = dict(zip(wanted, row))
        raw = d.get("message_content")
        if not raw:
            raw = d.get("compress_content") or b""
        if isinstance(raw, str):
            raw = raw.encode("utf-8", "replace")
        raw = bytes(raw)
        text = decode_content(raw)
        base, sub = split_type(d.get("local_type") or 0)
        packed = d.get("packed_info_data") or b""
        sid = d.get("real_sender_id")
        who = "self" if senders.get(sid) == self_wxid else "other"
        ts = int(d.get("create_time") or 0)
        md5 = packed_md5(packed)
        item = {"ts": ts, "sender": who, "type": "other", "text": "",
                "md5": "", "duration": 0, "extra": "", "server_id": d.get("server_id")}

        if base == 1:
            item["type"] = "text"
            item["text"] = text
        elif base == 3:
            item["type"] = "image"
            item["md5"] = md5 or xml_attr(text, "md5")
        elif base == 34:
            item["type"] = "voice"
            ms = 0
            m = re.search(r'voicelength\s*=\s*"(\d+)"', text)
            if m:
                ms = int(m.group(1))
            item["duration"] = round(ms / 1000) if ms else 0
        elif base == 43:
            item["type"] = "video"
            item["md5"] = md5
            m = re.search(r'playlength\s*=\s*"(\d+)"', text)
            if m:
                item["duration"] = int(m.group(1))
        elif base == 47:
            item["type"] = "sticker"
            item["md5"] = xml_attr(text, "md5")
        elif base == 49:
            kind = APP_KIND.get(sub, "app")
            item["type"] = kind
            title = clean_xml_text(xml_field(text, "title"))
            des = clean_xml_text(xml_field(text, "des"))
            if kind == "file":
                item["text"] = title or "文件"
                m = re.search(r"<totallen>(\d+)</totallen>", text)
                item["file_size"] = int(m.group(1)) if m else 0
            elif kind == "quote":
                refer_raw = html_mod.unescape(xml_field(text, "content") or "")
                refer_title = xml_field(refer_raw, "title")
                refer = clean_xml_text(refer_title or refer_raw)
                item["text"] = title
                item["extra"] = refer
                if not item["text"] and refer:
                    item["text"] = refer
                    item["extra"] = ""
            elif kind == "forward":
                item["text"] = title or "聊天记录"
                item["extra"] = des
            elif kind == "transfer":
                item["text"] = des or title or "转账"
            elif kind == "redpacket":
                item["text"] = des or title or "红包"
            elif kind == "sticker":
                item["md5"] = xml_attr(text, "md5") or md5
            elif kind == "location_share":
                item["text"] = title or "位置共享"
            else:
                item["text"] = title or des
                item["extra"] = des if des and des != title else ""
        elif base == 50:
            item["type"] = "call"
            item["text"] = cdata_text(text) or "通话"
        elif base == 10000:
            item["type"] = "system"
            item["text"] = text
        elif base == 11000:
            item["type"] = "system"
            item["text"] = text
        elif base == 48:
            item["type"] = "location"
            item["text"] = xml_attr(text, "poiname") or xml_attr(text, "label")
        elif base == 42:
            item["type"] = "card"
            item["text"] = xml_attr(text, "nickname") or xml_attr(text, "username")
        elif base == 10002:
            item["type"] = "system"
            item["text"] = text
        else:
            item["type"] = "other"
            item["text"] = text or xml_field(text, "title") or xml_field(text, "des")
        if item["type"] in ("other", "system") and not item["text"]:
            continue
        out.append(item)

    out.sort(key=lambda m: (m["ts"], m.get("server_id") or 0))
    stats = {"table": table, "count": len(out), "senders": senders}
    return out, stats
