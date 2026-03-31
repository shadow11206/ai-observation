#!/usr/bin/env python3
"""
build_opinions_index.py
解析 04-opinion-log/*.md 文件，提取当前判断、信心等级、更新记录、关联调研，
生成 ui/data/opinions-index.json 供前端动态渲染。
"""

import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPINION_DIR = os.path.join(BASE_DIR, '04-opinion-log')
OUTPUT_FILE = os.path.join(BASE_DIR, 'ui', 'data', 'opinions-index.json')

# 话题标签颜色映射
TAG_STYLES = {
    'model-landscape':  {'label': '大模型格局', 'bg': 'rgba(52,199,89,0.1)',   'color': '#1a7f37'},
    'ai-agent-landing': {'label': 'AI Agent',   'bg': 'rgba(0,113,227,0.08)', 'color': '#0071e3'},
    'ai-coding-trend':  {'label': 'AI Coding',  'bg': 'rgba(255,149,0,0.1)',  'color': '#c6690a'},
    'ai-pm-impact':     {'label': 'AI × PM',    'bg': 'rgba(175,82,222,0.1)', 'color': '#7b3fa0'},
}

# 信心状态颜色
CONFIDENCE_LEVELS = {
    1: 'low', 2: 'low', 3: 'medium', 4: 'high', 5: 'high'
}


def parse_confidence(text):
    """从文本中提取信心等级数字（★ 数量）"""
    stars = re.findall(r'★', text)
    return len(stars)


def parse_opinion_file(filepath, slug):
    """解析单个 opinion-log MD 文件，返回结构化数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    result = {
        'id': slug,
        'file': os.path.basename(filepath),
        'tag': TAG_STYLES.get(slug, {'label': slug, 'bg': 'rgba(0,0,0,0.05)', 'color': '#666'}),
    }

    # 提取标题（第一个 # 行）
    title_match = re.search(r'^#\s+核心问题[：:]\s*(.+)$', content, re.MULTILINE)
    result['question'] = title_match.group(1).strip() if title_match else slug

    # 提取建立日期和最近更新日期
    created_match = re.search(r'建立日期[：:]\s*(\d{4}-\d{2}-\d{2})', content)
    updated_match = re.search(r'最近更新[：:]\s*(\d{4}-\d{2}-\d{2})', content)
    result['created_at'] = created_match.group(1) if created_match else ''
    result['updated_at'] = updated_match.group(1) if updated_match else ''

    # 提取当前判断区块（## 🟢/🟡/🔴 当前判断 ... 信心：）
    judgment_match = re.search(
        r'##\s+[🟢🟡🔴]\s+当前判断[（(][^)）]*[）)](.*?)(?=^---|\Z)',
        content, re.MULTILINE | re.DOTALL
    )
    if judgment_match:
        judgment_block = judgment_match.group(1).strip()
        # 提取信心行
        conf_match = re.search(r'信心[：:]\s*(★+[☆]*)', judgment_block)
        if conf_match:
            result['confidence_raw'] = conf_match.group(1)
            result['confidence'] = parse_confidence(conf_match.group(1))
            # 移除信心行，保留正文
            verdict = re.sub(r'\n*信心[：:].*$', '', judgment_block, flags=re.MULTILINE).strip()
        else:
            result['confidence_raw'] = ''
            result['confidence'] = 0
            verdict = judgment_block
        # 清理 markdown 加粗/链接，保留可读文本
        verdict = re.sub(r'\*\*(.+?)\*\*', r'\1', verdict)
        verdict = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', verdict)
        result['verdict'] = verdict
    else:
        result['verdict'] = ''
        result['confidence_raw'] = ''
        result['confidence'] = 0

    # 判断状态颜色
    conf_num = result['confidence']
    if conf_num >= 4:
        result['status_color'] = 'green'
        result['status_emoji'] = '🟢'
    elif conf_num == 3:
        result['status_color'] = 'yellow'
        result['status_emoji'] = '🟡'
    else:
        result['status_color'] = 'red'
        result['status_emoji'] = '🔴'

    # 提取更新记录（## 更新记录 下所有 ### 条目）
    updates = []
    updates_section = re.search(
        r'##\s+更新记录(.*?)(?=^##\s+[^#]|\Z)',
        content, re.MULTILINE | re.DOTALL
    )
    if updates_section:
        update_items = re.findall(
            r'###\s+(\d{4}-\d{2}-\d{2})\s*\|?\s*(.+?)(?=###\s+\d{4}|\Z)',
            updates_section.group(1),
            re.DOTALL
        )
        for date_str, body in update_items:
            # 提取信心变化
            conf_change_match = re.search(r'信心[变化]*[：:]\s*([★☆→\s\+\-\d]+)', body)
            conf_change = conf_change_match.group(1).strip() if conf_change_match else ''
            # 清理正文
            body_clean = body.strip()
            body_clean = re.sub(r'\*\*(.+?)\*\*', r'\1', body_clean)
            body_clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', body_clean)
            updates.append({
                'date': date_str,
                'title': re.search(r'\|?\s*(.+)', date_str + ' ' + body.split('\n')[0]).group(1).strip() if body.split('\n')[0] else '',
                'body': body_clean,
                'confidence_change': conf_change,
            })
    result['updates'] = updates
    result['updates_count'] = len(updates)

    # 提取关联深度调研
    related = []
    related_section = re.search(r'##\s+🔗\s+相关深度调研(.*?)(?=^##|\Z)', content, re.MULTILINE | re.DOTALL)
    if related_section:
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', related_section.group(1))
        for title, href in links:
            if '待补充' not in title and href.strip():
                related.append({'title': title, 'href': href})
    result['related_research'] = related

    return result


def build_index():
    print('📋 构建判断索引...')
    items = []

    # 按固定顺序处理（model-landscape 最重要，放首位）
    order = ['model-landscape', 'ai-agent-landing', 'ai-coding-trend', 'ai-pm-impact']

    for slug in order:
        filepath = os.path.join(OPINION_DIR, f'{slug}.md')
        if not os.path.isfile(filepath):
            print(f'  ⚠️  跳过（文件不存在）: {slug}.md')
            continue
        try:
            item = parse_opinion_file(filepath, slug)
            items.append(item)
            print(f'  ✅ {slug} | 信心 {item["confidence_raw"]} | 更新 {item["updated_at"]}')
        except Exception as e:
            print(f'  ❌ 解析失败 {slug}: {e}')

    # 按最近更新降序
    items.sort(key=lambda x: x.get('updated_at', ''), reverse=True)

    index = {
        'total': len(items),
        'updated_at': datetime.now().strftime('%Y-%m-%d'),
        'items': items,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f'\n✅ 索引已写入：ui/data/opinions-index.json')
    print(f'   共 {len(items)} 个判断')


if __name__ == '__main__':
    build_index()
