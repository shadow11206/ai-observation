# -*- coding: utf-8 -*-
"""
build_daily_index.py
扫描 01-daily-reports/ 下所有 .json 日报，提取关键字段，生成 ui/data/daily-index.json
供 index.html 首页「近期日报」区块动态渲染

运行方式:
  python scripts/build_daily_index.py
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "01-daily-reports"
OUTPUT_FILE = BASE_DIR / "ui" / "data" / "daily-index.json"


def extract_summary(data: dict) -> str:
    """从日报 JSON 中提取摘要：取前 3 条新闻标题拼成简介"""
    top_items = data.get("top_items", [])
    if not top_items:
        return ""
    titles = [item.get("title", "") for item in top_items[:3] if item.get("title")]
    if not titles:
        return ""
    # 取第一条标题作为主标题，后续作为补充
    if len(titles) == 1:
        return titles[0]
    return titles[0] + "…"


def extract_headline(data: dict) -> str:
    """生成日报标题：取 top_items 第一条标题，或 fallback"""
    top_items = data.get("top_items", [])
    if top_items and top_items[0].get("title"):
        first_title = top_items[0]["title"]
        # 如果有多条，拼成「XX + N 条重要动态」
        count = len(top_items)
        if count > 1:
            return f"今日 AI 日报：{first_title} + {count - 1} 条重要动态"
        return f"今日 AI 日报：{first_title}"
    return f"AI 日报 {data.get('date', '')}"


def extract_excerpt(data: dict) -> str:
    """生成摘要文字：取前 3 条新闻的 judgment 片段"""
    top_items = data.get("top_items", [])
    excerpts = []
    for item in top_items[:3]:
        j = item.get("judgment", "")
        if j:
            # 取前 40 个字
            excerpts.append(j[:40])
    if excerpts:
        return excerpts[0] + "…"
    return ""


def scan_reports() -> list:
    """扫描所有日报 JSON，返回按日期降序排列的列表"""
    entries = []
    for month_dir in sorted(REPORTS_DIR.iterdir(), reverse=True):
        if not month_dir.is_dir():
            continue
        for json_file in sorted(month_dir.glob("*.json"), reverse=True):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                date = data.get("date") or json_file.stem
                entries.append({
                    "date": date,
                    "title": extract_headline(data),
                    "excerpt": extract_excerpt(data),
                    "top_count": len(data.get("top_items", [])),
                    "file": json_file.name,
                })
            except Exception as e:
                print(f"  ⚠️ 解析 {json_file.name} 失败: {e}")
    return entries


def main():
    print("🔧 build_daily_index.py 启动...")
    entries = scan_reports()
    output = {
        "total": len(entries),
        "reports": entries,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 已生成 ui/data/daily-index.json")
    print(f"  📊 共 {len(entries)} 期日报")
    for e in entries[:5]:
        print(f"     - {e['date']}: {e['title'][:40]}...")


if __name__ == "__main__":
    main()
