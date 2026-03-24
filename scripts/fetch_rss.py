"""
信息获取层 - Level 1：RSS 抓取
============================
后续升级路径：
  Level 2 → 替换为 fetch_api.py（Perplexity/Exa API）
  Level 3 → 替换为 fetch_browser.py（AI Agent 控制浏览器）

只需替换本文件中的 fetch_info() 函数，下游 generate_daily.py 不需要改动。
"""

import feedparser
import yaml
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateutil_parser


def load_config() -> dict:
    with open("scripts/config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_info() -> list[dict]:
    """
    主入口：从 RSS 抓取过去 N 小时内的信息
    返回格式：[{"source": str, "title": str, "url": str, "summary": str, "published": str}]
    """
    config = load_config()
    rss_feeds = config["rss_feeds"]
    hours_lookback = config["filter"]["hours_lookback"]
    max_items = config["filter"]["max_items_per_feed"]
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)

    all_items = []

    for feed_config in rss_feeds:
        name = feed_config["name"]
        url = feed_config["url"]
        priority = feed_config.get("priority", 1)

        try:
            feed = feedparser.parse(url)
            items = _parse_feed_items(feed, name, priority, cutoff_time, max_items)
            all_items.extend(items)
            print(f"  ✓ {name}: {len(items)} 条")
        except Exception as e:
            print(f"  ✗ {name}: 抓取失败 - {e}")

    # 按优先级和时间排序
    all_items.sort(key=lambda x: (-x["priority"], x["published"]), reverse=False)
    print(f"\n共抓取 {len(all_items)} 条信息")
    return all_items


def _parse_feed_items(feed, source_name: str, priority: int,
                      cutoff_time: datetime, max_items: int) -> list[dict]:
    items = []
    for entry in feed.entries[:max_items * 2]:  # 多取一些，过滤后剩 max_items
        try:
            # 解析发布时间
            published_str = entry.get("published", "") or entry.get("updated", "")
            if published_str:
                published_dt = dateutil_parser.parse(published_str)
                if published_dt.tzinfo is None:
                    published_dt = published_dt.replace(tzinfo=timezone.utc)
            else:
                published_dt = datetime.now(timezone.utc)

            # 只取 cutoff_time 之后的
            if published_dt < cutoff_time:
                continue

            # 提取摘要
            summary = (
                entry.get("summary", "")
                or entry.get("description", "")
                or ""
            )[:500]  # 限制长度，节省 token

            items.append({
                "source": source_name,
                "priority": priority,
                "title": entry.get("title", "无标题"),
                "url": entry.get("link", ""),
                "summary": summary,
                "published": published_dt.strftime("%Y-%m-%d %H:%M UTC"),
            })

            if len(items) >= max_items:
                break

        except Exception:
            continue

    return items
