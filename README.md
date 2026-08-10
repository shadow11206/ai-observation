# AI Observation

> 个人 AI 行业洞察系统 — 系统化追踪、沉淀判断、驱动内容输出

**作者**：tujia  
**定位**：个人认知升级工具 + AI 观点输出平台  
**站点**：[shadow11206.github.io/AI-Observation](https://shadow11206.github.io/ai-observation/ui/index.html)

---

## 这是什么

一个基于 GitHub Pages + GitHub Actions 构建的个人 AI 行业观察系统，核心功能：

- **每日日报**：自动抓取 30+ RSS 信源，AI 提炼摘要，每天 10:00 自动生成
- **追踪体系**：持续跟踪 AI 领域重要人物、公司和信息源动态
- **深度调研**：针对重点公司 / 话题 / 趋势的深度研究存档
- **观点日志**：对 AI 行业核心问题的实时判断更新，区别于普通资料收藏

---

## 项目结构

```
ai-observation/
├── 01-daily-reports/          # 每日日报（Markdown，自动生成）
├── 02-deep-research/          # 深度调研（公司 / 话题 / 趋势）
│   ├── companies/
│   ├── topics/
│   └── trends/
├── 03-tracking-registry/      # 追踪注册表
│   ├── people/                # 重点人物档案
│   ├── companies/             # 公司档案
│   ├── sources/               # 信源清单与风险分级
│   └── update-reports/        # 追踪更新报告
├── 04-opinion-log/            # 观点更新日志（核心知识库）
├── scripts/                   # 自动化脚本
│   ├── generate_daily.py      # 日报生成
│   ├── fetch_rss.py           # RSS 抓取
│   ├── fetch_snapshot.py      # OpenRouter 模型排行抓取
│   ├── build_daily_index.py   # 日报索引构建
│   ├── build_tracking_json.py # 追踪数据构建
│   ├── update_tracking.py     # 追踪体系更新
│   ├── config.yaml            # 信源配置（30+ RSS 源）
│   └── requirements.txt
├── ui/                        # 前端展示层（静态站）
│   ├── index.html             # 首页
│   ├── daily.html             # 日报页
│   ├── research.html          # 调研页
│   ├── opinions.html          # 观点页
│   ├── tracking.html          # 追踪页
│   ├── data/                  # 前端数据（JSON）
│   └── styles/
├── .github/workflows/
│   ├── daily-report.yml       # 每日 09:00 自动生成日报
│   └── update-tracking.yml    # 追踪体系定期更新
└── index.html                 # 根路径跳转
```

---

## 核心设计

**信息流水线**：
```
RSS 信源 → 日报生成 → AI 摘要提炼 → 观点更新 → 公众号输出
                ↓
        追踪体系自动扫描 → 人物/公司/工具档案更新
```

**观点日志**（`04-opinion-log/`）是本项目最核心的模块：
- 每个文件对应一个 AI 行业核心问题
- 顶部"当前判断"实时维护，任何时候都能快速获得立场
- 每次有新信息影响判断，追加更新记录（时间倒序）
- 信心等级：★ = 猜测 → ★★★★★ = 非常确定

**当前追踪的核心问题**：
- AI Agent 真正落地的时间线
- 大模型竞争格局如何演变
- AI Coding 工具的趋势
- AI 对产品经理职业的影响

---

## 信源体系

| 级别 | 说明 | 代表信源 |
|------|------|---------|
| 🟢 安全 | 可直接引用，日期可靠 | 官方博客、机器之心、量子位、36氪、TechCrunch |
| 🟡 高危 | 可用但必须验证日期 | 掘金、开源中国 |
| 🔴 禁用 | 日期不可靠，禁止作为信源 | CSDN、知乎回答 |

完整信源清单见 `03-tracking-registry/sources/index.md`。

---

## 快速开始

**Fork 本仓库后，添加三个 GitHub Secrets：**

| Secret 名称 | 说明 |
|-------------|------|
| `AI_API_KEY` | AI API Key（DeepSeek / OpenAI / Anthropic 均支持） |
| `AI_API_BASE` | API Base URL，如 `https://api.deepseek.com` |

> OpenRouter 排行已改用官方页面同源 API（`/api/frontend/v1/rankings/models`，无需 Key）。

配置完成后，每天 10:00（北京时间）cron-job.org 自动触发日报生成并 commit 到仓库。  
也可在 Actions 页面手动触发。

---

## 技术栈

- **自动化**：GitHub Actions（定时触发，无需服务器）
- **AI 生成**：DeepSeek / OpenAI / Anthropic（通过环境变量切换）
- **数据层**：Python 脚本生成 JSON，存入仓库
- **前端**：纯静态 HTML/CSS/JS，部署于 GitHub Pages
- **信源**：30+ RSS 订阅，按优先级分级处理

---

*系统化追踪 AI 行业，让洞察可积累、可沉淀、有观点。*
