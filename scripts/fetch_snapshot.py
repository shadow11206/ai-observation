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
- OpenRouter 使用数据集 API（与官方页面口径一致）；
  permaslug 日期后缀清理兼容 :variant 结尾（nemotron-...-20260604:free）
"""

import json
import os
import re as _re
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 北京时区（UTC+8），确保 snapshot.date 与日报日期一致
_BJT = timezone(timedelta(hours=8))


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Observation-Bot/1.0)",
    "Accept": "application/json",
}

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
    使用 OpenRouter 官方数据集 API（需 API Key），与官方排行榜页面口径一致。

    API: https://openrouter.ai/api/v1/datasets/rankings-daily
    返回最近 ~30 天的每日模型 token 量（不含调用次数）。
    按清理后的 slug 聚合，取最新一天的总 token 量 Top 10，自行计算日环比变化。

    注意：页面调用的 /api/frontend/v1/rankings/models 接口字段简单相加
    （prompt+completion）比页面显示值大约 7 倍，不能直接使用。
    """
    from collections import defaultdict

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("  ⚠️ OPENROUTER_API_KEY 未设置，跳过 OpenRouter 快照")
        return []

    _OR_API = "https://openrouter.ai/api/v1/datasets/rankings-daily"
    _OR_HEADERS = {**HEADERS, "Authorization": f"Bearer {api_key}"}

    try:
        resp = requests.get(_OR_API, headers=_OR_HEADERS, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        print(f"  ⚠️ OpenRouter 排行榜 API 请求失败：{e}")
        return []

    rows = payload.get("data", [])
    if not rows:
        print("  ⚠️ OpenRouter API 返回空数据")
        return []

    # 按 (date, clean_slug) 聚合 token 量，排除 "other" 汇总行
    day_data = defaultdict(lambda: defaultdict(int))
    for row in rows:
        raw_slug = row.get("model_permaslug", "")
        if not raw_slug or raw_slug == "other":
            continue
        date = row.get("date", "")
        tokens = int(row.get("total_tokens", "0"))
        slug = _strip_date_suffix(raw_slug)
        day_data[date][slug] += tokens

    available_dates = sorted(day_data.keys(), reverse=True)
    if not available_dates:
        print("  ⚠️ OpenRouter API 返回数据无有效日期")
        return []

    target_date = available_dates[0]
    prev_date = available_dates[1] if len(available_dates) > 1 else None

    target_data = day_data[target_date]
    prev_data = day_data[prev_date] if prev_date else {}

    sorted_models = sorted(target_data.items(), key=lambda x: x[1], reverse=True)[:10]

    _MODEL_NAMES = _load_model_name_map()

    result = []
    for i, (clean_slug, total_tokens) in enumerate(sorted_models, 1):
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

        prev_tokens = prev_data.get(clean_slug, 0)
        change = round((total_tokens - prev_tokens) / prev_tokens * 100, 1) if prev_tokens > 0 else 0

        result.append({
            "rank": i,
            "slug": clean_slug,
            "name": display_name,
            "org": org,
            "total_tokens": total_tokens,
            "total_tokens_str": token_str,
            "api_calls": 0,   # 官方数据集 API 不提供调用次数
            "change": change,
            "url": f"https://openrouter.ai/{clean_slug}",
        })

    print(f"  ✓ OpenRouter 排行榜：{target_date} Top {len(result)} 个模型")
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
    """去掉 permaslug 末尾的日期后缀，保留 :variant（与官方页面一致，免费版单独显示）：
    deepseek-v4-flash-20260423 → deepseek-v4-flash
    nemotron-...-20260604:free → nemotron-...:free"""
    import re as _re
    return _re.sub(r"-\d{8}(?=:|$)", "", slug)


def _slug_to_display(permaslug: str) -> str:
    """fallback：从 permaslug 生成可读名称"""
    import re as _re
    # "deepseek/deepseek-v4-flash-20260423" → "deepseek-v4-flash"
    last = permaslug.split("/")[-1] if "/" in permaslug else permaslug
    last = _re.sub(r"-\d{8}(?=:|$)", "", last)  # 去掉日期后缀
    last = last.replace(":free", "（免费）").replace(":extended", "（扩展）").replace(":", " ")
    last = last.replace("-", " ").replace("_", " ")
    # 简单 title case
    return " ".join(w[0].upper() + w[1:] if w else w for w in last.split())


def _fetch_github_trending() -> list[dict]:
    """
    抓取 GitHub Trending 页面 (https://github.com/trending) 前 5 个项目。
    直接解析 HTML，不依赖 GitHub API，避免 Rate Limit。
    """
    try:
        resp = requests.get("https://github.com/trending", headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI-Observation-Bot/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        }, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ⚠️ GitHub Trending 抓取失败：{e}")
        return []

    text = resp.text
    articles = _re.findall(r'<article\s+class="Box-row"[^>]*>(.*?)</article>', text, _re.DOTALL)
    if not articles:
        print("  ⚠️ GitHub Trending 页面解析失败：未找到项目")
        return []

    result = []
    for art in articles[:5]:
        # Repo 名称：跳过 login/sponsors 等路径，取第一个 /org/repo
        hrefs = _re.findall(r'href="(/[^"]+)"', art)
        repo_href = ""
        for hf in hrefs:
            first = hf.lstrip("/")
            if first.split("/")[0] in ("login", "sponsors", "settings", "features", "trending"):
                continue
            if "/" in first and len(first.split("/")) == 2:
                repo_href = hf
                break
        if not repo_href:
            continue
        name = repo_href.strip("/")

        # 描述
        desc_match = _re.search(r'<p\s+class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', art, _re.DOTALL)
        desc = _re.sub(r"<[^>]+>", "", desc_match.group(1)).strip() if desc_match else ""

        # 语言
        lang_match = _re.search(r'itemprop="programmingLanguage"[^>]*>([^<]+)', art)
        language = lang_match.group(1).strip() if lang_match else ""

        # 今日新增星标
        today_match = _re.search(r"(\d[\d,]*)\s+stars?\s+today", art)
        stars_today = int(today_match.group(1).replace(",", "")) if today_match else 0

        # 总星标 + forks（去掉 SVG 后取数字）
        clean = _re.sub(r"<svg[^>]*>.*?</svg>", "", art, flags=_re.DOTALL)
        nums = [int(n.replace(",", "")) for n in _re.findall(r"<a[^>]*>\s*([\d,]+)\s*</a>", clean)]
        stars_total = nums[-2] if len(nums) >= 2 else 0
        forks = nums[-1] if len(nums) >= 1 else 0

        result.append({
            "name": name,
            "desc": desc[:100],
            "stars": stars_total,
            "stars_today": stars_today,
            "forks": forks,
            "language": language or "—",
            "url": f"https://github.com/{name}",
        })

    print(f"  ✓ GitHub Trending：成功解析 {len(result)} 个项目")
    return result
