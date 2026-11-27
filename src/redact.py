"""Automatic third-party redaction for chat text."""
from __future__ import annotations

import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "output")

URL = re.compile(r"https?://[^\s<>\"）)]+", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WXID = re.compile(r"wxid_[A-Za-z0-9]+")
IDNO = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
BANK = re.compile(r"(?<!\d)\d{16,19}(?!\d)")
PHONE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)")
LAND = re.compile(r"(?<!\d)0\d{2,3}-?\d{7,8}(?!\d)")
AT = re.compile(r"@[^\s@，。；;:：]{2,24}")

_NAMES = None

# Contact nicknames that collide with ordinary words read badly after masking.
_STOP = {
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "a little", "the one", "one day", "thank you", "good morning", "good night",
}


def _names():
    global _NAMES
    if _NAMES is not None:
        return _NAMES
    p = os.path.join(OUT, "contact_names.json")
    raw = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
    names = []
    for n in raw:
        n = n.strip()
        if len(n) < 3:
            continue
        if re.fullmatch(r"[0-9\W_]+", n):
            continue
        if n.lower() in _STOP:
            continue
        # all-lowercase multi-word phrases are usually not personal names
        if " " in n and re.fullmatch(r"[a-z .&|_-]+", n):
            continue
        names.append(n)
    names = sorted(set(names), key=len, reverse=True)[:3000]
    parts = []
    for n in names:
        e = re.escape(n)
        if re.search(r"[A-Za-z]", n):
            parts.append(rf"(?<![A-Za-z0-9]){e}(?![A-Za-z0-9])")
        else:
            parts.append(e)
    _NAMES = re.compile("|".join(parts)) if parts else None
    return _NAMES


def redact(text: str) -> str:
    if not text:
        return text
    s = URL.sub("[链接]", text)
    s = EMAIL.sub("[邮箱]", s)
    s = WXID.sub("[微信ID]", s)
    s = IDNO.sub("[证件号]", s)
    s = BANK.sub("[卡号]", s)
    s = PHONE.sub("[电话]", s)
    s = LAND.sub("[电话]", s)
    s = AT.sub("[姓名]", s)
    pat = _names()
    if pat is not None:
        s = pat.sub("[姓名]", s)
    return s
