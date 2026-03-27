# -*- coding: utf-8 -*-
"""
build_tracking_json.py
解析 03-tracking-registry/ 下三个 .md 文件，生成 ui/data/tracking.json
供 ui/tracking.html 动态渲染

运行方式:
  python scripts/build_tracking_json.py
"""

import json
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PEOPLE_MD = BASE_DIR / "03-tracking-registry" / "people" / "index.md"
COMPANIES_MD = BASE_DIR / "03-tracking-registry" / "companies" / "index.md"
SOURCES_MD = BASE_DIR / "03-tracking-registry" / "sources" / "index.md"
OUTPUT_DIR = BASE_DIR / "ui" / "data"
OUTPUT_FILE = OUTPUT_DIR / "tracking.json"


def parse_table_rows(lines, start, end):
    """解析 markdown 表格，返回 dict 列表（跳过分隔行）"""
    rows = []
    headers = []
    for i in range(start, min(end, len(lines))):
        line = lines[i].strip()
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not cells:
            continue
        # 分隔行（|---|---| 类型）
        if all(re.match(r"^[-: ]+$", c) for c in cells):
            continue
        if not headers:
            headers = [re.sub(r"\*+", "", c).strip() for c in cells]
        else:
            row = {}
            for j, h in enumerate(headers):
                val = cells[j] if j < len(cells) else ""
                # 去掉粗体标记 **xxx**
                val = re.sub(r"\*\*(.+?)\*\*", r"\1", val)
                row[h] = val.strip()
            rows.append(row)
    return rows


def find_section_ranges(lines, heading_prefix="###"):
    """
    返回 [(heading_text, start_line, end_line), ...]
    end_line 是下一个同级或更高级 heading 的行号（不含）
    """
    result = []
    prefix_len = len(heading_prefix)
    for i, line in enumerate(lines):
        if line.startswith(heading_prefix + " "):
            text = line[prefix_len:].strip()
            result.append([text, i, len(lines)])
    for idx in range(len(result) - 1):
        result[idx][2] = result[idx + 1][1]
    return [(t, s, e) for t, s, e in result]


def parse_people(filepath):
    """解析 people/index.md → L1/L2/L3 结构化数据"""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    result = {
        "l1": {"groups": []},
        "l2": {"groups": []},
        "l3": {"people": []}
    }

    current_level = None
    current_group = None
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # 检测一级章节（## L1 / ## L2 / ## L3）
        if line.startswith("## L1"):
            current_level = "l1"
            current_group = None
        elif line.startswith("## L2"):
            current_level = "l2"
            current_group = None
        elif line.startswith("## L3"):
            current_level = "l3"
            current_group = None

        # 检测三级章节 ### xxx（用于 L1/L2 分组）
        elif line.startswith("### ") and current_level in ("l1", "l2"):
            group_name = line[4:].strip()
            # 找到接下来的表格
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("|"):
                j += 1
            # 确定表格结束位置
            k = j
            while k < len(lines) and (lines[k].strip().startswith("|") or lines[k].strip() == ""):
                k += 1
            # 解析表格
            table_rows = parse_table_rows(lines, j, k)
            people = []
            for row in table_rows:
                # 统一字段名映射
                name = (row.get("人物") or row.get("人物/媒体") or "").strip()
                if not name:
                    continue
                people.append({
                    "name": name,
                    "role": (row.get("角色") or row.get("公司/角色") or "").strip(),
                    "channel": (row.get("主要渠道") or row.get("平台 URL") or row.get("平台") or "").strip(),
                    "keywords": (row.get("搜索关键词") or "").strip(),
                    "focus": (row.get("追踪重点") or row.get("代表输出") or row.get("价值定位") or "").strip(),
                    "score": _parse_int(row.get("influence_score", "")),
                    "freq": (row.get("检查频率") or "").strip(),
                })
            if people:
                result[current_level]["groups"].append({
                    "group": group_name,
                    "people": people
                })

        # L3 直接是表格（无三级标题）
        elif line.startswith("|") and current_level == "l3":
            j = i
            k = j
            while k < len(lines) and (lines[k].strip().startswith("|") or lines[k].strip() == ""):
                k += 1
            table_rows = parse_table_rows(lines, j, k)
            for row in table_rows:
                name = row.get("人物", "").strip()
                if not name:
                    continue
                result["l3"]["people"].append({
                    "name": name,
                    "role": (row.get("公司/角色") or "").strip(),
                    "channel": (row.get("主要渠道") or "").strip(),
                    "keywords": (row.get("搜索关键词") or "").strip(),
                    "focus": (row.get("信号权重") or row.get("追踪重点") or "").strip(),
                    "score": _parse_int(row.get("influence_score", "")),
                })
            i = k
            continue

        i += 1

    return result


def _parse_int(val):
    try:
        return int(str(val).strip())
    except Exception:
        return 0


def parse_companies(filepath):
    """解析 companies/index.md → 按大类分组的公司列表"""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    categories = []
    current_cat = None
    current_sub = None
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 二级标题 = 大类（## 一、xxx）
        if re.match(r"^## [一二三四五六七八九十]+[、.]", stripped):
            title = re.sub(r"^## [一二三四五六七八九十]+[、.]?\s*", "", stripped)
            current_cat = {"category": title, "subcategories": []}
            categories.append(current_cat)
            current_sub = None

        # 三级标题 = 子分类（### xxx）
        elif stripped.startswith("### ") and current_cat is not None:
            sub_title = stripped[4:].strip()
            current_sub = {"sub": sub_title, "companies": []}
            current_cat["subcategories"].append(current_sub)

        # 表格行
        elif stripped.startswith("|") and current_cat is not None:
            j = i
            k = j
            while k < len(lines) and (lines[k].strip().startswith("|") or lines[k].strip() == ""):
                k += 1
            table_rows = parse_table_rows(lines, j, k)
            for row in table_rows:
                name = (row.get("公司") or row.get("公司/产品") or "").strip()
                if not name:
                    continue
                company = {
                    "name": name,
                    "product": (row.get("核心产品") or row.get("产品") or row.get("AI核心产品/战略") or "").strip(),
                    "url": (row.get("官方渠道") or row.get("URL") or "").strip(),
                    "freq": (row.get("检查频率") or "").strip(),
                    "focus": (row.get("追踪重点") or "").strip(),
                }
                if current_sub is not None:
                    current_sub["companies"].append(company)
                else:
                    # 没有子分类，直接挂大类
                    if not current_cat["subcategories"]:
                        current_cat["subcategories"].append({"sub": "", "companies": []})
                    current_cat["subcategories"][-1]["companies"].append(company)
            i = k
            continue

        i += 1

    return categories


