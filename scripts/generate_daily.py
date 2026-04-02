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
      "title": "事件标题（必须是中文，如原标题是英文请翻译成中文）",
      "finding": "核心发现：用2-3句话说清楚发生了什么，面向普通读者，通俗易懂，避免专业术语堆砌",
      "key_data": ["关键数据或关键词1", "关键数据或关键词2", "关键数据或关键词3"],
      "judgment": "影响判断：这对 AI 行业/产品经理/开发者意味着什么，要有明确立场",
      "confidence": 4,
      "source": "来源名称",
      "url": "原文链接"
    }}
  ],
  "model_tech": [
    {{
      "source": "来源",
      "title": "标题（必须是中文）",
      "finding": "核心发现：2句话说清楚，通俗易懂",
      "key_data": ["关键数据1", "关键数据2"],
      "judgment": "影响判断（50字以内）",
      "confidence": 3,
      "url": "链接",
      "importance": 3
    }}
  ],
  "company_product": [
    {{
      "source": "来源",
      "title": "标题（必须是中文）",
      "finding": "核心发现：2句话说清楚，通俗易懂",
      "key_data": ["关键数据1", "关键数据2"],
      "judgment": "影响判断（50字以内）",
      "confidence": 3,
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
      "topic": "话题名称（中文）",
      "reason": "为什么值得深挖（50字以内）",
      "priority": "high"
    }}
  ],
  "summary_one_line": "今日一句话总结（20字以内，中文）"
}}

要求：
1. top_items 选 3-5 条，覆盖今日最重要的 AI 动态，不同类别都要有（模型/产品/研究/观点），不要只选同一类
2. model_tech 选 3-5 条；company_product 选 3-5 条；两者加起来至少 6 条
3. opinions 尽可能覆盖，有追踪人物发表观点必须收录，最多 3 条
4. 所有 title 字段必须是中文，英文标题需翻译
5. finding 要通俗易懂，像给聪明的非专业人士解释，不堆砌术语
6. key_data 提炼 2-4 个最关键的数字/词组，每个不超过 10 字，方便快速扫读
   ✅ 好的 key_data：「输入成本<0.8元/百万Token」「比 GPT-4o 快 3 倍」「开源 MIT 协议」
   ❌ 坏的 key_data：「大型强子对撞机（LHC）」「Coding plan」「多模态」「AI Agent」（太宽泛，无信息量）
7. judgment 必须有明确立场，说明"这对谁意味着什么、会带来什么变化"
8. confidence 为 1-5 的整数，代表信息可靠度：5=官方一手信息，4=权威媒体，3=可信来源，2=待验证，1=存疑
9. deep_dive_suggestions 只推荐真正值得花半天以上研究的话题
10. 如果某个分类今天没有值得关注的内容，返回空数组 []
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

    # 第一步：剥掉 AI 可能包裹的 markdown 代码块（```json ... ``` 或 ``` ... ```）
    raw_output = re.sub(r'^```(?:json)?\s*', '', raw_output.strip())
    raw_output = re.sub(r'\s*```\s*$', '', raw_output.strip())

    # 第二步：提取最外层 {...}（防止 AI 在 JSON 前后多输出说明文字）
    json_match = re.search(r'(\{[\s\S]*\})\s*$', raw_output.strip())
    if json_match:
        raw_output = json_match.group(1)

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


def _generate_hf_summary(hf_models: list[dict], config: dict) -> str:
    """用 AI 根据今日 HF 榜单生成一句话解读（≤40字）"""
    try:
        api_key = os.environ.get("AI_API_KEY")
        api_base = os.environ.get("AI_API_BASE", "https://api.deepseek.com")
        if not api_key:
            return ""
        client = OpenAI(api_key=api_key, base_url=api_base)

        lines = []
        for m in hf_models[:8]:
            label = m.get("label") or m.get("pipeline_tag") or ""
            short = m.get("short_name") or m.get("name", "").split("/")[-1]
            lines.append(f"- {short}（{label}）❤️{m.get('likes', 0)}")
        model_list = "\n".join(lines)

        resp = client.chat.completions.create(
            model=config["ai"]["model"],
            messages=[
                {"role": "system", "content": "你是 AI 行业观察者，擅长简洁总结趋势。"},
                {"role": "user", "content": (
                    f"以下是今日 Hugging Face 热门模型榜单：\n{model_list}\n\n"
                    "请用一句话（≤40字）总结今日榜单的整体趋势，要有观点，不要说废话。"
                    "直接输出总结文字，不加引号和标点。"
                )},
            ],
            max_tokens=80,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ⚠️ HF 一句话解读生成失败：{e}")
        return ""


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

    # Step 3.5: 给 snapshot 加 HF 一句话解读
    if snapshot.get("hf_trending"):
        print("\n💬 生成 HF 快照一句话解读...")
        snapshot["hf_summary"] = _generate_hf_summary(snapshot["hf_trending"], config)

    # Step 4: 保存双格式
    save_report(report_data, snapshot, config)
    print("\n🎉 日报生成完成！")


if __name__ == "__main__":
    main()
