"""
追踪体系自动更新脚本
====================
功能：
  1. 扫描全部 RSS 信息源，提取高频出现的人物/博客
  2. AI 评估是否满足准入门槛（引用频次 + 内容质量）
  3. 自动将通过门槛的新人加入对应 L1/L2/L3 清单
  4. 按影响力分（内容质量×50% + 被引用×30% + 活跃度×20%）重新排名
  5. 生成本次更新简报（≤15行），保存到 update-reports/

运行方式：
  python scripts/update_tracking.py

所需环境变量：
  AI_API_KEY   - AI 模型 API Key
  AI_API_BASE  - API Base URL

模块职责分离：
  fetch_rss.py      → 只负责抓取信息
  update_tracking.py → 只负责追踪体系更新逻辑
  generate_daily.py  → 只负责日报生成逻辑
"""

import json
import os
import re
import sys
import yaml
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.fetch_rss import fetch_info


# ── 路径常量 ────────────────────────────────────────────────────────────────
PEOPLE_INDEX = Path("03-tracking-registry/people/index.md")
SOURCES_INDEX = Path("03-tracking-registry/sources/index.md")
REPORT_DIR = Path("03-tracking-registry/update-reports")
CONFIG_PATH = Path("scripts/config.yaml")


# ── 配置加载 ────────────────────────────────────────────────────────────────
def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── 现有人物清单解析 ─────────────────────────────────────────────────────────
def parse_existing_people(md_content: str) -> dict[str, list[dict]]:
    """
    解析 people/index.md，返回：
    {
      "L1": [{"rank": 1, "name": "Simon Willison", "org": ..., "channel": ..., "focus": ..., "score": "—", "updated": "—"}, ...],
      "L2": [...],
      "L3": [...]
    }
    """
    result = {"L1": [], "L2": [], "L3": []}
    current_level = None

    for line in md_content.splitlines():
        # 检测层级标题
        if "## L1" in line:
            current_level = "L1"
        elif "## L2" in line:
            current_level = "L2"
        elif "## L3" in line:
            current_level = "L3"

        # 解析表格数据行（跳过表头和分隔线）
        if current_level and line.startswith("|") and "排名" not in line and "----" not in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 6 and cells[1]:  # cells[0]=排名, cells[1]=人物名
                result[current_level].append({
                    "rank": cells[0],
                    "name": cells[1],
                    "org": cells[2] if len(cells) > 2 else "",
                    "channel": cells[3] if len(cells) > 3 else "",
                    "focus": cells[4] if len(cells) > 4 else "",
                    "score": cells[5] if len(cells) > 5 else "—",
                    "updated": cells[6] if len(cells) > 6 else "—",
                })

    return result


def get_existing_names(people_data: dict) -> set[str]:
    """获取所有已追踪人物的名字集合"""
    names = set()
    for level_people in people_data.values():
        for p in level_people:
            names.add(p["name"].lower().strip())
    return names


# ── RSS 信息分析：提取高频人物 ──────────────────────────────────────────────
def extract_candidate_people(items: list[dict]) -> list[dict]:
    """
    从 RSS 内容中提取候选人物：
    - 统计各人物/博客被提及次数
    - 只保留出现 ≥ 3 次的候选人
    """
    mention_counter = Counter()
    mention_context = defaultdict(list)  # 保存上下文，供 AI 质量评估

    for item in items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        source_name = item.get("source", "")

        # 从 person 字段获取（config.yaml 中有标注的）
        if item.get("person"):
            mention_counter[item["person"]] += 1
            mention_context[item["person"]].append({
                "title": item.get("title", ""),
                "source": source_name,
                "url": item.get("url", ""),
            })

        # 从内容中提取（简单启发式：寻找 "X said", "X wrote" 等模式）
        # 这里只做轻量提取，重量级提取交给 AI
        name_patterns = [
            r"([A-Z][a-z]+ [A-Z][a-z]+) said",
            r"([A-Z][a-z]+ [A-Z][a-z]+) wrote",
            r"([A-Z][a-z]+ [A-Z][a-z]+)'s",
            r"by ([A-Z][a-z]+ [A-Z][a-z]+)",
        ]
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            for name in matches:
                # 过滤明显不是人名的词组
                if len(name) < 30 and name not in {"The New", "New York", "San Francisco"}:
                    mention_counter[name] += 1
                    mention_context[name].append({
                        "title": item.get("title", ""),
                        "source": source_name,
                        "url": item.get("url", ""),
                    })

    # 返回出现 ≥ 3 次的候选人
    candidates = []
    for name, count in mention_counter.most_common(30):
        if count >= 3:
            candidates.append({
                "name": name,
                "appearances": count,
                "context": mention_context[name][:3],  # 最多 3 条上下文
            })

    return candidates


