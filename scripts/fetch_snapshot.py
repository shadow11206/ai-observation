"""
信息获取层 - 今日数据快照
==========================
抓取 Hugging Face 热门模型 + GitHub Trending AI 项目
v2.0 新增：
- HF 每个模型补充 pipeline_tag + card_desc（model card 简介）
- 与昨日快照对比，标记趋势（new/up/same）
- GitHub 数据不稳定，保留但前端只在有数据时显示

修复记录：
- 403 fallback 后正确检查新响应状态码
- GitHub 查询改为 OR 逻辑，避免 topic 同时命中率极低
- 独立 timeout，两个请求互不影响
"""

import json
import os
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 北京时区（UTC+8），确保 snapshot.date 与日报日期一致
_BJT = timezone(timedelta(hours=8))


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Observation-Bot/1.0)",
    "Accept": "application/json",
}

_github_headers = {**HEADERS, "Accept": "application/vnd.github.v3+json"}
_github_token = os.environ.get("GITHUB_TOKEN")
if _github_token:
    _github_headers["Authorization"] = f"Bearer {_github_token}"

GITHUB_HEADERS = _github_headers

# pipeline_tag → 人类可读中文说明
PIPELINE_LABEL = {
    "text-generation": "文本生成",
    "text2text-generation": "文本生成",
    "image-text-to-text": "多模态理解",
    "image-to-text": "图片描述",
    "text-to-image": "文生图",
    "text-to-video": "文生视频",
    "image-to-video": "图生视频",
    "text-to-speech": "文字转语音",
    "automatic-speech-recognition": "语音识别",
    "feature-extraction": "向量嵌入",
    "sentence-similarity": "语义相似度",
    "token-classification": "命名实体识别",
    "translation": "翻译",
    "summarization": "摘要生成",
    "question-answering": "问答",
    "fill-mask": "完形填空",
    "image-classification": "图像分类",
    "object-detection": "目标检测",
    "depth-estimation": "深度估计",
    "video-classification": "视频分类",
    "reinforcement-learning": "强化学习",
}


def fetch_snapshot() -> dict:
    """主入口：获取今日数据快照，三个源各自独立，互不影响"""
    snapshot = {
        "date": datetime.now(_BJT).strftime("%Y-%m-%d"),
        "hf_trending": [],
        "github_trending": [],
        "openrouter_ranking": [],
    }

    print("  📊 抓取 Hugging Face Trending 模型...")
    raw_hf = _fetch_hf_trending()
    yesterday_map = _load_yesterday_hf_names()
    snapshot["hf_trending"] = _enrich_with_trend(raw_hf, yesterday_map)

    print("  📊 抓取 GitHub Trending AI 项目...")
    snapshot["github_trending"] = _fetch_github_trending()

    print("  📊 抓取 OpenRouter 模型调用排行榜...")
    snapshot["openrouter_ranking"] = _fetch_openrouter_ranking()

    print(
        f"  ✓ 快照完成：HF {len(snapshot['hf_trending'])} 个模型，"
        f"GitHub {len(snapshot['github_trending'])} 个项目，"
        f"OpenRouter Top {len(snapshot['openrouter_ranking'])} 模型"
    )
    return snapshot


def _load_yesterday_hf_names() -> set:
    """加载昨日 HF 榜单的模型名集合，用于趋势对比"""
    yesterday = (datetime.now(_BJT) - timedelta(days=1)).strftime("%Y-%m-%d")
    month = yesterday[:7]
    json_path = Path(f"01-daily-reports/{month}/{yesterday}.json")
    if not json_path.exists():
        return set()
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        hf = data.get("snapshot", {}).get("hf_trending", [])
        return {m.get("name", "") for m in hf}
    except Exception:
        return set()


def _enrich_with_trend(models: list[dict], yesterday_names: set) -> list[dict]:
    """给每个模型标记趋势：new（首次上榜）、same（连续上榜）"""
    for m in models:
        if m["name"] in yesterday_names:
            m["trend"] = "same"
        else:
            m["trend"] = "new"
    return models


