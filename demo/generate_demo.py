"""Generate the synthetic demo dataset (no real chat data)."""
import json
import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(BASE, "images")
os.makedirs(IMAGES, exist_ok=True)


def ts(day, hour, minute, second=0):
    return int(datetime(2026, 1, day, hour, minute, second).timestamp())


def make_image(name, label, color1, color2):
    img = Image.new("RGB", (760, 428), color1)
    draw = ImageDraw.Draw(img)
    for y in range(428):
        t = y / 427
        draw.line(
            [(0, y), (760, y)],
            fill=(int(color1[0] * (1 - t) + color2[0] * t),
                  int(color1[1] * (1 - t) + color2[1] * t),
                  int(color1[2] * (1 - t) + color2[2] * t)),
        )
    try:
        font = ImageFont.truetype("arial.ttf", 46)
    except OSError:
        font = ImageFont.load_default()
    draw.text((40, 330), label, fill=(255, 255, 255), font=font)
    draw.text((40, 40), "DEMO IMAGE", fill=(255, 255, 255), font=font)
    path = os.path.join(IMAGES, name)
    img.save(path, "JPEG", quality=86)


make_image("IMG_2026_01_02_10_05_00.jpg", "2026-01-02 10:05", (36, 99, 235), (16, 185, 129))
make_image("IMG_2026_01_03_10_12_00.jpg", "2026-01-03 10:12", (236, 72, 153), (249, 115, 22))
make_image("IMG_2026_01_04_09_30_00.jpg", "2026-01-04 09:30", (99, 102, 241), (14, 165, 233))


def img_item(day, h, m, name, text=""):
    p = os.path.join(IMAGES, name)
    dims = Image.open(p).size
    return {
        "ts": ts(day, h, m), "sender": "other", "type": "image", "text": text,
        "md5": name, "duration": 0, "extra": "", "server_id": ts(day, h, m),
        "image_path": "images/" + name,
        "image_dims": "%dx%d" % dims,
        "image_size": os.path.getsize(p),
    }


items = [
    {"ts": ts(2, 9, 2), "sender": "other", "type": "text",
     "text": "早上好呀，今天降温了，出门记得加件外套。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 9, 5), "sender": "self", "type": "text",
     "text": "刚出门就后悔了，风好大。你在公司了吗？", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 9, 6), "sender": "other", "type": "text",
     "text": "到了，正在泡咖啡 ☕", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 9, 10), "sender": "self", "type": "text",
     "text": "我下午要去一趟图书馆，顺便把上次借的书还了。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 9, 12), "sender": "other", "type": "text",
     "text": "那晚上一起吃饭吗？附近新开了一家云南米线。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 9, 13), "sender": "self", "type": "text",
     "text": "好呀，六点半？", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 9, 15), "sender": "other", "type": "location",
     "text": "城市图书馆地铁站 B 口", "md5": "", "duration": 0, "extra": ""},
    img_item(2, 10, 5, "IMG_2026_01_02_10_05_00.jpg", "这家店的菜单，看着还不错。"),
    {"ts": ts(2, 10, 7), "sender": "self", "type": "text",
     "text": "那个酸汤米线感觉很适合今天。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 12, 20), "sender": "self", "type": "text",
     "text": "我到了，人有点多，先占了个位。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 12, 22), "sender": "other", "type": "text",
     "text": "马上到，等我五分钟。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 13, 5), "sender": "other", "type": "voice",
     "text": "", "md5": "", "duration": 18, "extra": ""},
    {"ts": ts(2, 13, 7), "sender": "self", "type": "sticker",
     "text": "", "md5": "", "duration": 0, "extra": "", "sticker_name": "好耶"},
    {"ts": ts(2, 14, 30), "sender": "self", "type": "file",
     "text": "读书笔记_2026-01.pdf", "md5": "", "duration": 0, "extra": "",
     "file_size": 1284920},
    {"ts": ts(2, 14, 31), "sender": "self", "type": "text",
     "text": "上次说的那本书，笔记整理好了。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 15, 40), "sender": "other", "type": "link",
     "text": "周末徒步路线推荐（附交通和补给点）", "md5": "", "duration": 0,
     "extra": "含三条近郊路线，适合半天往返。"},
    {"ts": ts(2, 15, 41), "sender": "other", "type": "text",
     "text": "周末要不要去走走？", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 15, 45), "sender": "self", "type": "text",
     "text": "可以！不过别太早，我想睡个懒觉。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(2, 15, 46), "sender": "other", "type": "sticker",
     "text": "", "md5": "", "duration": 0, "extra": "", "sticker_name": "成交"},

    {"ts": ts(3, 8, 50), "sender": "self", "type": "text",
     "text": "早，昨晚睡得不错。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(3, 8, 52), "sender": "other", "type": "text",
     "text": "我也是，今天天气看着会晴。", "md5": "", "duration": 0, "extra": ""},
    img_item(3, 10, 12, "IMG_2026_01_03_10_12_00.jpg", "刚路过花市，顺手拍了一张。"),
    {"ts": ts(3, 10, 15), "sender": "self", "type": "text",
     "text": "好看，周末去逛逛？", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(3, 10, 16), "sender": "other", "type": "text",
     "text": "好啊，顺便把那家面包店打卡了。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(3, 18, 30), "sender": "self", "type": "video",
     "text": "", "md5": "", "duration": 12, "extra": "", "video_size": 3565158,
     "video_path": "videos/demo.mp4"},
    {"ts": ts(3, 18, 31), "sender": "self", "type": "text",
     "text": "傍晚的海边，风有点大。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(3, 20, 10), "sender": "other", "type": "quote",
     "text": "我已经在查路线了。", "md5": "", "duration": 0, "extra": "周末去逛逛？"},
    {"ts": ts(3, 21, 0), "sender": "self", "type": "text",
     "text": "那就这么定了，晚安。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(3, 21, 1), "sender": "other", "type": "text",
     "text": "晚安 🌙", "md5": "", "duration": 0, "extra": ""},

    img_item(4, 9, 30, "IMG_2026_01_04_09_30_00.jpg", "早餐做了松饼，下次做给你吃。"),
    {"ts": ts(4, 9, 33), "sender": "self", "type": "text",
     "text": "看起来很不错，期待。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(4, 11, 0), "sender": "self", "type": "transfer",
     "text": "转账 52.00", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(4, 11, 1), "sender": "self", "type": "text",
     "text": "上次的咖啡钱～", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(4, 11, 2), "sender": "other", "type": "redpacket",
     "text": "红包 8.88", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(4, 11, 3), "sender": "other", "type": "text",
     "text": "收下这份好运。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(4, 12, 0), "sender": "self", "type": "card",
     "text": "Demo Contact（户外向导）", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(4, 14, 20), "sender": "other", "type": "text",
     "text": "收到啦，周末见。", "md5": "", "duration": 0, "extra": ""},
    {"ts": ts(4, 14, 21), "sender": "self", "type": "text",
     "text": "周末见 👋", "md5": "", "duration": 0, "extra": ""},
]

for i, m in enumerate(items, 1):
    m.setdefault("server_id", i)
    m.setdefault("md5", "")
    m.setdefault("duration", 0)
    m.setdefault("extra", "")

items.sort(key=lambda m: m["ts"])
with open(os.path.join(BASE, "export_items.json"), "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=1)
print("demo items", len(items))
