"""Dump schema and sample rows of a decrypted WeChat database."""
import json
import sqlite3
import sys


def main(path):
    conn = sqlite3.connect(path)
    conn.text_factory = bytes
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
    ).fetchall()
    for typ, name, sql in rows:
        name_s = name.decode("utf-8", "replace") if isinstance(name, bytes) else name
        print("=" * 100)
        print(name_s)
        print(sql.decode("utf-8", "replace") if isinstance(sql, bytes) else sql)
        try:
            sample = cur.execute(f"SELECT * FROM [{name_s}] LIMIT 2").fetchall()
            cols = [d[0] for d in cur.description]
            print("columns:", cols)
            for r in sample:
                out = []
                for v in r:
                    if isinstance(v, bytes):
                        out.append(v[:80].hex())
                    else:
                        out.append(v)
                print("row:", out)
            cnt = cur.execute(f"SELECT COUNT(*) FROM [{name_s}]").fetchone()[0]
            print("count:", cnt)
        except Exception as e:
            print("sample error:", e)
    conn.close()


if __name__ == "__main__":
    main(sys.argv[1])