def parse_sources(filepath):
    """解析 sources/index.md → 风险分级 + 各类型信源列表"""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 提取风险分级信息
    risk_levels = {
        "safe": "🟢 安全：可直接引用，日期可靠，有编审机制",
        "warning": "🟡 高危：可引用但必须逐条验证发布日期",
        "banned": "🔴 禁用：绝对禁止作为日报信源（CSDN / 知乎回答）",
    }

    # 提取概览表格（类型总览）
    overview = []
    in_overview = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if "信息源分类概览" in stripped:
            in_overview = True
        elif in_overview and stripped.startswith("|"):
            j = i
            k = j
            while k < len(lines) and (lines[k].strip().startswith("|") or lines[k].strip() == ""):
                k += 1
            rows = parse_table_rows(lines, j, k)
            for row in rows:
                t = row.get("类型", "").strip()
                if not t:
                    continue
                overview.append({
                    "type": t,
                    "definition": row.get("定义", "").strip(),
                    "freq": row.get("检查频率", "").strip(),
                    "value": row.get("价值特点", "").strip(),
                    "count": row.get("数量", "").strip(),
                })
            in_overview = False
            i = k
            continue
        i += 1

    # 提取各大类（## xxx）下的子分类和表格内容
    categories = []
    current_cat = None
    current_sub = None
    i = 0

    # 跳过风险分级等说明章节，从"官方博客"开始
    start_keywords = ["官方博客", "Newsletter", "微信公众号", "播客", "YouTube", "学术", "社区", "X/Twitter", "媒体"]

    while i < len(lines):
        stripped = lines[i].strip()

        # 二级标题（## xxx）
        if stripped.startswith("## ") and not stripped.startswith("### "):
            title = stripped[3:].strip()
            # 只处理信源相关章节
            if any(k in title for k in start_keywords):
                current_cat = {"category": title, "subcategories": []}
                categories.append(current_cat)
                current_sub = None

        # 三级标题（### xxx）
        elif stripped.startswith("### ") and current_cat is not None:
            sub_title = stripped[4:].strip()
            current_sub = {"sub": sub_title, "items": []}
            current_cat["subcategories"].append(current_sub)

        # 表格
        elif stripped.startswith("|") and current_cat is not None:
            j = i
            k = j
            while k < len(lines) and (lines[k].strip().startswith("|") or lines[k].strip() == ""):
                k += 1
            rows = parse_table_rows(lines, j, k)
            items = []
            for row in rows:
                # 尝试多种字段名
                name = (row.get("名称") or row.get("公众号") or row.get("播客名")
                        or row.get("UP主") or row.get("频道") or row.get("账号")
                        or row.get("媒体") or row.get("平台") or row.get("公司")
                        or row.get("类型") or row.get("社区") or "").strip()
                if not name:
                    continue
                items.append({
                    "name": name,
                    "author": (row.get("作者") or row.get("主持人") or row.get("身份") or "").strip(),
                    "url": (row.get("URL") or row.get("邀请链接") or "").strip(),
                    "freq": (row.get("检查频率") or "").strip(),
                    "value": (row.get("价值定位") or row.get("价值") or row.get("内容类型") or row.get("内容定位") or "").strip(),
                })
            if items:
                if current_sub is not None:
                    current_sub["items"].extend(items)
                else:
                    if not current_cat["subcategories"]:
                        current_cat["subcategories"].append({"sub": "", "items": []})
                    current_cat["subcategories"][-1]["items"].extend(items)
            i = k
            continue

        i += 1

    return {
        "risk_levels": risk_levels,
        "overview": overview,
        "categories": categories,
    }


def main():
    print("🔧 build_tracking_json.py 启动...")

    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 解析三个文件
    print(f"  📂 解析 people/index.md ...")
    people = parse_people(PEOPLE_MD)

    print(f"  📂 解析 companies/index.md ...")
    companies = parse_companies(COMPANIES_MD)

    print(f"  📂 解析 sources/index.md ...")
    sources = parse_sources(SOURCES_MD)

    # 统计人物数
    l1_count = sum(len(g["people"]) for g in people["l1"]["groups"])
    l2_count = sum(len(g["people"]) for g in people["l2"]["groups"])
    l3_count = len(people["l3"]["people"])
    company_count = sum(
        len(sub["companies"])
        for cat in companies
        for sub in cat["subcategories"]
    )

    output = {
        "meta": {
            "generated_at": _now(),
            "people_total": l1_count + l2_count + l3_count,
            "l1_count": l1_count,
            "l2_count": l2_count,
            "l3_count": l3_count,
            "company_count": company_count,
        },
        "people": people,
        "companies": companies,
        "sources": sources,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 已生成 ui/data/tracking.json")
    print(f"  📊 人物: L1={l1_count} L2={l2_count} L3={l3_count} | 公司: {company_count}")


def _now():
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    main()
