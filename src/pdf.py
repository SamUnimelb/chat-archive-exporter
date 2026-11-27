"""Print an HTML file to PDF using the locally installed Edge/Chrome."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser() -> str:
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("未找到 Edge/Chrome，请安装 Edge 或修改 src/pdf.py 中的路径")


def html_to_pdf(html_path: str, pdf_path: str) -> str:
    browser = find_browser()
    html_path = os.path.abspath(html_path)
    pdf_path = os.path.abspath(pdf_path)
    os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)
    uri = Path(html_path).as_uri()
    before = os.stat(pdf_path).st_mtime_ns if os.path.exists(pdf_path) else None
    # A per-call profile keeps this instance independent: reusing the default
    # profile while another Edge is open silently hands the job to that process
    # and returns without writing the PDF.
    profile = tempfile.mkdtemp(prefix="wechat_pdf_")
    try:
        subprocess.run([
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-pdf-header-footer",
            "--allow-file-access-from-files",
            f"--user-data-dir={profile}",
            "--virtual-time-budget=120000",
            f"--print-to-pdf={pdf_path}",
            uri,
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if not os.path.exists(pdf_path):
        raise RuntimeError(f"浏览器未生成 PDF：{pdf_path}")
    if before is not None and os.stat(pdf_path).st_mtime_ns == before:
        raise RuntimeError(f"浏览器未覆盖旧 PDF（可能被占用）：{pdf_path}")
    return pdf_path
