# AI信息源追踪清单

> **版本**: v2.0.0
> **更新时间**: 2026-03-28
> **维护规则**: 每月 Review 一次，根据信息质量和时效性动态调整

---

## ⚠️ 信源风险分级（必读）

> **原则**: 信源质量直接决定日报可信度。高SEO排名 ≠ 高质量，发布日期不可靠是最大风险。

| 级别 | 标记 | 含义 | 信源 |
|------|------|------|------|
| 🟢 **安全** | ✅ | 可直接引用，日期可靠，有编审机制 | 产品官网、机器之心、量子位、36氪、TechCrunch、少数派、IT之家、InfoQ |
| 🟡 **高危** | ⚠️ | 可引用但**必须逐条验证发布日期**，UGC内容需交叉确认 | 掘金(juejin.cn)、开源中国(oschina.net)、博客园(cnblogs.com) |
| 🔴 **禁用** | ❌ | **绝对禁止作为日报信源**，SEO排名高但信息过时/日期不可靠/无编审 | CSDN(csdn.net)、知乎回答(zhihu.com) |

**禁用来源的问题**:
- **CSDN**: 社区聚合页标注"持续更新"实则无更新；博客日期混用"发布/编辑"不可信
- **知乎**: 回答按投票排序而非时间排序，旧答案长期霸榜；日期显示不透明

**高危来源使用规则**:
1. 必须在文章页面确认明确的发布日期
2. 日期必须在日报日期±7天内
3. 关键事实必须与安全来源交叉确认

---

## 🔄 月度配置保鲜检查

> **教训**: 配置文件是"设好就忘"的，没有主动刷新机制就会腐烂。

**每月1日执行，耗时约15分钟：**

### 检查项1：产品状态扫描
```
逐条检查官方博客/研究页中的每个URL：
- [ ] 产品是否仍在运营？（打开URL看是否404或重定向）
- [ ] 产品名称是否变更？（如MarsCode→Trae）
- [ ] 产品归属公司是否变化？（收购/独立/关停）
如有变更 → 立即更新本文件 + 搜索关键词
```

### 检查项2：信源质量复查
```
回顾过去一个月日报中实际引用的所有来源：
- [ ] 是否有来源多次出现日期不准确的情况？→ 考虑降级/禁用
- [ ] 是否有新发现的高质量来源？→ 考虑加入清单
- [ ] 禁用/高危来源是否有改善？→ 考虑是否调整级别
```

### 检查项3：搜索关键词保鲜
```
对照当前AI Coding/大模型/AI应用的实际竞争格局：
- [ ] 搜索关键词中是否有已不存在的产品名？
- [ ] 是否有新的重要产品未加入关键词？
- [ ] 关键词对应的公司/产品关系是否仍然正确？
```

---

## 信息源分类概览

| 类型 | 定义 | 检查频率 | 价值特点 | 数量 |
|------|------|---------|---------|------|
| **官方博客** | 公司官方发布渠道 | 每日/每周 | 一手信息, 产品更新 | 20+ |
| **Newsletter** | 个人/机构深度分析 | 每周2-3次 | 深度洞察, 趋势解读 | 20+ |
| **微信公众号** | 中文信息核心渠道 | 每日/每周 | 本土视角, 全面覆盖 | 50+ |
| **X/Twitter账号** | 关键人物动态 | 每日 | 最快信息源, 行业洞察 | 20+ |
| **播客** | 长对话, 深度访谈 | 每周 | 思想碰撞, 一手观点 | 15+ |
| **YouTube/B站** | 视频内容 | 每周 | 论文解读, 教程 | 13+ |
| **学术源** | 论文/评测/期刊 | 每周 | 前沿研究 | 15+ |
| **媒体** | 新闻/投融资报道 | 每日 | 市场动态, 资本信号 | 20+ |
| **社区/论坛** | 开源/讨论社区 | 每日/每周 | 技术讨论, 项目发现 | 10+ |
| **Discord社区** | 实时社区交流 | 按需 | 一手讨论, 产品反馈 | 10+ |

