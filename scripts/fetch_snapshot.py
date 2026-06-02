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
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 北京时区（UTC+8），确保 snapshot.date 与日报日期一致
_BJT = timezone(timedelta(hours=8))


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
    数据来源：https://openrouter.ai/rankings?view=day
    页面已改为客户端渲染（2026年4月底起），需使用 Playwright 浏览器抓取。
    """
    import re as _re

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ⚠️ Playwright 未安装，跳过 OpenRouter 排行榜")
        print("     安装：pip install playwright && playwright install chromium")
        return []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = browser.new_page()
            page.goto(
                "https://openrouter.ai/rankings?view=day",
                wait_until="networkidle",
                timeout=30000,
            )
            page.wait_for_selector(
                '[data-testid="model-rankings-leaderboard-row"]', timeout=15000
            )

            rows_raw = page.evaluate("""() => {
                const rows = document.querySelectorAll(
                    '[data-testid="model-rankings-leaderboard-row"]'
                );
                return Array.from(rows).map(row => {
                    const link = row.querySelector('a');
                    // 查找包含 % 的 span 元素及内部 SVG 的 class
                    // SVG class text-red-* = 下跌，text-green-* = 上涨
                    const spans = row.querySelectorAll('span');
                    let changeText = '';
                    let isDecline = false;
                    for (const s of spans) {
                        if (s.textContent && s.textContent.includes('%')) {
                            changeText = s.textContent.trim();
                            const svg = s.querySelector('svg');
                            if (svg) {
                                const cls = svg.getAttribute('class') || '';
                                isDecline = cls.includes('text-red');
                            }
                            break;
                        }
                    }
                    return {
                        href: link ? link.getAttribute('href') : '',
                        text: row.textContent || '',
                        changeText: changeText,
                        isDecline: isDecline,
                    };
                });
            }""")

            browser.close()

        result = []
        for row_data in rows_raw:
            text = row_data.get("text", "")
            href = row_data.get("href", "")
            change_text = row_data.get("changeText", "")
            is_decline = row_data.get("isDecline", False)
            # 示例文本： "1. Hy3 previewby tencent483B tokens3%"
            m = _re.match(
                r"^(\d+)\.\s*(.+?)by\s+([a-zA-Z][a-zA-Z-]*)\s*"
                r"([\d.]+)\s*(B|M|T|K)?\s*tokens",
                text,
            )
            if not m:
                continue
            rank, name, org, amount, unit = m.groups()

            # 从 changeText 提取变化百分比，用 SVG class 判断涨跌
            change = 0
            if change_text:
                digits = _re.search(r"[\d.]+", change_text)
                if digits:
                    val = float(digits.group())
                    change = -val if is_decline else val

            multiplier = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}
            total_tokens = int(float(amount) * multiplier.get(unit, 1e9))

            slug = href.lstrip("/")
            display_name = _re.sub(r"-\d{8}$", "", name.strip())
            display_name = display_name.replace(":free", " (free)").replace(":", " ")

            result.append({
                "rank": int(rank),
                "slug": slug,
                "name": display_name,
                "org": org.strip(),
                "total_tokens": total_tokens,
                "total_tokens_str": amount + (unit or "B"),
                "change": change,
                "url": f"https://openrouter.ai/{slug}",
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
    yesterday = (datetime.now(_BJT) - timedelta(days=1)).strftime("%Y-%m-%d")
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
