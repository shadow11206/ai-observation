# AI Observation — AI 协作规则

> 个人 AI 行业洞察系统。自动化日报生成（30+ RSS 信源）+ GitHub Pages 展示 + 微信公众号同步。
> 项目全貌见 README.md。

## 脚本速查

| 脚本 | 作用 | 触发方式 |
|------|------|---------|
| `scripts/generate_daily.py` | 主日报生成：RSS 抓取 → AI 摘要 → JSON+MD 双输出 | cron-job.org 每天 UTC 02:00（北京 10:00）触发 workflow_dispatch |
| `scripts/fetch_rss.py` | RSS 抓取 + 去重 + 时间过滤 | generate_daily 内部调用 |
| `scripts/fetch_snapshot.py` | HF Trending + OpenRouter 排行快照 | generate_daily 内部调用 |
| `scripts/build_daily_index.py` | 日报索引 JSON（供前端列表页） | Actions generate 之后 |
| `scripts/build_tracking_json.py` | 解析追踪 MD → 前端 JSON | Actions 每月 1 日 + 16 日 / 手动 |
| `scripts/publish_wechat.py` | 日报推送到微信公众号草稿箱 | Actions generate 之后（continue-on-error） |
| `scripts/build_opinions_index.py` | 观点日志索引 | 手动 |
| `scripts/build_research_index.py` | 深度调研索引 | 手动 |

## 环境变量 / GitHub Secrets

| Secret | 用途 | 必需 |
|--------|------|------|
| `AI_API_KEY` | DeepSeek/OpenAI/Anthropic API Key | ✅ |
| `AI_API_BASE` | API Base URL（如 `https://api.deepseek.com`） | ✅ |
| `GITHUB_TOKEN` | 用于 fetch_snapshot GitHub API 请求 | ✅（Actions 自动注入） |
| `OPENROUTER_API_KEY` | OpenRouter API Key（数据集 API 认证） | ✅ |
| `WECHAT_APPID` | 微信公众号 AppID | 仅微信推送 |
| `WECHAT_APPSECRET` | 微信公众号 AppSecret | 仅微信推送 |

**本地开发**：手动设环境变量或用 `.env`（已在 .gitignore）。

## OpenRouter 数据

- **API**：`https://openrouter.ai/api/v1/datasets/rankings-daily`（需 `OPENROUTER_API_KEY` Bearer Token），返回 JSON
- **认证**：在 https://openrouter.ai/keys 创建 API Key，设为 GitHub Secret `OPENROUTER_API_KEY`
- **数据规则**：UTC 日历天（00:00-23:59 UTC），API 返回最近 ~30 天的每日 Top 50 模型 token 量
- **不含调用次数**：官方数据集 API 只有 `total_tokens` 字段（字符串，需 `int()` 转换），无 API 调用次数
- **日环比自己算**：用当日和前一日的 `total_tokens` 差值算百分比变化
- **`model_permaslug` 含日期后缀**（如 `tencent/hy3-preview-20260421`），聚合前需 `_strip_date_suffix()` 去掉
- **排除 `other` 行**：API 返回中有一条 `model_permaslug: "other"` 的汇总行，需过滤掉
- 排行榜页面确认：`https://openrouter.ai/rankings?view=day`

### 历史：API 迁移（2026-06-19）

旧的无认证前端 API (`/api/frontend/rankings/models?view=day`) 被 OpenRouter 下线（返回 404），迁移到官方数据集 API。旧 API 提供 `count`（调用次数）和 `change`（涨跌百分比），新 API 只有 `total_tokens`。

## 微信公众号

- 实现：`scripts/publish_wechat.py`
- 流程：获取 access_token → 上传封面图（仅首次）→ 创建草稿
- Token 缓存：`.wechat_token_cache.json`（已 gitignore）
- **IP 白名单**：GitHub Actions 托管 runner 的出口 IP 会变，`errcode: 40164` 表示 IP 不在白名单
- **推送失败不阻断日报流程**：workflow 已设 `continue-on-error: true`

## crontab / 定时触发

- **主触发器**：[cron-job.org](https://console.cron-job.org) Job ID `7843092`，每天 UTC 02:00 POST 到 GitHub API 触发 `workflow_dispatch`
- GitHub Actions 自带的 `schedule`（`0 2 * * *`）保留作为备用，但可靠性差（多次延迟/未触发）
- **Cron 修改后有延迟**：GitHub schedule 改 cron 后可能过 1-2 个周期才生效
- **runner IP 动态变化**：公众号 IP 白名单问题无法靠单次添加 IP 永久解决

## 硬规则 / 红线

- **不要裸回滚 ui/scripts/ 下的代码**。回滚只针对数据文件（`.json`），JS/CSS 回滚会丢掉后来加的功能。如果必须回滚代码，逐文件 diff 确认
- **commit 后立刻 `git show HEAD --stat`**。验证改动文件数量和行数符合预期。历史事故：`replace_in_file` 误匹配到无关文件，删了 124 行
- **JS 改动后 `node --check` 验证语法再 push**。历史事故：`multi_replace` 残留未闭合 template string，页面 JS 加载卡死
- **改了数据层要主动检查展示层**。升级 MD 追踪清单 → 确认前端 JSON 已同步 → 确认网页正确渲染
- **改全站 hardcoded 数值前先 `grep -r` 全局找**。同一数字可能出现在 stats-bar、feature-card、pipeline 节点等多处

## 项目结构要点

- `01-daily-reports/YYYY-MM/YYYY-MM-DD.md` + 同名 `.json` — AI 生成，双格式输出
- `02-deep-research/` — 手动深度调研（companies/topics/trends）
- `03-tracking-registry/` — 追踪体系 MD 文件，被 `build_tracking_json.py` 解析为前端 JSON
- `04-opinion-log/` — 核心观点库，每个文件一个议题，顶部「当前判断」+ 更新记录
- `ui/` — 纯静态站，GitHub Pages 托管于 main 分支 `/ui` 目录
- `dev-logs/` — 开发日志（最后更新 2026-03-29）

## 命令速查

```bash
# 手动触发生成日报（本地需要 AI_API_KEY + AI_API_BASE）
python3 scripts/generate_daily.py

# GitHub Actions 手动触发
gh workflow run daily-report.yml

# 查看最新运行日志
gh run list --workflow=daily-report.yml --limit=3
gh run view $(gh run list --workflow=daily-report.yml --limit=1 --json databaseId -q '.[0].databaseId') --log

# 同步追踪体系 MD → 前端 JSON
python3 scripts/build_tracking_json.py

# 验证 JS 语法
node --check ui/scripts/report.js

# 清除 GitHub Pages CDN 缓存：script 标签加版本号
# 格式：<script src="scripts/report.js?v=YYYYMMDD"></script>
```

## 深入文档

| 文档 | 内容 |
|------|------|
| README.md | 项目全貌、信源体系、技术栈、快速开始 |
| 04-opinion-log/README.md | 观点日志使用规则 |
| 04-opinion-log/ai-agent-landing.md | AI Agent 落地时间线判断 |
| 04-opinion-log/model-landscape.md | 大模型竞争格局判断 |
| 04-opinion-log/ai-coding-trend.md | AI Coding 工具趋势判断 |
| 04-opinion-log/ai-pm-impact.md | AI 对 PM 职业影响判断 |
| dev-logs/2026-03-24.md 等 | 历史开发日志 |
| scripts/config.yaml | RSS 信源配置、追踪阈值、微信配置 |