---

## 官方博客/研究页

### 模型实验室

| 公司 | URL | 检查频率 | 内容类型 |
|------|-----|---------|---------|
| **OpenAI** | openai.com/blog | 每周2次 | 产品发布, 安全研究 |
| **Anthropic** | anthropic.com/research | 每周2次 | 研究论文, 产品博客 |
| **Google DeepMind** | deepmind.google/research | 每周1次 | 研究论文, 技术突破 |
| **Meta AI** | ai.meta.com/blog | 每周1次 | Llama 系列, 开源 |
| **Mistral** | mistral.ai/news | 每周1次 | 开源模型, 商业化 |
| **DeepSeek** | github.com/deepseek-ai | 每周2次 | 开源模型, 论文 |

### AI Coding 产品（海外）

| 公司 | URL | 检查频率 | 内容类型 |
|------|-----|---------|---------|
| **Cursor** | cursor.com/blog, cursor.com/changelog | 每日 | 产品更新, 技术博客 |
| **GitHub (Copilot)** | github.blog | 每周1次 | Copilot 更新 |
| **Replit** | replit.com/blog | 每周1次 | Agent 编程 |
| **Cognition** | cognition.ai/blog | 每周1次 | Devin/Windsurf 进展 |

### AI Coding 产品（国内）

| 公司/产品 | URL | 检查频率 | 内容类型 |
|----------|-----|---------|---------|
| **Trae (字节)** | trae.ai / trae.cn | 每日 | 国内首个AI原生IDE, 产品更新 |
| **通义灵码 (阿里)** | tongyi.aliyun.com/lingma | 每周2次 | IDE插件更新, 模型升级 |
| **CodeBuddy (腾讯)** | codebuddy.qq.com | 每周2次 | AI原生IDE, 微信生态集成 |
| **Comate (百度)** | comate.baidu.com | 每周1次 | 企业级AI编程 |
| **CodeGeeX (智谱)** | codegeex.cn | 每周1次 | 开源代码模型, IDE插件 |
| **CodeFuse (蚂蚁)** | github.com/codefuse-ai | 每月1次 | 开源框架, 多模型支持 |

> ⚠️ 注意: MarsCode已于2025年更名为Trae，原marscode.cn已重定向到trae.ai

### 企业AI / Agent平台

| 公司 | URL | 检查频率 | 内容类型 |
|------|-----|---------|---------|
| **Salesforce** | salesforce.com/news | 每周1次 | Agentforce, 企业AI |
| **Glean** | glean.com/blog | 每周1次 | 企业搜索AI |
| **Sierra** | sierra.ai/blog | 每月1次 | 客服AI Agent |
| **ServiceNow** | servicenow.com/blogs | 每月1次 | IT服务AI |

### 视频/图像生成

| 公司 | URL | 检查频率 | 内容类型 |
|------|-----|---------|---------|
| **Runway** | research.runwayml.com | 每周1次 | 视频生成研究 |
| **Stability AI** | stability.ai/news | 每周1次 | 开源图像生成 |
| **ElevenLabs** | elevenlabs.io/blog | 每月1次 | 语音AI |

---

## Newsletter / 博客

### 海外顶级

| 名称 | 作者 | URL | 检查频率 | 价值定位 |
|------|------|-----|---------|---------|
| **Simon Willison's Blog** | Simon Willison | simonwillison.net | 每日 | 最及时的AI工具评测 |
| **The Pragmatic Engineer** | Gergely Orosz | newsletter.pragmaticengineer.com | 每周2次 | 最深入的工程视角 |
| **Latent Space** | Swyx | latent.space | 每周1次 | AI 工程前沿, 深度访谈 |
| **One Useful Thing** | Ethan Mollick | oneusefulthing.org | 每周2次 | AI 对工作方式的影响 |
| **Stratechery** | Ben Thompson | stratechery.com | 每周1次 | 商业战略分析 |

