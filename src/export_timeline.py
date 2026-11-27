"""Generate a heuristic relationship timeline PDF from chat text."""
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

CATS = {
    "相识": ["通过了你的朋友验证"],
    "好感": ["喜欢你", "爱你", "心动", "love you", "miss you", "crush", "中意"],
    "确立关系": ["在一起", "男朋友", "女朋友", "boyfriend", "girlfriend", "my love",
                 "未婚妻", "未婚夫"],
    "见面": ["见面", "见到", "接你", "等你", "来找我"],
    "家人": ["爸妈", "父母", "见家长", "我妈", "我爸", "你妈", "你爸", "家里人"],
    "结婚": ["结婚", "订婚", "求婚", "戒指", "婚纱", "婚礼", "领证", "婚房",
             "彩礼", "伴娘", "伴郎", "嫁给我", "娶你", "嫁给你", "成婚",
             "marry", "married", "wedding", "engagement"],
    "签证/移民": ["签证", "配偶", "绿卡", "移民", "同居", "公证",
                  "partner visa", "spouse"],
    "旅行": ["旅行", "旅游", "蜜月", "酒店", "机票", "度假", "自驾"],
    "纪念": ["生日", "纪念日", "情人节", "七夕", "圣诞", "周年",
             "anniversary", "birthday"],
}

# High-confidence phrases only: used for the cover "key milestones" and monthly
# highlights, so that casual mentions (e.g. "我妈", "悉尼") don't masquerade as
# relationship milestones.
STRONG = {
    "好感": ["爱你", "喜欢你", "love you", "miss you", "想你", "心动"],
    "确立关系": ["做我女朋友", "做我男朋友", "在一起吧", "我们在一起",
                 "男朋友", "女朋友", "boyfriend", "girlfriend", "未婚妻", "未婚夫"],
    "见面": ["第一次见面", "接机", "来接你", "见面吧", "见一面", "见面的时候"],
    "家人": ["见家长", "见我爸妈", "见你爸妈", "见我父母", "见你父母",
             "叔叔阿姨", "爸妈很喜欢你", "我爸妈很喜欢"],
    "结婚": ["结婚", "订婚", "求婚", "领证", "婚纱", "婚礼", "彩礼", "婚房",
             "嫁给我", "娶你", "嫁给你", "marry me"],
    "签证/移民": ["配偶签证", "partner visa", "spouse visa", "担保你", "担保我",
                  "同居证明", "关系材料", "relationship evidence", "配偶移民"],
    "旅行": ["旅行", "蜜月", "度假", "一起出去玩", "自驾"],
    "纪念": ["纪念日", "周年", "anniversary"],
}


def _match(text, table):
    t = (text or "").lower()
    if ("签证" in t or "visa" in t) and "签证/移民" in table:
        return "签证/移民"
    for cat, kws in table.items():
        if any(k.lower() in t for k in kws):
            return cat
    return None


def category(text):
    return _match(text, STRONG) or _match(text, CATS)


def short(text, n=180):
    s = " ".join((text or "").split())
    return s[:n] + ("…" if len(s) > n else "")


