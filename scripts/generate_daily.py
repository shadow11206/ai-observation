"""
日报生成主脚本
=============
架构设计：信息获取层（fetch_rss.py）与内容生成层（本文件）分离
  - 升级信息源：只改 fetch_rss.py 或替换为 fetch_api.py / fetch_browser.py
  - 生成逻辑、存储逻辑、评估逻辑：本文件不需要改动

运行方式：
  python scripts/generate_daily.py

所需环境变量：
  AI_API_KEY   - AI 模型 API Key
  AI_API_BASE  - API Base URL（如 https://api.deepseek.com）
"""

import os
import sys
import yaml
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# 将项目根目录加入路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.fetch_rss import fetch_info


def load_config() -> dict:
    with open("scripts/config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt() -> str:
    prompt_path = Path("scripts/prompts/daily_report.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def load_template() -> str:
    with open("templates/daily-report-template.md", "r", encoding="utf-8") as f:
        return f.read()


def load_tracking_registry() -> str:
    """加载追踪体系作为 AI 上下文"""
    registry_parts = []
    for fname in ["people/index.md", "companies/index.md", "sources/index.md"]:
        path = Path("03-tracking-registry") / fname
        if path.exists():
            registry_parts.append(f"=== {fname} ===\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(registry_parts)


def generate_report_with_ai(raw_info: list[dict], config: dict) -> str:
    """调用 AI API 生成日报"""
    api_key = os.environ.get("AI_API_KEY")
    api_base = os.environ.get("AI_API_BASE", "https://api.deepseek.com")

    if not api_key:
        raise ValueError("未找到 AI_API_KEY 环境变量，请在 GitHub Secrets 中配置")

    client = OpenAI(api_key=api_key, base_url=api_base)

    today = datetime.now().strftime("%Y-%m-%d")
    system_prompt = load_prompt()
    tracking_registry = load_tracking_registry()
    template = load_template()

    # 将 raw_info 格式化为可读文本
    info_text = _format_info_for_prompt(raw_info)

    user_message = f"""今天是 {today}。

## 追踪体系（用于判断重要程度）
{tracking_registry}

## 今日抓取的信息（来自 RSS 订阅）
{info_text}

## 日报模板（请严格按此格式输出）
{template}

请基于以上信息，生成今天的 AI 日报。要求：
1. 用中文输出
2. "今日最重要"板块选出真正重要的 1-3 条，并给出你的一句话判断
3. "值得深挖"板块：评估哪些话题值得触发深度调研，说明理由
4. 信息按重要程度排序，不重要的信息可以跳过
5. 日期替换为 {today}
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

    return response.choices[0].message.content


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


def save_report(content: str, config: dict) -> Path:
    """将日报保存到对应目录"""
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    output_dir = Path(config["report"]["output_dir"]) / month
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{today}.md"
    output_path.write_text(content, encoding="utf-8")

    print(f"✅ 日报已保存：{output_path}")
    return output_path


def main():
    print("=== AI Observation 日报生成 ===\n")
    config = load_config()

    # Step 1: 获取信息（Level 1: RSS）
    print("📡 正在抓取 RSS 信息源...")
    raw_info = fetch_info()

    if not raw_info:
        print("⚠️  今日没有抓取到有效信息，跳过日报生成")
        return

    # Step 2: AI 生成日报
    print("\n🤖 正在调用 AI 生成日报...")
    report_content = generate_report_with_ai(raw_info, config)

    # Step 3: 保存
    save_report(report_content, config)
    print("\n🎉 日报生成完成！")


if __name__ == "__main__":
    main()