def _fetch_hf_trending() -> list[dict]:
    """抓取 Hugging Face 趋势模型（官方 API，无需 Key），补充 pipeline_tag + 简介"""
    try:
        url = "https://huggingface.co/api/models"
        params = {
            "sort": "likes7d",
            "direction": "-1",
            "limit": 8,
            "full": "true",   # 拉 full 字段，含 pipeline_tag 和 cardData
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

            pipeline_tag = m.get("pipeline_tag") or ""
            label = PIPELINE_LABEL.get(pipeline_tag, pipeline_tag.replace("-", " ").title() if pipeline_tag else "")

            # 尝试从 cardData 拿简介
            card_data = m.get("cardData") or {}
            card_desc = ""
            if isinstance(card_data, dict):
                card_desc = (card_data.get("model_description") or card_data.get("description") or "")[:60]

            # 从 model_id 提取简短可读名（去掉 org 前缀）
            short_name = model_id.split("/")[-1] if "/" in model_id else model_id

            result.append({
                "name": model_id,
                "short_name": short_name,
                "likes": m.get("likes") or 0,
                "downloads": m.get("downloads") or 0,
                "url": f"https://huggingface.co/{model_id}",
                "tags": (m.get("tags") or [])[:3],
                "pipeline_tag": pipeline_tag,
                "label": label,           # 中文类型说明
                "card_desc": card_desc,   # model card 简介（可能为空）
            })
        return result
    except Exception as e:
        print(f"  ⚠️ HF Trending 抓取失败：{e}")
        return []


def _fetch_openrouter_ranking() -> list[dict]:
    """
    抓取 OpenRouter 当日模型调用排行榜 Top 10。
    直接调用 OpenRouter 内部 API，无需浏览器，数据准确且稳定。

    API: https://openrouter.ai/api/frontend/rankings/models?view=day
    返回所有模型（含 variant）的每日 token 量 + 调用次数 + 涨跌百分比。
    按 model_permaslug 聚合（合并 standard/free 等 variant），取总 token 量 Top 10。
    """
    from collections import defaultdict

    _OR_API = "https://openrouter.ai/api/frontend/rankings/models?view=day"

    try:
        resp = requests.get(_OR_API, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        print(f"  ⚠️ OpenRouter 排行榜 API 请求失败：{e}")
        return []

    models = payload.get("data", [])
    if not models:
        print("  ⚠️ OpenRouter API 返回空数据")
        return []

    # 按 model_permaslug 聚合（同一模型可能有 standard / free 等多个 variant）
    # 先去掉日期后缀再聚合，确保不同日期版本的同一模型族合并统计
    agg = defaultdict(lambda: {"total_tokens": 0, "count": 0, "slug": "", "change": None})

    for m in models:
        raw_slug = m.get("model_permaslug", "")
        if not raw_slug:
            continue
        slug = _strip_date_suffix(raw_slug)
        agg[slug]["total_tokens"] += m.get("total_completion_tokens", 0) + m.get("total_prompt_tokens", 0)
        agg[slug]["count"] += m.get("count", 0)
        agg[slug]["slug"] = slug
        if agg[slug]["change"] is None and m.get("change") is not None:
            agg[slug]["change"] = m["change"]

    # 按总 token 量降序，取 Top 10
    sorted_models = sorted(agg.items(), key=lambda x: x[1]["total_tokens"], reverse=True)[:10]

    _MODEL_NAMES = _load_model_name_map()

    result = []
    for i, (clean_slug, info) in enumerate(sorted_models, 1):
        total_tokens = info["total_tokens"]

        if total_tokens >= 1e12:
            token_str = f"{total_tokens / 1e12:.1f}T"
        elif total_tokens >= 1e9:
            token_str = f"{total_tokens / 1e9:.0f}B"
        elif total_tokens >= 1e6:
            token_str = f"{total_tokens / 1e6:.0f}M"
        else:
            token_str = str(total_tokens)

        org = clean_slug.split("/")[0] if "/" in clean_slug else ""
        display_name = _MODEL_NAMES.get(clean_slug, _slug_to_display(clean_slug))
        change = round(info["change"] * 100, 1) if info["change"] is not None else 0

        result.append({
            "rank": i,
            "slug": clean_slug,
            "name": display_name,
            "org": org,
            "total_tokens": total_tokens,
            "total_tokens_str": token_str,
            "api_calls": info["count"],
            "change": change,
            "url": f"https://openrouter.ai/{clean_slug}",
        })

    print(f"  ✓ OpenRouter 排行榜：成功解析 {len(result)} 个模型")
    return result


# 已知模型 slug → 显示名称映射（从 /api/v1/models 提取，首次运行时自动填充）
_MODEL_NAME_CACHE = None


def _load_model_name_map() -> dict[str, str]:
    """加载所有模型的 slug → 可读名称映射（惰性加载，只请求一次）"""
    global _MODEL_NAME_CACHE
    if _MODEL_NAME_CACHE is not None:
        return _MODEL_NAME_CACHE

    _MODEL_NAME_CACHE = {}
    try:
        resp = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        for m in payload.get("data", []):
            model_id = m.get("id", "")
            raw_name = m.get("name", "")
            if not model_id or not raw_name:
                continue
            # "Anthropic: Claude Opus 4.7" → "Claude Opus 4.7"
            clean = raw_name.split(":", 1)[-1].strip()
            _MODEL_NAME_CACHE[model_id] = clean
            # 也注册去掉 :free/:extended 等 variant 后缀的版本
            base_id = model_id.split(":")[0]
            if base_id != model_id and base_id not in _MODEL_NAME_CACHE:
                _MODEL_NAME_CACHE[base_id] = clean
        print(f"  ✓ 已加载 {len(_MODEL_NAME_CACHE)} 个模型名称映射")
    except Exception as e:
        print(f"  ⚠️ 模型名称映射加载失败（将使用 slug 作为名称）：{e}")

    return _MODEL_NAME_CACHE


def _strip_date_suffix(slug: str) -> str:
    """去掉 permaslug 末尾的日期后缀：deepseek-v4-flash-20260423 → deepseek-v4-flash"""
    import re as _re
    return _re.sub(r"-\d{8}$", "", slug)


def _slug_to_display(permaslug: str) -> str:
    """fallback：从 permaslug 生成可读名称"""
    import re as _re
    # "deepseek/deepseek-v4-flash-20260423" → "deepseek-v4-flash"
    last = permaslug.split("/")[-1] if "/" in permaslug else permaslug
    last = _re.sub(r"-\d{8}$", "", last)  # 去掉日期后缀
    last = last.replace("-", " ").replace("_", " ")
    # 简单 title case
    return " ".join(w[0].upper() + w[1:] if w else w for w in last.split())


def _fetch_github_trending() -> list[dict]:
    """
    抓取 GitHub AI 相关热门项目。
    策略：主查询按 topic + 近期推送筛选活跃 AI 项目；
          结果为空或遭限流时降级为关键词搜索（更高星数门槛降噪）。
    """
    three_days_ago = (datetime.now(_BJT) - timedelta(days=3)).strftime("%Y-%m-%d")
    url = "https://api.github.com/search/repositories"

    # 主查询：有 AI topic 标签、近3天有推送、星数 > 50
    # GitHub topic qualifier 用逗号分隔表示 OR，不支持 OR 关键字
    primary_params = {
        "q": (
            "topic:ai,llm,machine-learning,deep-learning,llm-agent"
            f" pushed:>={three_days_ago} stars:>50"
        ),
        "sort": "stars",
        "order": "desc",
        "per_page": 8,
    }

    # 降级查询：关键词搜索（搜名称/描述），提高星数门槛到 200 以减少噪音
    fallback_params = {
        "q": (
            f'(ai OR llm OR "machine learning" OR "deep learning")'
            f" pushed:>={three_days_ago} stars:>200"
        ),
        "sort": "stars",
        "order": "desc",
        "per_page": 8,
    }

    def _do_request(params: dict) -> list | None:
        try:
            resp = requests.get(url, params=params, headers=GITHUB_HEADERS, timeout=15)
            if resp.status_code == 403:
                return None
            resp.raise_for_status()
            return resp.json().get("items", [])
        except Exception as e:
            print(f"  ⚠️ GitHub 请求异常：{e}")
            return []

    items = _do_request(primary_params)

    # 403 或主查询无结果时，尝试降级查询
    if items is None:
        print("  ⚠️ GitHub API Rate Limit，切换降级查询...")
    elif not items:
        print("  ⚠️ 主查询无结果，尝试降级查询...")

    if items is None or (isinstance(items, list) and not items):
        items = _do_request(fallback_params)
        if items is None:
            print("  ⚠️ 降级查询也遭遇 Rate Limit，跳过 GitHub 快照")
            return []
        if isinstance(items, list) and not items:
            print("  ⚠️ GitHub 查询无结果（已尝试主查询和降级查询）")
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