### AI工程/实践类

| 名称 | 作者 | URL | 检查频率 | 价值定位 |
|------|------|-----|---------|---------|
| **Eugene Yan Blog** | Eugene Yan | eugeneyan.com | 每周1次 | AI工程最佳实践 |
| **Chip Huyen Blog** | Chip Huyen | huyenchip.com | 每周1次 | ML系统设计 |
| **The Batch** | Andrew Ng | deeplearning.ai/the-batch | 每周1次 | AI教育+行业洞察 |
| **AI Snake Oil** | Arvind Narayanan | aisnakeoil.com | 每周1次 | AI批判性视角 |

### 高订阅量必读

| 名称 | URL | 订阅量 | 价值定位 |
|------|-----|--------|---------|
| **Import AI** | jack-clark.net | 顶级 | Anthropic联合创始人，AI政策+技术研究 |
| **Ben's Bites** | bensbites.com | 14万+ | 轻松风格的AI工具+新闻 |
| **The Rundown AI** | therundown.ai | 100万+ | 5分钟掌握AI动态，商业导向 |
| **Lenny's Newsletter** | lennysnewsletter.com | 100万+ | 产品策略+AI趋势，PM必读 |
| **There's An AI For That** | theresanaiforthat.com | 170万+ | AI工具聚合，发现新工具首选 |

### 中文圈

| 名称 | 作者 | 平台 | 检查频率 | 价值定位 |
|------|------|------|---------|---------|
| **宝玉的Twitter/公众号** | 宝玉 | X @dotey, 微信公众号 | 每日 | 最快的海外AI信息翻译 |
| **李沐论文精读** | 李沐 | YouTube / B站 | 每周1次 | 中文世界最好的论文解读 |

---

## 微信公众号

> **说明**: 微信公众号是中文AI信息的重要渠道，覆盖技术媒体、深度分析、学术解读等多个维度

### AI综合媒体（每日必读）

| 公众号 | 定位 | 价值 |
|--------|------|------|
| **机器之心** | AI技术媒体 | 最全面的AI技术新闻、论文解读 |
| **量子位** | AI综合媒体 | 国内AI新闻、产品评测、融资动态 |
| **新智元** | AI资讯媒体 | AI行业综合资讯、大模型动态 |
| **AI科技评论** | AI技术媒体 | 国内AI产业动态、学术会议 |
| **智东西** | 智能硬件+AI | AI硬件、机器人、智能汽车 |
| **雷峰网** | AI深度媒体 | 深度报道、人物访谈 |
| **极客公园** | 科技创新 | 科技创新报道、创业者访谈 |

### 深度洞察/商业分析（每周精读）

| 公众号 | 作者 | 价值 |
|--------|------|------|
| **宝玉** | 宝玉 @dotey | 最快的海外AI信息翻译 |
| **甲子光年** | 科技产业媒体 | AI产业深度研究、投融资分析 |
| **晚点LatePost** | 晚点团队 | 科技行业深度独家报道 |
| **潘乱/乱翻书** | 潘乱 | 中国互联网/AI行业深度分析 |
| **卫夕指北** | 卫夕 | 科技圈底层逻辑拆解 |
| **海外独角兽** | — | 硅谷创投深度报道 |
| **36氪** | 科技商业媒体 | AI投融资、商业分析 |
| **虎嗅** | 商业科技媒体 | 深度商业评论 |

### 大模型/技术深度（每周精读）

| 公众号 | 作者 | 价值 |
|--------|------|------|
| **符尧** | 大模型研究者 | 大模型技术深度、Scaling Law |
| **苏剑林科学空间** | 苏剑林 | NLP理论、大模型原理 |
| **PaperWeekly** | 学术社区 | 顶会论文解读、学术前沿 |
| **大模型日知录** | — | 大模型每日动态、论文速递 |

### AI产品/应用

