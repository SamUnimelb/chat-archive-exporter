"""Render normalized chat messages to a single self-contained-ish HTML file."""
from __future__ import annotations

import os
from collections import OrderedDict
from datetime import datetime
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape


def _img_src(path: str, html_dir: str) -> str:
    if not path:
        return ""
    rel = os.path.relpath(path, html_dir)
    return quote(rel.replace("\\", "/"))


def group_by_day(messages: list[dict]) -> list[dict]:
    days: "OrderedDict[str, list]" = OrderedDict()
    for m in messages:
        days.setdefault(m["date"], []).append(m)
    return [{"date": d, "messages": ms} for d, ms in days.items()]


def render_html(messages: list[dict], account: dict, stats: dict,
                out_path: str, assets_dir: str, title: str,
                subtitle: str, template: str = "chat.html.j2",
                **extra) -> str:
    html_dir = os.path.dirname(os.path.abspath(out_path))
    msgs = []
    for m in messages:
        m = dict(m)
        if m.get("image_path"):
            m["image_path"] = _img_src(m["image_path"], html_dir)
        if m.get("avatar"):
            m["avatar"] = _img_src(m["avatar"], html_dir)
        msgs.append(m)

    env = Environment(
        loader=FileSystemLoader(assets_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tmpl = env.get_template(template)
    html = tmpl.render(
        title=title,
        subtitle=subtitle,
        account=account,
        stats=stats,
        days=group_by_day(msgs),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        **extra,
    )
    os.makedirs(html_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
