# AI Observation

> 个人 AI 行业洞察系统 — 系统化追踪 AI 行业动态，沉淀观点，输出内容

**作者**：wb_tujia  
**目标**：个人认知升级 + 观点沉淀 + 公众号深度调研输出

---

## 项目结构

```
ai-observation/
├── 01-daily-reports/          # 每日日报（AI 自动生成，每天 09:00）
├── 02-deep-research/          # 深度调研（人工 or AI 触发）
├── 03-tracking-registry/      # 追踪体系（人物/公司/信息源）
├── 04-opinion-log/            # 观点更新日志（核心知识库）
├── templates/                 # 模板文件
├── scripts/                   # 自动化脚本
└── .github/workflows/         # GitHub Actions 工作流
```

## 核心设计理念

**信息流水线**：追踪体系 → 日报摄入 → AI 评估 → 深度调研 → 观点更新 → 公众号输出

**观点更新日志**（`04-opinion-log/`）是本项目的核心，区别于传统知识库：
- 不按主题分类存档，而是围绕**核心问题**维护实时判断
- 每次有新信息，更新对应问题下的观点和信心
- 公众号文章直接从观点日志中提炼

## 信息获取层（可随时升级）

| 级别 | 方式 | 状态 |
|------|------|------|
| Level 1 | RSS 订阅抓取 | ✅ 当前启用 |
| Level 2 | Perplexity/Exa 搜索 API | 🔜 后续升级 |
| Level 3 | AI Agent 控制浏览器 | 🔜 更后续 |

升级时只需替换 `scripts/fetch_rss.py`，下游生成逻辑不受影响。

## 快速开始

1. Fork/Clone 本仓库
2. 在 GitHub Settings → Secrets 中添加：
   - `AI_API_KEY`：你的 AI API Key（支持 DeepSeek/OpenAI/Anthropic）
   - `AI_API_BASE`：API Base URL（如 `https://api.deepseek.com`）
3. GitHub Actions 每天 09:00（北京时间）自动生成日报
4. 手动触发：Actions → Daily AI Report → Run workflow

## 飞书知识库

结构设计见 `docs/feishu-structure.md`

---

*让 AI 行业洞察变得系统化、可持续、有观点*