| 公众号 | 价值 |
|--------|------|
| **AI产品经理大本营** | AI产品设计、落地案例、方法论 |
| **歸藏的AI工具箱** | AI工具深度测评、实用技巧 |
| **AI工具集** | AI工具推荐、使用教程 |

### 公司官方号

| 公众号 | 所属公司 | 检查频率 |
|--------|---------|---------|
| **智谱AI** | 智谱 | 每周2次 |
| **深度求索DeepSeek** | DeepSeek | 每周2次 |
| **月之暗面Moonshot** | 月之暗面 | 每周1次 |
| **字节跳动技术团队** | 字节跳动 | 每周1次 |
| **阿里云** | 阿里巴巴 | 每周1次 |
| **腾讯AI Lab** | 腾讯 | 每周1次 |
| **百度AI** | 百度 | 每周1次 |
| **蚂蚁技术AntTech** | 蚂蚁集团 | 每周1次 |
| **CodeGeeX** | 智谱AI | 每周2次 |
| **通义灵码** | 阿里云 | 每周1次 |
| **科大讯飞** | 科大讯飞 | 每周1次 |
| **微软亚洲研究院** | 微软 | 每周1次 |
| **谷歌黑板报** | Google | 每周1次 |

---

## 播客

### 海外必听

| 播客名 | 主持人 | 平台 | 价值定位 |
|--------|-------|------|---------|
| **Latent Space Podcast** | Swyx + Alessio | Apple/Spotify/YouTube | AI 工程最前沿访谈 |
| **Lex Fridman Podcast** | Lex Fridman | YouTube | 长对话, 深度思想交流 |
| **Cognitive Revolution** | Nathan Lebenz | Apple/Spotify | AI 深度访谈 |
| **All-In Podcast** | Chamath/Sacks等 | YouTube | 科技投资热点 |

### 中文播客

| 播客名 | 主持人 | 平台 | 价值定位 |
|--------|-------|------|---------|
| **硅谷101** | 泓君 | Apple/Spotify | 中文圈最好的硅谷科技播客 |
| **张小珺的播客** | 张小珺 | 小宇宙 | 中国科技创业深度访谈 |
| **晚点聊LateTalk** | 晚点 | 小宇宙 | 中国科技行业深度对话 |
| **疯投圈** | — | 小宇宙 | 创投视角, 商业分析 |

---

## YouTube / B站

### 海外频道

| 频道 | 创作者 | 检查频率 | 价值定位 |
|------|-------|---------|---------| 
| **Andrej Karpathy** | Andrej Karpathy | 按更新 | 技术深度教程 |
| **Yannic Kilcher** | Yannic Kilcher | 每周1次 | 最深入的论文解读 |
| **Two Minute Papers** | Károly Zsolnai-Fehér | 每周2次 | 最快的论文摘要 |
| **AI Explained** | — | 每周1次 | AI 新闻深度分析 |

### B站/国内

| UP主 | 粉丝量 | 内容定位 |
|------|--------|---------|
| **跟李沐学AI** | 100万+ | 论文精读、深度学习教程 |
| **同济子豪兄** | 20万+ | CV/深度学习、工程实践 |
| **3Blue1Brown中文** | — | 数学可视化、神经网络直观理解 |

---

## 学术/研究源

| 类型 | 平台 | URL | 检查频率 | 价值定位 |
|------|------|-----|---------|---------|
| **预印本** | ArXiv CS.AI/CL/LG | arxiv.org/list/cs.AI | 每周2次 | 最前沿论文 |
| **论文追踪** | Papers With Code | paperswithcode.com | 每周1次 | 论文+代码 |
| **模型排行** | Hugging Face Hub | huggingface.co/models | 每周1次 | 模型热度/新模型 |
| **评测排行** | LMSYS Leaderboard | chat.lmsys.org | 每周1次 | 模型对比评测 |

### 年度报告/行业研究

