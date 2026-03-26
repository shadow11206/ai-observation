"""
信息获取层 - 今日数据快照
==========================
抓取 Hugging Face 热门模型 + GitHub Trending AI 项目
这两个都有公开 API/页面，无需 API Key。

返回格式：
{
  "hf_trending": [{"name": str, "likes": int, "url": str, "desc": str}],
  "github_trending": [{"name": str, "stars": str, "url": str, "desc": str, "language": str}]
}
"""

import requests
from datetime import datetime


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Observation-Bot/1.0)",
    "Accept": "application/json",
}


def fetch_snapshot() -> dict:
    """主入口：获取今日数据快照"""
    snapshot = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "hf_trending": [],
        "github_trending": [],
    }

    print("  📊 抓取 Hugging Face Trending 模型...")
    snapshot["hf_trending"] = _fetch_hf_trending()

    print("  📊 抓取 GitHub Trending AI 项目...")
    snapshot["github_trending"] = _fetch_github_trending()

    total = len(snapshot["hf_trending"]) + len(snapshot["github_trending"])
    print(f"  ✓ 快照完成：HF {len(snapshot['hf_trending'])} 个模型，GitHub {len(snapshot['github_trending'])} 个项目")
    return snapshot


def _fetch_hf_trending() -> list[dict]:
    """抓取 Hugging Face 趋势模型（官方 API，无需 Key）"""
    try:
        # HF 公开 API：获取最近 24h 内 likes 增长最多的模型
        url = "https://huggingface.co/api/models"
        params = {
            "sort": "likes7d",
            "direction": "-1",
            "limit": 8,
            "full": "false",
            "config": "false",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        models = resp.json()

        result = []
        for m in models[:8]:
            result.append({
                "name": m.get("id", ""),
                "likes": m.get("likes", 0),
                "downloads": m.get("downloads", 0),
                "url": f"https://huggingface.co/{m.get('id', '')}",
                "tags": m.get("tags", [])[:3],
            })
        return result
    except Exception as e:
        print(f"  ⚠️ HF Trending 抓取失败：{e}")
        return []


def _fetch_github_trending() -> list[dict]:
    """抓取 GitHub Trending AI 相关项目（使用 GitHub Search API，无需 Key）"""
    try:
        # 用 GitHub Search API 查最近 1 天内 star 增长的 AI 项目
        from datetime import timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        url = "https://api.github.com/search/repositories"
        params = {
            "q": f"topic:llm topic:ai created:>{yesterday}",
            "sort": "stars",
            "order": "desc",
            "per_page": 6,
        }
        # 也查一下最近更新的热门 AI 项目
        resp = requests.get(url, params=params, headers={**HEADERS, "Accept": "application/vnd.github.v3+json"}, timeout=15)

        if resp.status_code == 403:
            # Rate limit，换一个查询
            params["q"] = f"machine-learning OR llm pushed:>{yesterday} stars:>100"
            resp = requests.get(url, params=params, headers={**HEADERS, "Accept": "application/vnd.github.v3+json"}, timeout=15)

        resp.raise_for_status()
        items = resp.json().get("items", [])

        result = []
        for repo in items[:6]:
            result.append({
                "name": repo.get("full_name", ""),
                "desc": (repo.get("description") or "")[:100],
                "stars": repo.get("stargazers_count", 0),
                "language": repo.get("language") or "—",
                "url": repo.get("html_url", ""),
                "topics": repo.get("topics", [])[:3],
            })
        return result
    except Exception as e:
        print(f"  ⚠️ GitHub Trending 抓取失败：{e}")
        return []
