"""
信息获取层 - 今日数据快照
==========================
抓取 Hugging Face 热门模型 + GitHub Trending AI 项目
这两个都有公开 API/页面，无需 API Key。

修复记录：
- 403 fallback 后正确检查新响应状态码
- GitHub 查询改为 OR 逻辑，避免 topic 同时命中率极低
- 独立 timeout，两个请求互不影响
"""

import requests
from datetime import datetime, timedelta


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Observation-Bot/1.0)",
    "Accept": "application/json",
}

GITHUB_HEADERS = {**HEADERS, "Accept": "application/vnd.github.v3+json"}


def fetch_snapshot() -> dict:
    """主入口：获取今日数据快照，两个源各自独立，互不影响"""
    snapshot = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "hf_trending": [],
        "github_trending": [],
    }

    print("  📊 抓取 Hugging Face Trending 模型...")
    snapshot["hf_trending"] = _fetch_hf_trending()

    print("  📊 抓取 GitHub Trending AI 项目...")
    snapshot["github_trending"] = _fetch_github_trending()

    print(f"  ✓ 快照完成：HF {len(snapshot['hf_trending'])} 个模型，GitHub {len(snapshot['github_trending'])} 个项目")
    return snapshot


def _fetch_hf_trending() -> list[dict]:
    """抓取 Hugging Face 趋势模型（官方 API，无需 Key）"""
    try:
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

        if not isinstance(models, list):
            print("  ⚠️ HF API 返回格式异常")
            return []

        result = []
        for m in models[:8]:
            model_id = m.get("id") or ""
            if not model_id:
                continue
            result.append({
                "name": model_id,
                "likes": m.get("likes") or 0,
                "downloads": m.get("downloads") or 0,
                "url": f"https://huggingface.co/{model_id}",
                "tags": (m.get("tags") or [])[:3],
            })
        return result
    except Exception as e:
        print(f"  ⚠️ HF Trending 抓取失败：{e}")
        return []


def _fetch_github_trending() -> list[dict]:
    """
    抓取 GitHub AI 相关热门项目。
    策略：优先查今日新建的 AI 项目；若 403 Rate Limit，降级查近期高星项目。
    """
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    url = "https://api.github.com/search/repositories"

    # 主查询：今日新建的 AI/LLM 相关项目（OR 逻辑，命中率更高）
    primary_params = {
        "q": f"(topic:llm OR topic:ai OR topic:llm-agent) created:>{yesterday}",
        "sort": "stars",
        "order": "desc",
        "per_page": 8,
    }

    # 降级查询：近期高星 AI 项目（不依赖 topic 标签）
    fallback_params = {
        "q": f"artificial-intelligence OR large-language-model pushed:>{yesterday} stars:>50",
        "sort": "stars",
        "order": "desc",
        "per_page": 8,
    }

    def _do_request(params: dict) -> list:
        try:
            resp = requests.get(url, params=params, headers=GITHUB_HEADERS, timeout=15)
            if resp.status_code == 403:
                return None  # 明确标记 rate limit
            resp.raise_for_status()
            return resp.json().get("items", [])
        except Exception as e:
            print(f"  ⚠️ GitHub 请求异常：{e}")
            return []

    items = _do_request(primary_params)

    # 403 时用降级查询，并打印提示
    if items is None:
        print("  ⚠️ GitHub API Rate Limit，切换降级查询...")
        items = _do_request(fallback_params)
        if items is None:
            print("  ⚠️ 降级查询也遭遇 Rate Limit，跳过 GitHub 快照")
            return []

    if not items:
        return []

    result = []
    for repo in items[:6]:
        html_url = repo.get("html_url") or ""
        full_name = repo.get("full_name") or ""
        if not full_name:
            continue
        result.append({
            "name": full_name,
            "desc": (repo.get("description") or "")[:100],
            "stars": repo.get("stargazers_count") or 0,
            "language": repo.get("language") or "—",
            "url": html_url,
            "topics": (repo.get("topics") or [])[:3],
        })
    return result