| 来源 | URL | 检查频率 | 价值定位 |
|------|-----|---------|---------|
| **State of AI Report** | stateof.ai | 每年10月 | 年度AI全景报告 |
| **AI Index Report** | hai.stanford.edu | 每年 | 学术权威AI指标 |
| **Sequoia AI 50** | sequoiacap.com | 每年 | AI投资热点公司 |
| **McKinsey AI Survey** | mckinsey.com | 每年 | 企业AI采纳调研 |

---

## 社区/开源

| 平台 | URL | 检查频率 | 价值定位 |
|------|-----|---------|---------|
| **GitHub Trending** | github.com/trending | 每日 | 开源热门项目 |
| **Hacker News** | news.ycombinator.com | 每日 | 技术社区热点 |
| **Reddit r/MachineLearning** | reddit.com/r/MachineLearning | 每周2次 | ML 社区讨论 |
| **Reddit r/LocalLLaMA** | reddit.com/r/LocalLLaMA | 每周2次 | 本地部署社区 |
| **Product Hunt AI** | producthunt.com | 每周2次 | AI产品发布 |

### Discord社区（重要）

> Discord是AI社区实时交流的主要平台，可获得产品更新、技术讨论、一手信息

| 社区 | 邀请链接 | 成员规模 | 价值定位 |
|------|---------|---------|---------|
| **OpenAI** | discord.gg/openai | 100万+ | ChatGPT/Sora官方社区，产品更新 |
| **Anthropic** | discord.gg/anthropic | 10万+ | Claude官方，MCP讨论、API支持 |
| **Hugging Face** | discord.gg/hugging-face | 20万+ | 开源ML社区，模型分享 |
| **Midjourney** | discord.gg/midjourney | 1500万+ | 最活跃的AI艺术社区 |

---

## X/Twitter 关键账号

### AI实验室领袖

| 账号 | 身份 | 关注价值 |
|------|------|---------|
| **@sama** | Sam Altman | OpenAI CEO，产品方向、行业观点 |
| **@DarioAmodei** | Dario Amodei | Anthropic CEO，AI安全思想领袖 |
| **@JeffDean** | Jeff Dean | Google AI负责人，技术突破 |
| **@ylecun** | Yann LeCun | Meta首席科学家，学术观点 |

### AI研究者/实践者

| 账号 | 身份 | 关注价值 |
|------|------|---------|
| **@karpathy** | Andrej Karpathy | 前OpenAI/Tesla，教育视频、技术洞察 |
| **@swyx** | Swyx | Latent Space主理人，AI工程前沿 |
| **@simonw** | Simon Willison | AI工具评测，LLM实践 |
| **@dotey** | 宝玉 | 海外AI信息翻译，中文圈必关注 |
| **@fchollet** | François Chollet | Keras创始人，AGI思考 |

---

## 媒体/投融资

### 海外科技媒体

| 媒体 | URL | 检查频率 |
|------|-----|---------|
| **TechCrunch** | techcrunch.com | 每日 |
| **The Verge** | theverge.com | 每日 |
| **MIT Technology Review** | technologyreview.com | 每周2次 |
| **Wired** | wired.com | 每周2次 |

### 投融资数据

| 媒体 | URL | 检查频率 | 内容 |
|------|-----|---------|------|
| **CB Insights** | cbinsights.com | 每周1次 | 全球 AI 投融资数据 |
| **IT桔子** | itjuzi.com | 每周1次 | 国内 AI 投融资 |

### 中文科技媒体

| 媒体 | URL | 检查频率 |
|------|-----|---------|
| **机器之心** | jiqizhixin.com | 每日 |
| **量子位** | qbitai.com | 每日 |
| **36氪** | 36kr.com | 每日 |
| **虎嗅** | huxiu.com | 每日 |

---

## 搜索执行策略

> ⚠️ **国内覆盖强制规则**: 国内搜索与海外搜索**分开执行**，各自独立完成，不允许"海外搜完就跳过国内"
> 每期日报国内新闻 ≥ 3条，海外:国内比例不超过 4:1

