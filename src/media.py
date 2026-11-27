"""Image/video media helpers: locate .dat, decrypt, resize, read durations."""
from __future__ import annotations

import glob
import os
import struct

from PIL import Image

from crypto import decrypt_dat_bytes, derive_image_key, derive_xor_key


class Media:
    def __init__(self, attach_root: str, video_root: str, image_code: int,
                 wxid: str, out_dir: str, max_px: int = 900):
        self.attach_root = attach_root
        self.video_root = video_root
        self.aes_key = derive_image_key(image_code, wxid)
        self.xor_key = derive_xor_key(image_code)
        self.out_dir = out_dir
        self.max_px = max_px
        os.makedirs(out_dir, exist_ok=True)
        self._cache = {}
        self._index = {}
        for p in glob.glob(os.path.join(attach_root, "**", "Img", "*.dat"),
                           recursive=True):
            name = os.path.basename(p)[:-4]
            if "_" in name:
                md5, suffix = name.rsplit("_", 1)
            else:
                md5, suffix = name, ""
            self._index.setdefault(md5.lower(), []).append((suffix, p))

    def candidates(self, md5: str):
        items = self._index.get(md5.lower(), [])
        order = {"": 0, "h": 1, "t": 2}
        return [p for _s, p in sorted(items, key=lambda x: order.get(x[0], 9))]

    def export_image(self, md5: str, max_px: int | None = None) -> str | None:
        if not md5:
            return None
        if md5 in self._cache:
            return self._cache[md5]
        limit = max_px or self.max_px
        out = os.path.join(self.out_dir, f"{md5}.jpg")
        if os.path.exists(out):
            self._cache[md5] = out
            return out
        for path in self.candidates(md5):
            try:
                data = open(path, "rb").read()
            except OSError:
                continue
            plain, ext = decrypt_dat_bytes(data, self.aes_key, self.xor_key)
            if ext not in ("jpg", "png", "gif", "webp"):
                continue
            out = os.path.join(self.out_dir, f"{md5}.jpg")
            try:
                im = Image.open(__import__("io").BytesIO(plain))
                im = im.convert("RGB")
                if max(im.size) > limit:
                    im.thumbnail((limit, limit), Image.LANCZOS)
                im.save(out, "JPEG", quality=82, optimize=True)
            except Exception:
                continue
            self._cache[md5] = out
            return out
        return None

    def video_duration(self, md5: str) -> float | None:
        if not md5:
            return None
        hits = glob.glob(os.path.join(self.video_root, "**", f"{md5}*.mp4"),
                         recursive=True)
        if not hits:
            return None
        try:
            return mp4_duration(hits[0])
        except Exception:
            return None


def mp4_duration(path: str) -> float | None:
    with open(path, "rb") as f:
        data = f.read(2 * 1024 * 1024)
    idx = data.find(b"mvhd")
    if idx < 0 or idx + 32 > len(data):
        return None
    version = data[idx + 4]
    if version == 1:
        timescale = struct.unpack_from(">I", data, idx + 24)[0]
        duration = struct.unpack_from(">Q", data, idx + 28)[0]
    else:
        timescale = struct.unpack_from(">I", data, idx + 16)[0]
        duration = struct.unpack_from(">I", data, idx + 20)[0]
    if not timescale:
        return None
    return duration / timescale
