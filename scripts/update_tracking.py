# -*- coding: utf-8 -*-
"""
追踪体系月度自动更新脚本
========================
功能：
  1. 抓取近 30 天 RSS 信息，从中发现高频出现的候选人物
  2. AI 评估候选人：是否满足准入门槛，加入哪个 L 级别
  3. 将通过评估的新人追加到 people/index.md 对应公司分组下
  4. 同步更新现有人物的 influence_score 字段
  5. 生成月度更新报告，保存到 03-tracking-registry/update-reports/

运行方式：
  python scripts/update_tracking.py

所需环境变量：
  AI_API_KEY   - AI 模型 API Key
  AI_API_BASE  - API Base URL（可选，默认 DeepSeek）

注意：本脚本只做"追加"，绝对不会删除或重写现有分组结构。
"""

import json
import os
import re
import sys
import yaml
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.fetch_rss import fetch_info

# ── 路径常量 ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
PEOPLE_INDEX = BASE_DIR / "03-tracking-registry" / "people" / "index.md"
COMPANIES_INDEX = BASE_DIR / "03-tracking-registry" / "companies" / "index.md"
SOURCES_INDEX = BASE_DIR / "03-tracking-registry" / "sources" / "index.md"
REPORT_DIR = BASE_DIR / "03-tracking-registry" / "update-reports"
CONFIG_PATH = BASE_DIR / "scripts" / "config.yaml"


# ── 辅助 ─────────────────────────────────────────────────────────────────────
def now_cn() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── 解析现有 people/index.md：获取所有已追踪人物名字 ─────────────────────────
def get_existing_names(md_content: str) -> set:
    """
    从 v2.0.0 格式的 people/index.md 中提取所有人物名字。
    格式示例：
      | **Jason Wei** | Research Lead | ...
      | **Barry Zhang** (张宇杰) | ...
    """
    names = set()
    for line in md_content.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        raw = cells[0]
        # 去掉 markdown 修饰
        raw = re.sub(r"\*+", "", raw)
        # 去掉括号里的中文名
        raw = re.sub(r"\s*\(.*?\)", "", raw).strip()
        # 过滤表头、分隔行
        if raw and not re.match(r"^[-: ]+$", raw) and "人物" not in raw and "名称" not in raw:
            names.add(raw.lower())
    return names


# ── 从 RSS 提取高频候选人 ────────────────────────────────────────────────────
def extract_candidate_people(items: list) -> list:
    """
    从抓取到的 RSS 条目中提取高频出现的人物候选。
    出现 ≥ 2 次才进入候选列表（月度窗口，门槛略低于周度）
    """
    mention_counter = Counter()
    mention_context = defaultdict(list)

    for item in items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        source_name = item.get("source", "")

        # config.yaml 中标注了 person 字段的优先
        if item.get("person"):
            mention_counter[item["person"]] += 2  # 标注的权重×2
            mention_context[item["person"]].append({
                "title": item.get("title", ""),
                "source": source_name,
                "url": item.get("url", ""),
            })

        # 启发式提取英文名
        name_patterns = [
            r"([A-Z][a-z]+ [A-Z][a-z]+) said",
            r"([A-Z][a-z]+ [A-Z][a-z]+) wrote",
            r"([A-Z][a-z]+ [A-Z][a-z]+)'s",
            r"by ([A-Z][a-z]+ [A-Z][a-z]+)",
            r"([A-Z][a-z]+ [A-Z][a-z]+) announced",
            r"([A-Z][a-z]+ [A-Z][a-z]+) published",
        ]
        for pattern in name_patterns:
            for name in re.findall(pattern, text):
                if len(name) < 35 and name not in {
                    "The New", "New York", "San Francisco",
                    "United States", "Last Week", "This Week",
                }:
                    mention_counter[name] += 1
                    mention_context[name].append({
                        "title": item.get("title", ""),
                        "source": source_name,
                        "url": item.get("url", ""),
                    })

    candidates = []
    for name, count in mention_counter.most_common(40):
        if count >= 2:
            candidates.append({
                "name": name,
                "appearances": count,
                "context": mention_context[name][:3],
            })
    return candidates