### 每日必做 — 海外部分

```bash
# L1 定向人物搜索（每天覆盖至少4组）

# OpenAI 团队（每日至少查1项）
site:openai.com/blog
"Jason Wei" OpenAI latest 2026

# Anthropic 团队（每日至少查1项）
site:anthropic.com/research
"Barry Zhang" anthropic 2026

# Cursor 团队（每日必查）
site:cursor.com/blog
site:cursor.com/changelog

# AI Coding 实践者（每日轮换2个）
"Addy Osmani" AI coding latest
"Andrej Karpathy" latest 2026

# L2 源直查（每日必做）
直查: simonwillison.net（最近文章）
site:simonwillison.net（最近7天）
```

### 每日必做 — 国内部分

```bash
# ━━━━ 维度1: 国内AI公司动态（每日至少查4组）━━━━

# 大模型公司（每日至少查2家）
DeepSeek 最新 发布 2026
Moonshot kimi 最新动态
智谱 GLM ChatGLM 最新
阿里 通义 千问 Qwen 最新
字节 豆包 最新 发布

# AI Coding产品（每日至少查2家）
Trae 字节 AI编程 最新
通义灵码 更新 发布
CodeBuddy 腾讯 AI编程
CodeGeeX 智谱 更新

# ━━━━ 维度2: 国内AI媒体报道（每日必查）━━━━

# 网页直查（每日必做）
site:jiqizhixin.com（今日）    # 机器之心
site:qbitai.com（今日）        # 量子位
site:36kr.com AI（今日）       # 36氪AI频道
site:ithome.com AI（今日）     # IT之家

# ━━━━ 维度3: 国内开发者社区（每日轮换）━━━━

# ⚠️ 禁用: CSDN、知乎回答
# ⚠️ 高危可用: 掘金（必须逐条验证发布日期）
site:sspai.com AI（最新）    # 少数派 ✅ 安全
site:juejin.cn AI（今日）    # 掘金 ⚠️ 需验证日期
```

### 每周深度

```bash
# L3 官方博客检查
直查: anthropic.com/research（新文章）
直查: openai.com/blog（新文章）
直查: deepmind.google/research（新文章）

# 长文/播客
"Dario Amodei" essay interview 2026
"Sam Altman" blog interview 2026

# 投融资专项
AI startup funding round 2026
中国 AI创业 融资 最新

# 国内政策/产业
中国 AI政策 监管 最新
中国 AI产业 报告 2026
```

---

## 覆盖均衡性原则

**每日 L1 轮换搜索必须覆盖以下至少 8 组**（防止信息窄化）：

### 海外必覆盖（≥5组）
1. 海外头部实验室（OpenAI / Anthropic / Google / Meta）至少 2 组
2. AI Coding 产品方（Cursor / Replit / Cognition 等）至少 1 家
3. 独立研究者 / AI Coding 实践者 至少 1 人
4. 企业AI/Agent创业公司（Glean / Sierra / Harvey 等）至少 1 家
5. X/Twitter关键账号（@karpathy / @sama / @ylecun 等）至少 2 个

### 国内必覆盖（≥4组）
6. **国内大模型公司**（DeepSeek / 智谱 / Moonshot / 百度 / 阿里 / 字节）至少 **2** 家
7. **国内AI Coding产品**（Trae / 通义灵码 / CodeBuddy / Comate）至少 **1** 家
8. **微信公众号**（机器之心 / 量子位 / 宝玉 等）至少 **3** 个
9. **国内科技媒体网站**（36氪 / IT之家 / 机器之心官网）至少 **1** 个

### 均衡性自检
- 每期日报完成后，统计海外:国内新闻条数
- 如比例超过 4:1，需要补充国内内容
- 如连续2天某板块无国内内容，下一天该板块必须优先搜索国内

---

*更新频率：每月 Review 一次，根据信息质量调整优先级*
