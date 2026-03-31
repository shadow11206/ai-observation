#!/usr/bin/env python3
"""
build_research_index.py
遍历 02-deep-research/ 三个子目录，读取所有 .json 元数据，
生成 ui/data/research-index.json 索引文件。
"""

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESEARCH_DIR = os.path.join(BASE_DIR, '02-deep-research')
OUTPUT_FILE = os.path.join(BASE_DIR, 'ui', 'data', 'research-index.json')

CATEGORIES = ['trends', 'companies', 'topics']

CATEGORY_LABELS = {
    'trends': '趋势洞察',
    'companies': '公司调研',
    'topics': '专题研究',
}

def load_research_items():
    items = []
    for category in CATEGORIES:
        cat_dir = os.path.join(RESEARCH_DIR, category)
        if not os.path.isdir(cat_dir):
            continue
        for fname in os.listdir(cat_dir):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(cat_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 只保留索引页需要的字段
                item = {
                    'id': data.get('id', fname.replace('.json', '')),
                    'date': data.get('date', ''),
                    'title': data.get('title', ''),
                    'category': data.get('category', category),
                    'category_label': CATEGORY_LABELS.get(data.get('category', category), '调研'),
                    'type': data.get('type', ''),
                    'tags': data.get('tags', []),
                    'tldr': data.get('tldr', ''),
                    'confidence_rating': data.get('confidence_rating', ''),
                    'sources_count': data.get('sources_count', 0),
                    'from_report': data.get('from_report', ''),
                    'confidence_delta': data.get('confidence_delta', 0),
                }
                items.append(item)
                print(f'  ✅ {item["id"]}')
            except Exception as e:
                print(f'  ❌ 跳过 {fname}: {e}')

    # 按日期降序排列
    items.sort(key=lambda x: x['date'], reverse=True)
    return items

def build_index():
    print('📦 构建深度调研索引...')
    items = load_research_items()

    index = {
        'total': len(items),
        'updated_at': datetime.now().strftime('%Y-%m-%d'),
        'items': items,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f'\n✅ 索引已写入：ui/data/research-index.json')
    print(f'   共 {len(items)} 篇调研报告')

if __name__ == '__main__':
    build_index()
