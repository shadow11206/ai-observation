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
import requests
from datetime import datetime, timedelta
from pathlib import Path


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Observation-Bot/1.0)",
    "Accept": "application/json",
}

GITHUB_HEADERS = {**HEADERS, "Accept": "application/vnd.github.v3+json"}

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
        "date": datetime.now().strftime("%Y-%m-%d"),
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
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
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
    数据来源：https://openrouter.ai/rankings?view=day
    通过 Next.js RSC 流接口获取，无需 API Key，每天抓一次。
    """
    import re as _re
    import random
    import string
    from collections import defaultdict

    try:
        rsc_token = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        url = f"https://openrouter.ai/rankings?view=day&_rsc={rsc_token}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/x-component",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "RSC": "1",
            "Next-Router-State-Tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22rankings%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
            "Referer": "https://openrouter.ai/",
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        raw = resp.text

        # 找到含 rankingData 的 RSC 行
        ranking_line = None
        for line in raw.split("\n"):
            if '"rankingData"' in line and "model_permaslug" in line:
                ranking_line = line
                break

        if not ranking_line:
            print("  ⚠️ OpenRouter：未找到 rankingData 行")
            return []

        # 去掉 RSC 行前缀（如 '25:' 或 '2a:'）
        m = _re.match(r"^[0-9a-f]+:(.*)", ranking_line, _re.DOTALL)
        json_str = m.group(1) if m else ranking_line

        # 逐字符提取 rankingData 数组
        arr_start = json_str.find('"rankingData":')
        if arr_start == -1:
            return []
        bracket_start = json_str.find("[", arr_start)
        if bracket_start == -1:
            return []

        depth = 0
        end = bracket_start
        for i, c in enumerate(json_str[bracket_start:]):
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    end = bracket_start + i + 1
                    break

        ranking_data = json.loads(json_str[bracket_start:end])

        # 按模型聚合
        model_agg = defaultdict(lambda: {"total_tokens": 0, "count": 0, "change": 0.0})
        for row in ranking_data:
            slug = row.get("model_permaslug") or ""
            if not slug:
                continue
            prompt = row.get("total_prompt_tokens") or 0
            completion = row.get("total_completion_tokens") or 0
            model_agg[slug]["total_tokens"] += prompt + completion
            model_agg[slug]["count"] += row.get("count") or 0
            model_agg[slug]["change"] = row.get("change") or 0.0

        top10 = sorted(model_agg.items(), key=lambda x: x[1]["total_tokens"], reverse=True)[:10]

        result = []
        for rank, (slug, stats) in enumerate(top10, 1):
            t = stats["total_tokens"]
            if t >= 1e12:
                t_str = f"{t / 1e12:.1f}T"
            elif t >= 1e9:
                t_str = f"{t / 1e9:.0f}B"
            elif t >= 1e6:
                t_str = f"{t / 1e6:.0f}M"
            else:
                t_str = str(t)

            org = slug.split("/")[0] if "/" in slug else ""
            model_name = slug.split("/")[-1] if "/" in slug else slug
            import re as _re2
            display_name = _re2.sub(r"-\d{8}$", "", model_name)
            display_name = display_name.replace(":free", " (free)").replace(":", " ")

            result.append({
                "rank": rank,
                "slug": slug,
                "name": display_name,
                "org": org,
                "total_tokens": t,
                "total_tokens_str": t_str,
                "calls": stats["count"],
                "change": round(stats["change"] * 100, 1),
                "url": f"https://openrouter.ai/models/{slug}",
            })

        return result

    except Exception as e:
        print(f"  ⚠️ OpenRouter 排行榜抓取失败：{e}")
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
