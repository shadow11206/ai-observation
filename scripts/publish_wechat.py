#!/usr/bin/env python3
"""推送日报摘要到微信公众号草稿箱。

用法:
    python scripts/publish_wechat.py                # 推送今天的日报
    python scripts/publish_wechat.py 2026-06-10     # 推送指定日期

环境变量:
    WECHAT_APPID      — 微信公众号 AppID
    WECHAT_APPSECRET  — 微信公众号 AppSecret
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path

import requests
import yaml
from PIL import Image

BJT = timezone(timedelta(hours=8))
REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN_CACHE = REPO_ROOT / ".wechat_token_cache.json"


def load_config():
    with open(REPO_ROOT / "scripts" / "config.yaml") as f:
        return yaml.safe_load(f)


def today_str():
    return datetime.now(BJT).strftime("%Y-%m-%d")


def resolve_date(argv_date=None):
    if argv_date:
        return argv_date
    return today_str()


def load_report_json(date_str):
    year_month = date_str[:7]
    path = REPO_ROOT / "01-daily-reports" / year_month / f"{date_str}.json"
    if not path.exists():
        print(f"❌ 日报文件不存在: {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def load_cache():
    if TOKEN_CACHE.exists():
        return json.loads(TOKEN_CACHE.read_text())
    return {}


def save_cache(data):
    TOKEN_CACHE.write_text(json.dumps(data))


def get_access_token(appid, secret):
    cache = load_cache()
    if cache.get("expires_at", 0) > time.time() + 60:
        return cache["access_token"]

    url = "https://api.weixin.qq.com/cgi-bin/token"
    resp = requests.get(url, params={
        "grant_type": "client_credential",
        "appid": appid,
        "secret": secret,
    }, timeout=15)
    data = resp.json()
    if "access_token" not in data:
        print(f"❌ 获取 access_token 失败: {data}")
        sys.exit(1)

    cache["access_token"] = data["access_token"]
    cache["expires_at"] = time.time() + data.get("expires_in", 7200) - 300
    save_cache(cache)
    return data["access_token"]


def get_or_upload_thumb(access_token):
    """上传一次占位封面并永久缓存，封面在后台手动替换。"""
    cache = load_cache()
    thumb_id = cache.get("thumb_media_id", "")
    if thumb_id:
        return thumb_id

    print("🖼️  上传占位封面（仅首次）...")
    img = Image.new("RGB", (900, 383), (15, 30, 80))
    buf = BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    url = (f"https://api.weixin.qq.com/cgi-bin/material/add_material"
           f"?access_token={access_token}&type=thumb")
    resp = requests.post(url, files={"media": ("cover.png", BytesIO(png_bytes), "image/png")}, timeout=30)
    data = resp.json()
    if "media_id" not in data:
        print(f"❌ 上传封面失败: {data}")
        sys.exit(1)

    cache["thumb_media_id"] = data["media_id"]
    save_cache(cache)
    return data["media_id"]


def _item_card(rank, item, show_source=True):
    title = escape_html(item.get("title", ""))
    finding = escape_html(item.get("finding", ""))
    source = escape_html(item.get("source", ""))

    parts = [
        '<div style="margin: 12px 0; padding: 12px; background: #fafafa; '
        'border-radius: 6px; border-left: 3px solid #1890ff;">',
    ]
    tag = f"{rank}. " if rank else ""
    parts.append(
        f'<p style="font-weight: bold; font-size: 15px; margin: 0 0 6px 0; color: #1a1a1a;">'
        f'{tag}{title}'
        f'</p>'
    )
    parts.append(
        f'<p style="font-size: 14px; color: #555; margin: 0 0 6px 0; line-height: 1.7;">'
        f'{finding}'
        f'</p>'
    )
    if show_source and source:
        parts.append(
            f'<p style="font-size: 12px; color: #999; margin: 0;">来源：{source}</p>'
        )
    parts.append('</div>')
    return "".join(parts)


def _section_header(text):
    return (
        f'<p style="font-weight: bold; font-size: 16px; margin-top: 20px; '
        f'color: #1a1a1a;">{text}</p>'
    )


def _or_item(slug, tokens_str):
    return (
        f'<span style="display: inline-block; margin: 4px 6px; padding: 4px 10px; '
        f'background: #e8f4fd; border-radius: 4px; font-size: 13px; color: #333;">'
        f'{escape_html(slug)} <b>{escape_html(tokens_str)}</b>'
        f'</span>'
    )


def build_wechat_html(report):
    top_items = report.get("top_items", [])
    summary = report.get("summary_one_line", "")
    date_str = report.get("date", "")
    model_tech = report.get("model_tech", [])
    company_product = report.get("company_product", [])
    or_ranking = report.get("snapshot", {}).get("openrouter_ranking", [])

    parts = [
        '<section style="padding: 10px 0; line-height: 1.8; color: #333; font-size: 15px;">',
    ]

    # 标题
    parts.append(
        f'<h2 style="text-align: center; font-size: 20px; color: #1a1a1a; margin-bottom: 8px;">'
        f'AI 日报 · {date_str}'
        f'</h2>'
    )

    # 一句话总结
    if summary:
        parts.append(
            f'<blockquote style="border-left: 3px solid #1890ff; padding: 8px 12px; '
            f'margin: 12px 0; background: #f0f7ff; color: #555; font-size: 14px;">'
            f'{escape_html(summary)}'
            f'</blockquote>'
        )

    # 今日最重要
    parts.append(_section_header("📌 今日最重要"))
    for item in top_items:
        parts.append(_item_card(item.get("rank", ""), item))

    # 模型/技术动态（取前 2 条）
    if model_tech:
        parts.append(_section_header("🧠 模型/技术动态"))
        for i, item in enumerate(model_tech[:2], 1):
            parts.append(_item_card(i, item))

    # 公司/产品动态（取前 2 条）
    if company_product:
        parts.append(_section_header("🏢 公司/产品动态"))
        for i, item in enumerate(company_product[:2], 1):
            parts.append(_item_card(i, item))

    # OpenRouter 日调用排行
    if or_ranking:
        parts.append(_section_header("📊 OpenRouter 日调用量排行 TOP 10"))
        parts.append('<p style="line-height: 2.2; margin: 8px 0;">')
        for entry in or_ranking[:10]:
            slug = entry.get("slug", entry.get("name", ""))
            tokens = entry.get("total_tokens_str", "")
            parts.append(_or_item(slug, f"日 {tokens}"))
        parts.append('</p>')

    parts.append('</section>')
    return "".join(parts)


def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def create_draft(access_token, title, content, thumb_media_id, source_url):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
    body = {
        "articles": [{
            "title": title,
            "author": "赛博中登",
            "thumb_media_id": thumb_media_id,
            "content": content,
            "content_source_url": source_url,
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }]
    }
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    resp = requests.post(url, data=payload, headers={"Content-Type": "application/json"}, timeout=30)
    data = resp.json()
    if "media_id" not in data:
        print(f"❌ 创建草稿失败: {data}")
        sys.exit(1)
    return data["media_id"]


def main():
    if len(sys.argv) > 1:
        date_str = resolve_date(sys.argv[1])
    else:
        date_str = resolve_date()

    appid = os.environ.get("WECHAT_APPID", "")
    secret = os.environ.get("WECHAT_APPSECRET", "")

    if not appid or not secret:
        print("⚠️  WECHAT_APPID 或 WECHAT_APPSECRET 未设置，跳过微信发布")
        return

    config = load_config()
    wechat_cfg = config.get("wechat", {})
    if not wechat_cfg.get("enabled", False):
        print("⚠️  wechat.enabled=false，跳过微信发布")
        return

    site_base_url = wechat_cfg.get("site_base_url", "").rstrip("/")
    if not site_base_url:
        print("❌ wechat.site_base_url 未配置")
        sys.exit(1)

    print(f"📅 日期: {date_str}")
    report = load_report_json(date_str)

    title = f"AI 日报 · {date_str}"
    top_count = len(report.get("top_items", []))
    mt_count = len(report.get("model_tech", []))
    cp_count = len(report.get("company_product", []))
    or_count = len(report.get("snapshot", {}).get("openrouter_ranking", []))
    print(f"📊 top_items: {top_count} | 模型技术: {mt_count} | 公司产品: {cp_count} | OR排行: {or_count}")

    html = build_wechat_html(report)
    print("🔑 获取 access_token ...")
    token = get_access_token(appid, secret)

    thumb_id = get_or_upload_thumb(token)

    print("📤 创建草稿 ...")
    daily_url = f"{site_base_url}/ui/daily.html?date={date_str}"
    media_id = create_draft(token, title, html, thumb_id, daily_url)
    print(f"✅ 草稿已创建，media_id: {media_id}")
    print(f"🔗 原文链接: {daily_url}")


if __name__ == "__main__":
    main()
