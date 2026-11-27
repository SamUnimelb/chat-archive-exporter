"""Validate database keys supplied by the user (no process access, no extraction).

Usage:
    python src/import_key.py --keys output/keys.json
    python src/import_key.py --keys output/keys.json --db path/to/message_0.db
    python src/import_key.py --keys output/keys.json --db-dir path/to/db_storage

Key file format (JSON):
    {"message_0": "<64 hex chars>", "contact": "<64 hex chars>", ...}
The key name is matched against the database file stem (with or without ".db").
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys

from Crypto.Cipher import AES

SQLITE_HDR = b"SQLite format 3\x00"
PAGE_SIZE = 4096
KDF_ITER = 256000


def verify(db_path: str, key_hex: str) -> bool:
    try:
        raw = bytes.fromhex(key_hex)
    except ValueError:
        return False
    if len(raw) != 32:
        return False
    with open(db_path, "rb") as fh:
        page1 = fh.read(PAGE_SIZE)
    if len(page1) < 4096:
        return False
    salt = page1[:16]
    iv = page1[4016:4032]
    ciphertext = page1[16:32]
    derived = hashlib.pbkdf2_hmac("sha512", raw, salt, KDF_ITER, 32)
    plain = AES.new(derived, AES.MODE_CBC, iv).decrypt(ciphertext)
    return plain == SQLITE_HDR


def find_dbs(db_dir: str) -> list[str]:
    return sorted(glob.glob(os.path.join(db_dir, "**", "*.db"), recursive=True))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keys", default=os.path.join("output", "keys.json"),
                    help="JSON file mapping database name to 64-char hex key")
    ap.add_argument("--db", action="append", default=[],
                    help="database file to check (repeatable)")
    ap.add_argument("--db-dir", help="directory to scan recursively for *.db")
    args = ap.parse_args(argv)

    if not os.path.exists(args.keys):
        print("key file not found:", args.keys)
        return 1
    with open(args.keys, encoding="utf-8") as fh:
        keys = json.load(fh)

    if not isinstance(keys, dict) or not keys:
        print("key file must be a non-empty JSON object")
        return 1

    bad = [name for name, value in keys.items()
           if not (isinstance(value, str) and len(value) == 64
                   and all(c in "0123456789abcdefABCDEF" for c in value))]
    if bad:
        print("invalid key entries (need 64 hex chars):", ", ".join(bad))
        return 1
    print("format OK: %d key(s)" % len(keys))

    dbs = list(args.db)
    if args.db_dir:
        dbs.extend(find_dbs(args.db_dir))
    if not dbs:
        print("no database supplied; format check only "
              "(use --db or --db-dir to verify)")
        return 0

    ok = fail = skip = 0
    for db in dbs:
        stem = os.path.splitext(os.path.basename(db))[0]
        key = keys.get(stem) or keys.get(stem + ".db")
        if not key:
            print("SKIP", db, "(no key entry)")
            skip += 1
            continue
        if verify(db, key):
            print("OK  ", db)
            ok += 1
        else:
            print("FAIL", db)
            fail += 1
    print("verified: %d ok, %d failed, %d skipped" % (ok, fail, skip))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
