"""
补报日报脚本
============
用于补报缺失的日报（如某天 RSS 无数据或 AI 解析失败导致文件缺失）。

用法：
  AI_API_KEY=xxx AI_API_BASE=https://api.deepseek.com python scripts/backfill_report.py 2026-05-24

使用当前 RSS 数据生成指定日期的日报，summary 中标注"(补报)"。
"""

import json
import os
import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.fetch_rss import fetch_info
from scripts.fetch_snapshot import fetch_snapshot
from scripts.generate_daily import (
    generate_report_with_ai,
    _render_md,
    _generate_hf_summary,
)


def backfill(date_str: str):
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    print(f"=== 补报日报：{date_str} ===\n")

    print("📡 正在抓取 RSS 信息源...")
    raw_info = fetch_info()
    if not raw_info:
        print("⚠️  当前没有抓取到有效 RSS 信息，无法生成补报")
        return

    print("\n📊 正在抓取数据快照...")
    snapshot = fetch_snapshot()
    snapshot["date"] = date_str

    print("\n🤖 正在调用 AI 生成日报...")
    report_data = generate_report_with_ai(raw_info, config, date_override=date_str)

    original_summary = report_data.get("summary_one_line", "")
    report_data["summary_one_line"] = f"{original_summary}（补报）"

    if snapshot.get("hf_trending"):
        print("\n💬 生成 HF 快照一句话解读...")
        snapshot["hf_summary"] = _generate_hf_summary(snapshot["hf_trending"], config)

    report_data["snapshot"] = snapshot
    report_data.pop("raw_content", None)

    month = date_str[:7]
    output_dir = Path(config["report"]["output_dir"]) / month
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{date_str}.json"
    json_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"✅ JSON 已保存：{json_path}")

    md_content = _render_md(report_data)
    md_path = output_dir / f"{date_str}.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"✅ MD  已保存：{md_path}")

    print(f"\n🎉 补报完成！{date_str} 日报已生成")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scripts/backfill_report.py YYYY-MM-DD")
        print("需要设置环境变量：AI_API_KEY 和 AI_API_BASE")
        sys.exit(1)

    backfill(sys.argv[1])