# ── AI 评估：新人准入 + 影响力评分 ──────────────────────────────────────────
def ai_evaluate_candidates(
    candidates: list[dict],
    existing_names: set[str],
    all_items: list[dict],
    config: dict,
) -> dict:
    """
    调用 AI 完成两件事：
    1. 评估候选人是否满足准入条件，确定加入哪个 L 级别
    2. 对全部现有人物重新计算影响力分并排名

    返回：
    {
      "new_people": [{"name": ..., "level": "L1/L2/L3", "org": ..., "channel": ..., "focus": ..., "score": 85}],
      "scored_people": {
        "L1": [{"name": ..., "score": 90, "score_breakdown": {...}}, ...],
        "L2": [...],
        "L3": [...]
      },
      "summary": "本次更新简报（纯文本，≤15行）"
    }
    """
    api_key = os.environ.get("AI_API_KEY")
    api_base = os.environ.get("AI_API_BASE", "https://api.deepseek.com")
    if not api_key:
        raise ValueError("未找到 AI_API_KEY 环境变量")

    client = OpenAI(api_key=api_key, base_url=api_base)

    # 准备现有人物列表（供 AI 参考计算影响力）
    existing_content = PEOPLE_INDEX.read_text(encoding="utf-8")
    existing_data = parse_existing_people(existing_content)

    # 准备候选人信息（过滤掉已存在的）
    new_candidates = [
        c for c in candidates
        if c["name"].lower() not in existing_names
    ]

    # 准备近 7 天信息摘要（用于计算活跃度和被引用次数）
    info_summary = _build_info_summary(all_items)

    prompt = f"""你是 AI Observation 项目的追踪体系管理员。

## 当前追踪人物清单
{existing_content}

## 过去 7 天信息摘要（用于计算影响力分）
{info_summary}

## 候选新人（出现 ≥ 3 次，待评估是否加入）
{json.dumps(new_candidates, ensure_ascii=False, indent=2)}

## 你的任务

### 任务 1：评估候选新人是否加入
准入条件（同时满足）：
1. 内容以「一手洞察」为主（本人的实践经验/技术分析），而非纯转述他人
2. 在 AI 行业有持续影响力，不是单篇爆款
3. 能被持续追踪（有博客/RSS/GitHub）

层级定义：
- L1 实践者：正在一线构建 AI 产品，有第一手技术产出
- L2 深度观察者：对 AI 行业有深度解读，产出高质量分析
- L3 战略决策者：AI 公司 CEO/CTO 级别，信息频率低但影响大

### 任务 2：对全部现有人物（含新加入的）重新计算影响力分并排名
影响力分（0-100）= 内容质量×50% + 被引用次数×30% + 近期活跃度×20%

评分标准：
- 内容质量（0-100）：一手洞察占比、内容深度、是否对行业有独特贡献
- 被引用次数（0-100）：过去 7 天被其他信息源引用/提及次数（相对分）
- 近期活跃度（0-100）：过去 7 天有无新发布（有=100，无=0）

注意：只在同一 L 级别内排名，不跨级比较。

## 严格按以下 JSON 格式输出（只输出 JSON）：
{{
  "new_people": [
    {{
      "name": "人物名",
      "level": "L1",
      "org": "所在机构/项目",
      "channel": "主要追踪渠道",
      "focus": "关注方向（20字以内）",
      "score": 75,
      "reason": "加入理由（30字以内）"
    }}
  ],
  "scored_people": {{
    "L1": [
      {{
        "name": "Simon Willison",
        "score": 92,
        "quality": 95,
        "citations": 88,
        "activity": 100
      }}
    ],
    "L2": [],
    "L3": []
  }},
  "summary": "本次更新简报：\\n新增 X 人（L1: X, L2: X, L3: X）\\n影响力分变化最大：XXX（+X）→ 当前分 XX\\n本周最活跃：XXX"
}}

要求：
1. new_people 只填真正满足准入条件的候选人，不凑数，宁缺毋滥
2. scored_people 必须包含当前清单中的全部人物（含新加入的）
3. 每个 L 级别内按 score 降序排列
4. summary 不超过 15 行
"""

    response = client.chat.completions.create(
        model=config["ai"]["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    json_match = re.search(r'(\{[\s\S]*\})\s*$', raw.strip())
    if json_match:
        raw = json_match.group(1)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"⚠️ AI 返回 JSON 解析失败：{e}")
        return {"new_people": [], "scored_people": {"L1": [], "L2": [], "L3": []}, "summary": "评估失败，请查看日志"}


def _build_info_summary(items: list[dict]) -> str:
    """将近 7 天信息压缩为摘要字符串，控制在合理长度"""
    lines = []
    for i, item in enumerate(items[:60]):  # 最多 60 条
        lines.append(f"[{item.get('source', '')}] {item.get('title', '')} | {item.get('url', '')}")
    return "\n".join(lines)


# ── 更新 people/index.md ────────────────────────────────────────────────────
def update_people_index(eval_result: dict, existing_data: dict) -> str:
    """
    根据 AI 评估结果生成新的 people/index.md 内容
    """
    today = datetime.now().strftime("%Y-%m-%d")
    scored = eval_result.get("scored_people", {"L1": [], "L2": [], "L3": []})
    new_people = eval_result.get("new_people", [])

    # 将新人合并到 scored 中
    for person in new_people:
        level = person.get("level", "L2")
        if level in scored:
            scored[level].append({
                "name": person["name"],
                "score": person.get("score", 50),
                "quality": 50,
                "citations": 50,
                "activity": 100,
                # 保留额外信息供渲染
                "_org": person.get("org", "—"),
                "_channel": person.get("channel", "—"),
                "_focus": person.get("focus", "—"),
            })

    # 重新按 score 排序
    for level in scored:
        scored[level].sort(key=lambda x: x.get("score", 0), reverse=True)

    # 从 existing_data 中建立人物信息字典（补充 org/channel/focus）
    info_map = {}
    for level, people_list in existing_data.items():
        for p in people_list:
            info_map[p["name"]] = p

    # 生成 markdown
    lines = [
        "# 人物追踪清单",
        "",
        "> 追踪原则：实践者（L1）> 观察者（L2）> 决策者（L3）",
        "> L1 信息优先处理，L3 信息重点关注方向判断",
        ">",
        "> **影响力分说明**（0-100，由 update_tracking.py 每周自动更新）",
        "> = 内容质量×50% + 被引用次数×30% + 近期活跃度×20%",
        "> 同级内按影响力分降序排列，分值越高越靠前",
        "",
        "---",
    ]

    level_meta = {
        "L1": ("## L1 实践者 / 构建者", "正在一线构建 AI 产品，产出第一手经验和技术洞察"),
        "L2": ("## L2 深度观察者", "对 AI 行业有深度解读能力的分析者，产出高质量二手洞察"),
        "L3": ("## L3 战略决策者", "AI 行业的战略制定者，信息频率低但影响大，重点关注方向判断"),
    }

    for level in ["L1", "L2", "L3"]:
        title, desc = level_meta[level]
        count = len(scored.get(level, []))
        lines += [
            "",
            title,
            "",
            f"> {desc}",
            "",
            "| 排名 | 人物 | 所在机构/项目 | 主要追踪渠道 | 关注方向 | 影响力分 | 最近更新 |",
            "|------|------|-------------|------------|---------|---------|---------|",
        ]

        for i, person in enumerate(scored.get(level, []), 1):
            name = person["name"]
            score = person.get("score", "—")
            # 优先从现有信息获取 org/channel/focus
            info = info_map.get(name, {})
            org = info.get("org") or person.get("_org", "—")
            channel = info.get("channel") or person.get("_channel", "—")
            focus = info.get("focus") or person.get("_focus", "—")
            lines.append(f"| {i} | {name} | {org} | {channel} | {focus} | {score} | {today} |")

        lines.append("")
        lines.append("---")

    lines += [
        "",
        f"*影响力分由 `scripts/update_tracking.py` 每周一 11:00 (UTC+8) 自动更新*",
        f"*最后自动更新：{today}*",
    ]

    return "\n".join(lines)


# ── 生成更新报告 ─────────────────────────────────────────────────────────────
def save_update_report(eval_result: dict, new_count: int, today: str):
    """保存本次更新简报到 update-reports/"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{today}.md"

    summary = eval_result.get("summary", "无")
    new_people = eval_result.get("new_people", [])
    scored = eval_result.get("scored_people", {})

    lines = [
        f"# 追踪体系更新报告 · {today}",
        "",
        "## 本次更新摘要",
        "",
        summary,
        "",
        "## 新增人物详情",
        "",
    ]

    if new_people:
        lines.append("| 人物 | 层级 | 机构 | 关注方向 | 加入理由 |")
        lines.append("|------|------|------|---------|---------|")
        for p in new_people:
            lines.append(f"| {p['name']} | {p['level']} | {p.get('org','—')} | {p.get('focus','—')} | {p.get('reason','—')} |")
    else:
        lines.append("本次无新增人物。")

    lines += [
        "",
        "## 影响力分 Top 5（各层级）",
        "",
    ]

    for level in ["L1", "L2", "L3"]:
        level_people = scored.get(level, [])
        lines.append(f"### {level}")
        for i, p in enumerate(level_people[:5], 1):
            lines.append(f"{i}. {p['name']} — {p.get('score', '—')} 分")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ 更新报告已保存：{report_path}")


# ── 主流程 ────────────────────────────────────────────────────────────────────
def main():
    print("=== AI Observation 追踪体系更新 ===\n")
    today = datetime.now().strftime("%Y-%m-%d")
    config = load_config()

    # Step 1: 读取现有人物清单
    print("📋 读取当前追踪人物清单...")
    existing_content = PEOPLE_INDEX.read_text(encoding="utf-8")
    existing_data = parse_existing_people(existing_content)
    existing_names = get_existing_names(existing_data)
    print(f"  当前：L1={len(existing_data['L1'])} 人，L2={len(existing_data['L2'])} 人，L3={len(existing_data['L3'])} 人")

    # Step 2: 抓取近 7 天 RSS 信息（lookback=168h）
    print("\n📡 抓取近 7 天 RSS 信息（用于发现新人）...")
    # 临时修改 lookback 为 168 小时（7 天）
    original_lookback = config["filter"]["hours_lookback"]
    config["filter"]["hours_lookback"] = 168
    all_items = fetch_info(config=config)
    config["filter"]["hours_lookback"] = original_lookback
    print(f"  共获取 {len(all_items)} 条信息")

    # Step 3: 提取候选人
    print("\n🔍 分析高频出现的人物...")
    candidates = extract_candidate_people(all_items)
    new_candidates = [c for c in candidates if c["name"].lower() not in existing_names]
    print(f"  发现 {len(candidates)} 个高频人物，其中 {len(new_candidates)} 个是新候选人")

    # Step 4: AI 评估 + 重新排名
    print("\n🤖 AI 评估候选人 + 重新计算影响力分...")
    eval_result = ai_evaluate_candidates(candidates, existing_names, all_items, config)

    new_people = eval_result.get("new_people", [])
    print(f"  ✓ 新增 {len(new_people)} 人：{[p['name'] for p in new_people]}")

    # Step 5: ⚠️ 不自动覆盖 people/index.md
    # 原因：parse_existing_people 只能解析标准排名表格格式，
    # 而当前 index.md 是按公司分组的自定义格式，解析结果为空，
    # 写回后会清空所有人物记录。改为只输出新人建议到更新报告。
    new_people = eval_result.get("new_people", [])
    if new_people:
        print(f"\n💡 本次发现 {len(new_people)} 个新候选人，请手动评估是否加入追踪清单：")
        for p in new_people:
            print(f"  - {p['name']} ({p.get('level','?')}) @ {p.get('org','—')} — {p.get('focus','—')}")
        print(f"  ↳ 详见更新报告，请人工审核后手动添加到 people/index.md")
    else:
        print("\n  本次无新候选人")

    # Step 6: 保存更新报告
    print("\n📊 生成更新报告...")
    save_update_report(eval_result, len(new_people), today)

    print(f"\n🎉 追踪体系扫描完成！发现 {len(new_people)} 个新候选人（需人工审核）")

    # 打印简报
    print("\n" + "─" * 40)
    print(eval_result.get("summary", ""))
    print("─" * 40)


if __name__ == "__main__":
    main()