def main():
    raw = json.load(open(os.path.join(OUT, "export_items.json"), encoding="utf-8"))
    raw.sort(key=lambda m: (m["ts"], m.get("server_id") or 0))
    usable = [m for m in raw if m["type"] not in ("call", "system", "location_share")]
    text_items = [m for m in usable if (m.get("text") or "").strip()
                  and m["type"] in ("text", "link", "app", "miniprogram", "forward",
                                    "quote", "transfer", "redpacket", "location", "card")]
    if not usable:
        print("no data")
        return 1

    month_counts = {}
    for m in usable:
        dt = datetime.fromtimestamp(m["ts"])
        ym = dt.strftime("%Y-%m")
        month_counts[ym] = month_counts.get(ym, 0) + 1
    top_months = sorted(month_counts.items(), key=lambda x: -x[1])[:5]
    top_str = "；".join(f"{k}（{v} 条）" for k, v in top_months)

    keydates = []
    seen_cats = set()
    first_text = text_items[0]
    dt = datetime.fromtimestamp(first_text["ts"])
    keydates.append({
        "tag": "相识",
        "when": dt.strftime("%Y-%m-%d %H:%M"),
        "name": ACCOUNT["target_display"] if first_text["sender"] == "other"
                else ACCOUNT["self_display"],
        "text": short(first_text["text"], 120),
    })
    seen_cats.add("相识")
    for m in text_items[1:]:
        cat = _match(m["text"], STRONG)
        if cat and cat not in seen_cats:
            seen_cats.add(cat)
            dt = datetime.fromtimestamp(m["ts"])
            keydates.append({
                "tag": cat,
                "when": dt.strftime("%Y-%m-%d %H:%M"),
                "name": ACCOUNT["target_display"] if m["sender"] == "other"
                        else ACCOUNT["self_display"],
                "text": short(m["text"], 120),
            })

    per_month = {}
    for m in text_items:
        cat = category(m["text"])
        if not cat:
            continue
        dt = datetime.fromtimestamp(m["ts"])
        ym = dt.strftime("%Y-%m")
        per_month.setdefault(ym, []).append({
            "tag": cat,
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M"),
            "name": ACCOUNT["target_display"] if m["sender"] == "other"
                    else ACCOUNT["self_display"],
            "text": short(m["text"], 180),
        })

    months = []
    for ym in sorted(month_counts):
        sub = [m for m in usable if datetime.fromtimestamp(m["ts"]).strftime("%Y-%m") == ym]
        items = per_month.get(ym, [])
        seen = set()
        uniq = []
        for it in items:
            if it["text"] in seen or it["date"] in {u["date"] for u in uniq}:
                continue
            seen.add(it["text"])
            uniq.append(it)
            if len(uniq) >= 5:
                break
        if not uniq:
            first = next((m for m in sub if (m.get("text") or "").strip()), None)
            if first:
                dt = datetime.fromtimestamp(first["ts"])
                uniq = [{
                    "tag": "日常",
                    "date": dt.strftime("%Y-%m-%d"),
                    "time": dt.strftime("%H:%M"),
                    "name": ACCOUNT["target_display"] if first["sender"] == "other"
                            else ACCOUNT["self_display"],
                    "text": short(first["text"], 180),
                }]
        months.append({
            "ym": ym,
            "stats": (f"共 {len(sub)} 条 · 文字 {sum(1 for x in sub if x['type']=='text')} · "
                      f"图片 {sum(1 for x in sub if x['type']=='image')} · "
                      f"语音 {sum(1 for x in sub if x['type']=='voice')} · "
                      f"视频 {sum(1 for x in sub if x['type']=='video')}"),
            "entries": uniq,
        })

    first = datetime.fromtimestamp(usable[0]["ts"])
    last = datetime.fromtimestamp(usable[-1]["ts"])
    stats = {
        "first_time": first.strftime("%Y-%m-%d %H:%M"),
        "last_time": last.strftime("%Y-%m-%d %H:%M"),
        "days": (last.date() - first.date()).days + 1,
        "total": len(usable),
        "text": sum(1 for m in usable if m["type"] == "text"),
        "image": sum(1 for m in usable if m["type"] == "image"),
        "voice": sum(1 for m in usable if m["type"] == "voice"),
        "video": sum(1 for m in usable if m["type"] == "video"),
        "file": sum(1 for m in usable if m["type"] == "file"),
        "top_months": top_str,
    }
    html = os.path.join(OUT, "relationship_timeline.html")
    render_html([], ACCOUNT, stats, html, os.path.join(BASE, "assets"),
                "关系时间线", "Relationship Timeline", template="timeline.html.j2",
                months=months, keydates=keydates)
    pdf = os.path.join(OUT, "relationship_timeline.pdf")
    html_to_pdf(html, pdf)
    print("months", len(months), "keydates", len(keydates))
    print("PDF", pdf, os.path.getsize(pdf))
    return 0


if __name__ == "__main__":
    sys.exit(main())