# ── 构建信息摘要（给 AI 参考） ───────────────────────────────────────────────
def _build_info_summary(items: list) -> str:
    lines = []
    for item in items[:80]:
        lines.append(
            f"[{item.get('source', '')}] {item.get('title', '')} | {item.get('url', '')}"
        )
    return "\n".join(lines)


# ── AI 评估：候选人准入 + influence_score 更新 ───────────────────────────────
def ai_evaluate(candidates: list, existing_names: set,
                all_items: list, config: dict) -> dict:
    """
    返回：
    {
      "new_people": [
        {
          "name": "xxx",
          "level": "L1|L2|L3",
          "company_group": "所属分组（对应 people/index.md 的 ### 标题）",
          "role": "职位/角色",
          "channel": "主要渠道（URL）",
          "keywords": "\"xxx\" site:yyy",
          "focus": "追踪重点（20字内）",
          "score": 75,
          "reason": "加入理由（30字内）"
        }
      ],
      "score_updates": [
        {"name": "xxx", "score": 88}
      ],
      "summary": "本月更新简报（≤15行）"
    }
    """
    api_key = os.environ.get("AI_API_KEY")
    api_base = os.environ.get("AI_API_BASE", "https://api.deepseek.com")
    if not api_key:
        raise ValueError("未找到 AI_API_KEY 环境变量")

    client = OpenAI(api_key=api_key, base_url=api_base)

    existing_content = PEOPLE_INDEX.read_text(encoding="utf-8")
    new_candidates = [c for c in candidates if c["name"].lower() not in existing_names]
    info_summary = _build_info_summary(all_items)

    prompt = f"""你是 AI Observation 项目的追踪体系管理员，正在做每月一次的追踪清单更新。

## 当前 people/index.md（v2.0.0 格式，按公司/类别分组）
{existing_content[:6000]}

## 过去 30 天信息摘要（用于判断活跃度和引用次数）
{info_summary[:3000]}

## 候选新人（出现 ≥ 2 次，待评估是否加入）
{json.dumps(new_candidates, ensure_ascii=False, indent=2)}

---

## 你的任务

### 任务 1：评估候选新人是否加入清单
准入条件（同时满足所有条件）：
1. 内容以「一手洞察」为主（本人的实践/技术产出），不是纯转述
2. 在 AI 行业有持续影响力（不是单篇热文）
3. 可以被持续追踪（有博客/X/GitHub/RSS）

层级定义：
- L1 实践者/构建者：正在一线做 AI 产品、写代码、有原创技术框架
- L2 深度观察者：有最深入的行业解读，产出 Newsletter/播客/深度分析
- L3 战略决策者：AI 公司 CEO/CTO/首席科学家，定方向

company_group 字段：填写此人应追加到 people/index.md 中哪个 ### 分组下。
例如：OpenAI、Anthropic、AI Coding 产品领导者、中国 AI 核心人物、必读 Newsletter/博客作者 等。
如果是全新的类别，请在 group 名后加"（新）"标注。

### 任务 2：对现有人物更新 influence_score
influence_score（0-100）= 内容质量×50% + 被引用次数×30% + 近期活跃度×20%
只输出 score 有变化（±3 分及以上）的人物。

---

## 严格按以下 JSON 格式输出（只输出 JSON，不加任何解释）：
{{
  "new_people": [
    {{
      "name": "人物名",
      "level": "L1",
      "company_group": "所属分组名",
      "role": "职位/角色",
      "channel": "主要渠道 URL 或 X 账号",
      "keywords": "搜索关键词（如 \\\"Name\\\" site:xxx）",
      "focus": "追踪重点（20字内）",
      "score": 75,
      "reason": "加入理由（30字内）"
    }}
  ],
  "score_updates": [
    {{"name": "现有人物名", "score": 88}}
  ],
  "summary": "本月更新简报（纯文本，≤15行）"
}}

要求：
1. new_people 宁缺毋滥，不满足条件的一律不加
2. score_updates 只列出变化 ±3 分及以上的，保持稳定的无需列出
3. summary 简洁，包含：新增X人、影响力变化最大者、本月最活跃
"""

    response = client.chat.completions.create(
        model=config["ai"]["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    # 非贪婪提取 JSON
    json_match = re.search(r'\{[\s\S]*?\}(?=\s*$)', raw)
    if json_match:
        raw = json_match.group(0)
    else:
        # fallback：找最外层 {}
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            raw = json_match.group(0)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"⚠️ AI JSON 解析失败：{e}\n原始内容：{raw[:300]}")
        return {
            "new_people": [],
            "score_updates": [],
            "summary": "评估失败，请检查日志"
        }


# ── 将新人追加到 people/index.md 对应分组 ────────────────────────────────────
def append_new_people(new_people: list) -> int:
    """
    逐人追加到 people/index.md 的对应 ### 分组下。
    - 若分组已存在：追加到该分组表格末尾
    - 若分组不存在：在对应 ## L 级章节末尾创建新分组
    返回实际追加数量。
    """
    if not new_people:
        return 0

    content = PEOPLE_INDEX.read_text(encoding="utf-8")
    lines = content.splitlines()
    added = 0

    for person in new_people:
        name = person.get("name", "").strip()
        if not name:
            continue

        level = person.get("level", "L2")  # L1 / L2 / L3
        group = person.get("company_group", "").strip()
        role = person.get("role", "").strip()
        channel = person.get("channel", "").strip()
        keywords = person.get("keywords", "").strip()
        focus = person.get("focus", "").strip()
        score = person.get("score", 0)

        # 根据 level 判断表头格式
        if level in ("L1",):
            table_header = "| 人物 | 角色 | 主要渠道 | 搜索关键词 | 追踪重点 |"
            table_sep   = "|------|------|---------|-----------|---------|"
            new_row     = f"| **{name}** | {role} | {channel} | `{keywords}` | {focus} |"
        elif level == "L2":
            table_header = "| 人物 | 平台 URL | 检查频率 | 价值定位 | influence_score |"
            table_sep   = "|------|---------|---------|---------|----------------|"
            new_row     = f"| **{name}** | {channel} | 每周1次 | {focus} | {score} |"
        else:  # L3
            # L3 是一个大表，直接找到 L3 表格末尾追加
            group = None  # L3 无分组

        content_lines = PEOPLE_INDEX.read_text(encoding="utf-8").splitlines()

        if level == "L3":
            # 找到 ## L3 章节下的表格，追加一行
            in_l3 = False
            table_started = False
            insert_at = None
            for i, ln in enumerate(content_lines):
                if ln.strip().startswith("## L3"):
                    in_l3 = True
                elif in_l3 and ln.strip().startswith("## "):
                    break  # 超出 L3 范围
                elif in_l3 and ln.strip().startswith("|") and "人物" in ln:
                    table_started = True
                elif table_started and ln.strip().startswith("|"):
                    insert_at = i  # 持续更新，最后一个 | 行
                elif table_started and not ln.strip().startswith("|") and ln.strip():
                    break  # 表格结束

            if insert_at is not None:
                row = f"| **{name}** | {role} | {channel} | `{keywords}` | {focus} | {score} |"
                content_lines.insert(insert_at + 1, row)
                PEOPLE_INDEX.write_text("\n".join(content_lines), encoding="utf-8")
                added += 1
                print(f"  ✅ 新增 L3：{name}")
            else:
                print(f"  ⚠️ 找不到 L3 表格插入位置，跳过：{name}")
            continue

        # L1 / L2：找对应分组（### group）
        # 先检查分组是否已存在
        group_line_idx = None
        for i, ln in enumerate(content_lines):
            if ln.strip() == f"### {group}":
                group_line_idx = i
                break

        if group_line_idx is not None:
            # 找到分组，定位到该分组表格末尾
            insert_at = None
            table_started = False
            for i in range(group_line_idx + 1, len(content_lines)):
                ln = content_lines[i].strip()
                if ln.startswith("| ") or ln.startswith("|---"):
                    table_started = True
                    if ln.startswith("| ") and not ln.startswith("|---") and "人物" not in ln and "名称" not in ln:
                        insert_at = i
                elif table_started and ln.startswith("### ") or (table_started and ln.startswith("## ")):
                    break
                elif table_started and not ln.startswith("|") and ln:
                    break

            if insert_at is not None:
                content_lines.insert(insert_at + 1, new_row)
                PEOPLE_INDEX.write_text("\n".join(content_lines), encoding="utf-8")
                added += 1
                print(f"  ✅ 追加到 [{group}]：{name}")
            else:
                print(f"  ⚠️ 找不到 [{group}] 的表格末尾，跳过：{name}")
        else:
            # 分组不存在，在对应 ## L 级章节末尾创建新分组
            # 找到该 L 级的最后一个 ### 分组
            level_heading = f"## L{level[-1]}"  # ## L1 / ## L2
            in_level = False
            last_section_end = None
            for i, ln in enumerate(content_lines):
                if ln.strip().startswith(level_heading):
                    in_level = True
                elif in_level and (ln.strip().startswith("## L") or ln.strip() == "---"):
                    last_section_end = i
                    break
            if last_section_end is None:
                last_section_end = len(content_lines)

            # 在前一个 --- 之前插入新分组
            insert_idx = last_section_end
            new_section = [
                "",
                f"### {group}",
                "",
                table_header,
                table_sep,
                new_row,
            ]
            for offset, sl in enumerate(new_section):
                content_lines.insert(insert_idx + offset, sl)

            PEOPLE_INDEX.write_text("\n".join(content_lines), encoding="utf-8")
            added += 1
            print(f"  ✅ 创建新分组 [{group}] 并添加：{name}")

    return added


# ── 更新现有人物的 influence_score ────────────────────────────────────────────
def update_influence_scores(score_updates: list) -> int:
    """
    对 score_updates 中的每个人物，在 people/index.md 中找到对应行并更新 influence_score 列。
    只更新 L2 表格（L2 有 influence_score 列）。
    返回实际更新数量。
    """
    if not score_updates:
        return 0

    content = PEOPLE_INDEX.read_text(encoding="utf-8")
    lines = content.splitlines()
    updated = 0

    for update in score_updates:
        name = update.get("name", "").strip()
        new_score = update.get("score")
        if not name or new_score is None:
            continue

        # 在所有表格行中找该人物
        for i, line in enumerate(lines):
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells:
                continue
            # 提取第一格人物名（去掉 ** 和括号注释）
            cell_name = re.sub(r"\*+", "", cells[0]).strip()
            cell_name = re.sub(r"\s*\(.*?\)", "", cell_name).strip()
            if cell_name.lower() != name.lower():
                continue

            # 找到 influence_score 列（通常是最后一列或倒数第二列）
            # 策略：看表头确定列索引
            # 先向上找最近的表头行
            header_row = None
            for j in range(i - 1, max(i - 10, -1), -1):
                if "influence_score" in lines[j]:
                    header_row = j
                    break

            if header_row is not None:
                headers = [c.strip().lower() for c in lines[header_row].strip("|").split("|")]
                try:
                    score_col = headers.index("influence_score")
                    # 更新该行的 score_col 列
                    row_cells = [c.strip() for c in line.strip("|").split("|")]
                    if len(row_cells) > score_col:
                        row_cells[score_col] = str(new_score)
                        lines[i] = "| " + " | ".join(row_cells) + " |"
                        updated += 1
                        print(f"  📊 更新 influence_score：{name} → {new_score}")
                except ValueError:
                    pass  # 该表格没有 influence_score 列

    PEOPLE_INDEX.write_text("\n".join(lines), encoding="utf-8")
    return updated


# ── 生成月度更新报告 ──────────────────────────────────────────────────────────
def save_monthly_report(eval_result: dict, new_count: int,
                        score_updated: int, today: str):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{today}.md"

    summary = eval_result.get("summary", "无")
    new_people = eval_result.get("new_people", [])

    lines = [
        f"# 追踪体系月度更新报告 · {today}",
        "",
        "## 本月更新摘要",
        "",
        summary,
        "",
        f"**统计**：新增 {new_count} 人，influence_score 更新 {score_updated} 人",
        "",
        "## 新增人物详情",
        "",
    ]

    if new_people:
        lines += [
            "| 人物 | 层级 | 所属分组 | 职位 | 追踪重点 | 加入理由 |",
            "|------|------|---------|------|---------|---------|",
        ]
        for p in new_people:
            lines.append(
                f"| {p.get('name','—')} "
                f"| {p.get('level','—')} "
                f"| {p.get('company_group','—')} "
                f"| {p.get('role','—')} "
                f"| {p.get('focus','—')} "
                f"| {p.get('reason','—')} |"
            )
    else:
        lines.append("本月无新增人物。")

    lines += [
        "",
        "---",
        "",
        f"*由 `scripts/update_tracking.py` 于 {today} 自动生成*",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✅ 月度报告已保存：{report_path}")


# ── 主流程 ────────────────────────────────────────────────────────────────────
def main():
    print("=== AI Observation 追踪体系月度更新 ===\n")
    today = now_cn()
    config = load_config()

    # Step 1: 读取现有人物清单
    print("📋 读取当前追踪清单...")
    existing_content = PEOPLE_INDEX.read_text(encoding="utf-8")
    existing_names = get_existing_names(existing_content)
    print(f"  当前已追踪人物：{len(existing_names)} 人")

    # Step 2: 抓取近 30 天 RSS 信息
    print("\n📡 抓取近 30 天 RSS 信息...")
    original_lookback = config["filter"].get("hours_lookback", 24)
    config["filter"]["hours_lookback"] = 720  # 30天
    try:
        all_items = fetch_info(config=config)
    except Exception as e:
        print(f"  ⚠️ RSS 抓取出错：{e}，使用空列表继续")
        all_items = []
    finally:
        config["filter"]["hours_lookback"] = original_lookback
    print(f"  获取 {len(all_items)} 条信息")

    # Step 3: 提取候选人
    print("\n🔍 提取高频出现的候选人物...")
    candidates = extract_candidate_people(all_items)
    new_candidates = [c for c in candidates if c["name"].lower() not in existing_names]
    print(f"  高频人物：{len(candidates)} 个，新候选：{len(new_candidates)} 个")

    # Step 4: AI 评估
    print("\n🤖 AI 评估候选人 + 计算 influence_score 变化...")
    eval_result = ai_evaluate(candidates, existing_names, all_items, config)
    new_people = eval_result.get("new_people", [])
    score_updates = eval_result.get("score_updates", [])
    print(f"  新增候选：{[p['name'] for p in new_people]}")
    print(f"  influence_score 变化：{len(score_updates)} 人")

    # Step 5: 追加新人到 people/index.md
    print("\n📝 追加新人到追踪清单...")
    added = append_new_people(new_people)

    # Step 6: 更新 influence_score
    print("\n📊 更新 influence_score...")
    score_updated = update_influence_scores(score_updates)

    # Step 7: 保存月度报告
    print("\n📄 生成月度报告...")
    save_monthly_report(eval_result, added, score_updated, today)

    print(f"\n🎉 月度更新完成！新增 {added} 人，score 更新 {score_updated} 人")
    print("\n" + "─" * 40)
    print(eval_result.get("summary", ""))
    print("─" * 40)


if __name__ == "__main__":
    main()
