"""
日报生成主脚本
=============
架构设计：信息获取层（fetch_rss.py）与内容生成层（本文件）分离

输出格式：.md（人类可读）+ .json（前端渲染）双格式同步输出
  - .md  → 01-daily-reports/YYYY-MM/YYYY-MM-DD.md
  - .json → 01-daily-reports/YYYY-MM/YYYY-MM-DD.json

运行方式：
  python scripts/generate_daily.py

所需环境变量：
  AI_API_KEY   - AI 模型 API Key
  AI_API_BASE  - API Base URL（如 https://api.deepseek.com）
"""

import json
import os
import re
import sys
import yaml
from datetime import datetime
from pathlib import Path

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.fetch_rss import fetch_info
from scripts.fetch_snapshot import fetch_snapshot


def load_config() -> dict:
    with open("scripts/config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt() -> str:
    with open("scripts/prompts/daily_report.txt", "r", encoding="utf-8") as f:
        return f.read()


def load_tracking_registry() -> str:
    parts = []
    for fname in ["people/index.md", "companies/index.md"]:
        path = Path("03-tracking-registry") / fname
        if path.exists():
            parts.append(f"=== {fname} ===\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


def generate_report_with_ai(raw_info: list[dict], config: dict) -> dict:
    """
    调用 AI 生成日报，返回结构化 dict（同时用于 .json 和 .md 渲染）
    """
    api_key = os.environ.get("AI_API_KEY")
    api_base = os.environ.get("AI_API_BASE", "https://api.deepseek.com")

    if not api_key:
        raise ValueError("未找到 AI_API_KEY 环境变量，请在 GitHub Secrets 中配置")

    client = OpenAI(api_key=api_key, base_url=api_base)

    today = datetime.now().strftime("%Y-%m-%d")
    system_prompt = load_prompt()
    tracking_registry = load_tracking_registry()
    info_text = _format_info_for_prompt(raw_info)

    user_message = f"""今天是 {today}。

## 追踪体系（用于判断重要程度）
{tracking_registry}

## 今日抓取的信息（来自 RSS 订阅）
{info_text}

请基于以上信息，严格按照以下 JSON 结构输出今天的 AI 日报（只输出 JSON，不要有其他文字）：

{{
  "date": "{today}",
  "top_items": [
    {{
      "rank": 1,
      "title": "事件标题",
      "judgment": "一句话判断：这意味着什么",
      "source": "来源名称",
      "url": "原文链接",
      "tags": ["模型动态"]
    }}
  ],
  "model_tech": [
    {{
      "source": "来源",
      "title": "标题",
      "summary": "100字以内摘要",
      "url": "链接",
      "importance": 3
    }}
  ],
  "company_product": [
    {{
      "source": "来源",
      "title": "标题",
      "summary": "100字以内摘要",
      "url": "链接",
      "importance": 2
    }}
  ],
  "opinions": [
    {{
      "person": "人物名",
      "level": "L1",
      "quote": "核心观点（100字以内）",
      "source": "来源链接"
    }}
  ],
  "deep_dive_suggestions": [
    {{
      "topic": "话题名称",
      "reason": "为什么值得深挖（50字以内）",
      "priority": "high"
    }}
  ],
  "summary_one_line": "今日一句话总结（20字以内）"
}}

要求：
1. top_items 选 1-3 条，只选真正重要的，不凑数
2. 每条 judgment 必须有观点，说明"这意味着什么"
3. deep_dive_suggestions 只推荐真正值得花半天以上研究的话题
4. 如果某个分类今天没有值得关注的内容，返回空数组 []
5. tags 从以下选择：模型动态、产品发布、技术突破、商业化、开源、观点解读、行业趋势
"""

    response = client.chat.completions.create(
        model=config["ai"]["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=config["ai"]["max_tokens"],
        temperature=config["ai"]["temperature"],
    )

    raw_output = response.choices[0].message.content.strip()

    # 提取 JSON（防止 AI 多输出了 markdown 代码块）
    json_match = re.search(r'\{[\s\S]*\}', raw_output)
    if json_match:
        raw_output = json_match.group(0)

    try:
        report_data = json.loads(raw_output)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON 解析失败，尝试宽松解析：{e}")
        # 降级：返回包含原始内容的基础结构
        report_data = {
            "date": today,
            "top_items": [],
            "model_tech": [],
            "company_product": [],
            "opinions": [],
            "deep_dive_suggestions": [],
            "summary_one_line": "今日日报生成完成",
            "raw_content": raw_output,
        }

    return report_data


def _format_info_for_prompt(items: list[dict]) -> str:
    lines = []
    for i, item in enumerate(items, 1):
        lines.append(
            f"{i}. [{item['source']}] {item['title']}\n"
            f"   链接：{item['url']}\n"
            f"   时间：{item['published']}\n"
            f"   摘要：{item['summary'][:200]}...\n"
        )
    return "\n".join(lines)


def save_report(report_data: dict, snapshot: dict, config: dict) -> tuple[Path, Path]:
    """保存 .md 和 .json 两份文件"""
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")
    output_dir = Path(config["report"]["output_dir"]) / month
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- 合并快照数据到 report_data ---
    report_data["snapshot"] = snapshot

    # --- 保存 .json ---
    json_path = output_dir / f"{today}.json"
    json_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ JSON 已保存：{json_path}")

    # --- 生成 .md（人类可读版） ---
    md_content = _render_md(report_data)
    md_path = output_dir / f"{today}.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"✅ MD  已保存：{md_path}")

    return md_path, json_path


def _render_md(data: dict) -> str:
    """将 report_data dict 渲染为 Markdown 格式"""
    lines = [f"# AI 日报 - {data['date']}\n"]

    if data.get("summary_one_line"):
        lines.append(f"> {data['summary_one_line']}\n")

    # 今日最重要
    lines.append("## 📌 今日最重要\n")
    for item in data.get("top_items", []):
        lines.append(f"**{item.get('rank', '')}. {item.get('title', '')}**")
        lines.append(f"> {item.get('judgment', '')}")
        if item.get("url"):
            lines.append(f"> 来源：[{item.get('source', '')}]({item.get('url', '')})")
        lines.append("")

    # 模型/技术动态
    if data.get("model_tech"):
        lines.append("## 🔬 模型 / 技术动态\n")
        for item in data["model_tech"]:
            lines.append(f"- **[{item.get('source', '')}]** [{item.get('title', '')}]({item.get('url', '')})")
            lines.append(f"  {item.get('summary', '')}\n")

    # 公司/产品动态
    if data.get("company_product"):
        lines.append("## 🏢 公司 / 产品动态\n")
        for item in data["company_product"]:
            lines.append(f"- **[{item.get('source', '')}]** [{item.get('title', '')}]({item.get('url', '')})")
            lines.append(f"  {item.get('summary', '')}\n")

    # 观点
    if data.get("opinions"):
        lines.append("## 💡 追踪人物观点\n")
        for op in data["opinions"]:
            lines.append(f"- **{op.get('person', '')}** ({op.get('level', '')})：{op.get('quote', '')}")
            if op.get("source"):
                lines.append(f"  [来源]({op.get('source', '')})")
            lines.append("")

    # 值得深挖
    if data.get("deep_dive_suggestions"):
        lines.append("## 🔭 值得深挖？\n")
        for s in data["deep_dive_suggestions"]:
            lines.append(f"- [ ] **{s.get('topic', '')}** — {s.get('reason', '')}")
        lines.append("")

    # 数据快照
    snapshot = data.get("snapshot", {})
    if snapshot.get("hf_trending") or snapshot.get("github_trending"):
        lines.append("## ⚡ 今日数据快照\n")
        if snapshot.get("hf_trending"):
            lines.append("### Hugging Face Trending\n")
            for m in snapshot["hf_trending"][:5]:
                lines.append(f"- [{m.get('name', '')}]({m.get('url', '')}) — ❤️ {m.get('likes', 0)}")
        if snapshot.get("github_trending"):
            lines.append("\n### GitHub Trending AI\n")
            for r in snapshot["github_trending"][:5]:
                lines.append(f"- [{r.get('name', '')}]({r.get('url', '')}) — ⭐ {r.get('stars', 0)} · {r.get('language', '')}")
                if r.get("desc"):
                    lines.append(f"  {r.get('desc', '')}")

    lines.append(f"\n---\n*本日报由 AI 自动生成 · {data['date']}*")
    return "\n".join(lines)


def main():
    print("=== AI Observation 日报生成 ===\n")
    config = load_config()

    # Step 1: 获取 RSS 信息
    print("📡 正在抓取 RSS 信息源...")
    raw_info = fetch_info()
    if not raw_info:
        print("⚠️  今日没有抓取到有效信息，跳过日报生成")
        return

    # Step 2: 抓取数据快照
    print("\n📊 正在抓取今日数据快照...")
    snapshot = fetch_snapshot()

    # Step 3: AI 生成结构化日报
    print("\n🤖 正在调用 AI 生成日报...")
    report_data = generate_report_with_ai(raw_info, config)

    # Step 4: 保存双格式
    save_report(report_data, snapshot, config)
    print("\n🎉 日报生成完成！")


if __name__ == "__main__":
    main()
