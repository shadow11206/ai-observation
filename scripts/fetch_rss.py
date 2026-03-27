"""
信息获取层 - Level 1：RSS 抓取
============================
后续升级路径：
  Level 2 → 替换为 fetch_api.py（Perplexity/Exa API）
  Level 3 → 替换为 fetch_browser.py（AI Agent 控制浏览器）

接口规范：fetch_info(config=None) → list[dict]
  - config=None 时自动加载 scripts/config.yaml
  - config 可由调用方传入（供 update_tracking.py 临时修改 lookback 时间使用）
"""

import feedparser
import yaml
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateutil_parser
from pathlib import Path


def load_config() -> dict:
    with open("scripts/config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_info(config: dict = None) -> list[dict]:
    """
    主入口：从 RSS 抓取过去 N 小时内的信息

    参数：
      config: 外部传入的配置 dict（可选）。
              None 时自动从 scripts/config.yaml 加载。
              传入时直接使用，方便调用方临时覆盖 hours_lookback 等参数。

    返回：
      [{"source": str, "title": str, "url": str, "summary": str,
        "published": str, "priority": int, "person": str}]
    """
    if config is None:
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
        person = feed_config.get("person", "")  # 与人物追踪的关联字段

        try:
            feed = feedparser.parse(url)
            items = _parse_feed_items(feed, name, priority, cutoff_time, max_items, person)
            all_items.extend(items)
            print(f"  ✓ {name}: {len(items)} 条")
        except Exception as e:
            print(f"  ✗ {name}: 抓取失败 - {e}")

    # 按优先级降序、时间升序排序
    all_items.sort(key=lambda x: (-x["priority"], x["published"]))
    print(f"\n共抓取 {len(all_items)} 条信息")
    return all_items


def _parse_feed_items(feed, source_name: str, priority: int,
                      cutoff_time: datetime, max_items: int,
                      person: str = "") -> list[dict]:
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

            # 提取摘要（清除 HTML 标签，控制长度）
            summary = (
                entry.get("summary", "")
                or entry.get("description", "")
                or ""
            )
            # 简单去除 HTML 标签
            summary = _strip_html(summary)[:500]

            items.append({
                "source": source_name,
                "priority": priority,
                "person": person,          # 关联追踪人物（空字符串表示无关联）
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


def _strip_html(text: str) -> str:
    """简单去除 HTML 标签"""
    import re
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean
