"""SQLCipher 4 (WeChat 4.x) database decryption + V2 .dat image decryption.

Verified against WeChat 4.2.0.53 data on 2026-11-26.
"""
from __future__ import annotations

import hashlib
import os
import struct

from Crypto.Cipher import AES

PAGE_SZ = 4096
RESERVE_SZ = 80          # IV(16) + HMAC(64)
IV_OFF = PAGE_SZ - RESERVE_SZ   # 4016
SALT_SZ = 16
SQLITE_HDR = b"SQLite format 3\x00"

V2_MAGIC = b"\x07\x08V2\x08\x07"
V1_MAGIC = b"\x07\x08V1\x08\x07"
V1_AES_KEY = b"cfcd208495d565ef"


# ---------------------------------------------------------------- image .dat

def derive_image_key(code: int, wxid: str) -> bytes:
    """Account-level V2 image key: md5(code + wxid)[:16] as 16 ASCII bytes."""
    return hashlib.md5(f"{code}{wxid}".encode()).hexdigest()[:16].encode()


def derive_xor_key(code: int) -> int:
    return code & 0xFF


def _guess_image_ext(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"GIF8"):
        return "gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"wxgf") or data.startswith(b"WXGF"):
        return "wxgf"
    return "bin"


def decrypt_dat_bytes(data: bytes, aes_key: bytes, xor_key: int) -> tuple[bytes, str]:
    """Decrypt a V2/V1 .dat blob; return (plaintext, extension)."""
    if data[:6] in (V2_MAGIC, V1_MAGIC):
        key = aes_key if data[:6] == V2_MAGIC else V1_AES_KEY
        _magic, aes_size, xor_size = struct.unpack("<6sLL", data[:14])
        aes_part = AES.new(key, AES.MODE_ECB).decrypt(data[15:15 + aes_size])
        tail_start = 15 + aes_size + 16
        tail = bytes(b ^ xor_key for b in data[tail_start:tail_start + xor_size])
        plain = aes_part + tail
        return plain, _guess_image_ext(plain)
    # legacy single-byte XOR
    for k in range(256):
        plain = bytes(b ^ k for b in data[:16])
        if _guess_image_ext(plain) != "bin":
            return bytes(b ^ k for b in data), _guess_image_ext(plain)
    return data, "bin"


def decrypt_dat_file(path: str, out_dir: str, aes_key: bytes,
                     xor_key: int) -> tuple[str | None, str | None]:
    with open(path, "rb") as f:
        data = f.read()
    plain, ext = decrypt_dat_bytes(data, aes_key, xor_key)
    if ext == "bin":
        return None, None
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(out_dir, f"{name}.{ext}")
    with open(out, "wb") as f:
        f.write(plain)
    return out, ext


# ---------------------------------------------------------------- SQLCipher

def derive_enc_key(password: bytes, salt: bytes, iterations: int = 256000) -> bytes:
    return hashlib.pbkdf2_hmac("sha512", password, salt, iterations, dklen=32)


def verify_enc_key(enc_key: bytes, page1: bytes) -> bool:
    if len(page1) < PAGE_SZ:
        return False
    iv = page1[IV_OFF:IV_OFF + 16]
    pt = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(page1[SALT_SZ:SALT_SZ + 16])
    return pt[0:2] == b"\x10\x00" and pt[4:8] == b"\x50\x40\x20\x20"


def decrypt_page(enc_key: bytes, page: bytes, pgno: int) -> bytes:
    if len(page) < PAGE_SZ:
        page = page + b"\x00" * (PAGE_SZ - len(page))
    iv = page[IV_OFF:IV_OFF + 16]
    if pgno == 1:
        dec = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(page[SALT_SZ:PAGE_SZ - RESERVE_SZ])
        return SQLITE_HDR + dec + b"\x00" * RESERVE_SZ
    dec = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(page[:PAGE_SZ - RESERVE_SZ])
    return dec + b"\x00" * RESERVE_SZ


def decrypt_database(src: str, dst: str, enc_key: bytes) -> int:
    size = os.path.getsize(src)
    pages = (size + PAGE_SZ - 1) // PAGE_SZ
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        for pgno in range(1, pages + 1):
            page = fi.read(PAGE_SZ)
            if not page:
                break
            fo.write(decrypt_page(enc_key, page, pgno))
    return pages


def apply_wal(db_path: str, wal_path: str, enc_key: bytes,
              out_path: str | None = None) -> int:
    """Replay a SQLCipher WAL onto a decrypted database. Returns frames applied."""
    if not os.path.exists(wal_path):
        return 0
    wal = open(wal_path, "rb").read()
    if len(wal) < 32:
        return 0
    # WAL header: magic(4) version(4) page_size(4) checkpoint(4) salt1(4) salt2(4) c1(4) c2(4)
    page_size = struct.unpack_from(">I", wal, 8)[0]
    if page_size != PAGE_SZ:
        return 0
    salt1, salt2 = struct.unpack_from(">II", wal, 16)
    out = out_path or db_path
    frames = 0
    with open(out, "r+b") as db:
        pos = 32
        while pos + 24 + PAGE_SZ <= len(wal):
            pgno, dbsize, s1, s2 = struct.unpack_from(">IIII", wal, pos)
            if pgno == 0:
                break
            if (s1, s2) != (salt1, salt2):
                pos += 24 + PAGE_SZ
                continue
            page = wal[pos + 24:pos + 24 + PAGE_SZ]
            plain = decrypt_page(enc_key, page, pgno)
            db.seek((pgno - 1) * PAGE_SZ)
            db.write(plain)
            frames += 1
            if dbsize:
                db.truncate(dbsize * PAGE_SZ)
            pos += 24 + PAGE_SZ
    return frames
