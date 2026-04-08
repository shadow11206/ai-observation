# Qwen3.5-Omni 的性能已到位，但「215项SOTA」是在精心选择的擂台上打的

**定价不是中国模型的护身符，而是战略武器。** Qwen3.5-Omni 文本输入 0.8元/百万 token，约为 Gemini 3.1 Pro（$2.00≈14.6元）的 **1/18**——但这个数字背后有三层被主流报道忽略的故事：benchmark 对比对象在表格中途被悄悄替换、权重闭源让本地部署完全不可能、以及"支持113种语言"的宣称中至少有一部分只是底层文本能力的溢出而非真正的多语言 TTS 训练。**价格战的真实目的不是让开发者省钱，而是让 Google 无法降价反制，因为 Google 同等幅度降价会直接吃掉 Cloud 利润。**

---

## 01. 背景与触发

2026年3月30日，阿里发布 Qwen3.5-Omni，包含 Plus/Flash/Light 三档，支持文本/图片/音频/音视频全模态输入，支持256k上下文、超过10小时音频、400秒720P视频。官博声称在215项音频/音视频子任务/benchmark中取得SOTA，"通用音频理解全面超越 Gemini-3.1 Pro，音视频理解总体达到 Gemini-3.1 Pro 水平"。

**定价**（中国内地，百炼平台，邀测期限时免费）：
- 文本/图片/视频输入：0.8元/百万 token
- 音频输入：约 4.96元/百万 token（上代 Qwen3-Omni-Flash 公开定价换算）
- 对比 Gemini 3.1 Pro：$2.00/百万 token（≈14.6元），$12.00 输出

*来源：[Qwen 官博](https://qwen.ai/blog?id=qwen3.5-omni)（2026-03-30，一手）；[Google AI Dev 定价页](https://ai.google.dev/gemini-api/docs/pricing)（实时截图，一手）*

---

## 02. 核心发现

### 1. 「215项SOTA」成立，但benchmark表格在中途换掉了对比对象

**发现**：Qwen 官博的 benchmark 表格在音视频评测中以 Gemini-3.1 Pro 为对比基准；但在音频和视觉部分，对比对象悄然变成了 Gemini-3 Pro 和 Gemini-2.5 Pro（均是更老/更弱的版本）。

**数据**：
- Reddit 上批评此事的评论获得 **74票**，是整个帖子最高赞的批评性评论（sittingmongoose）："They changed the models they benchmarked against on the right as you go down…that's super misleading."
- IBM296（30票）追问："Why suddenly compare with Gemini 3 Pro and 2.5 Pro instead of 3.1 Pro like before."
- 部分用户为 Alibaba 辩护：PuppyGirlEfina（33票）指出"2.5 Pro 是 TTS 领域最新版，他们没发新 TTS 版本"——但这个辩护本身说明在语音生成领域，Gemini 并没有发布 3.1 的 TTS 模型

**判断**：215项SOTA的数字是真实的，但它是在精心构建的擂台上打出来的。在核心音视频理解评测中（DailyOmni、Omni-Cloze），Qwen3.5-Omni-Plus 确实胜出 Gemini 3.1 Pro；但在 WorldSense（65.5 vs 62.8）、VideoMME（89.0 vs 83.7）、OmniGAIA（68.9 vs 57.2）上，Gemini 3.1 Pro 依然领先。"总体达到水平"≠"全面超越"。

*来源：Qwen 官博 benchmark 表格（一手）；Reddit r/LocalLLaMA（292票帖，独立）*

---

### 2. 权重闭源：定价屠刀是 API 生意，不是开源生态

**发现**：Qwen3.5-Omni 全系列权重闭源，不提供本地部署支持。

**数据**：
- Reddit 帖子（HF Demo版）最高赞评论：coder543（**53票**）"But it is closed weights, which is disappointing."
- 帖子中多名工程师追问何时开放，官方博客只字未提权重发布计划
- 对比前代 Qwen3.5（文本版）：已开源，Hugging Face 上大量第三方蒸馏版（如 `Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled`）下载量超百万

**判断**：这是一个关键的战略分野。Qwen3.5 文本版开源制造生态飞轮；Omni 多模态闭源做 API 收入。这不是矛盾，而是分层商业化策略——用开源文本模型统治 HF/GitHub 开发者心智，用闭源 Omni 在企业 API 市场收费。但这意味着：Qwen3.5-Omni 的定价优势只对 API 调用用户有效，工程师社区对此兴趣有限，HN 上至今**零评论**就是信号。

*来源：Reddit r/LocalLLaMA coder543 评论（独立，53票）；HN 搜索结果（独立）*

---

### 3. 「113种语言支持」有水分：稀有语言TTS实测极差

**发现**：一名 Reddit 用户系统测试了拉脱维亚语（Latvian，属欧洲小语种）的音频输入输出，ASR 识别准确、文字回复正常，但**音频输出发音质量极差**，"字面上是我听过最差的，即使练了一周的人发音也比这好"。

**数据**：No-Refrigerator-1672 的完整实测（独立，有细节）：
- 音频输入识别正确 ✓
- 文字回复质量与普通 Qwen3.5-35B 相当 ✓
- **音频输出：literally the worst I've ever heard**（最差的发音）✗
- 结论：所谓多语言支持，只是底层文本 LLM 的多语言能力，在 TTS 编码器层面没有真正训练过这些稀有语言

**判断**：Qwen3.5-Omni 的语音能力存在明显的"头部语言强、长尾语言差"的双峰分布。官方 benchmark 里的 Fleurs 59语言、Librispeech 等都是主流语言，稀有语言完全没有进入评测。"113种语言识别 + 36种语音生成"的宣传措辞需要打折理解。实际上，在主流语言（中文、英文、粤语、日语等）的 ASR 评测中，Qwen3.5-Omni-Plus 的 WER 确实全面优于 Gemini-3.1 Pro（Fleurs WER: 6.55 vs 7.32；Librispeech clean WER: 1.11 vs 3.36）——主流语言是真实力，稀有语言是水分。

*来源：Reddit r/LocalLLaMA No-Refrigerator-1672 实测评论（独立）；Qwen 官博 ASR benchmark 表格（一手）*

---

### 4. 定价是战略武器：目的是让Google无法降价反制

**发现**：Qwen3.5-Omni 文本输入 0.8元（≈$0.055），约为 Gemini 3.1 Pro 的 1/36（按美元）；即使对比 Gemini 3 Flash（$0.50），Qwen 依然低约 9倍。

**数据**：
| 模型 | 文本输入（/百万 token） | 输出（/百万 token） |
|------|----------------------|-------------------|
| Qwen3.5-Omni-Plus（中国内地） | **¥0.8（≈$0.055）** | ¥9.6（≈$0.66）|
| Gemini 3.1 Pro | $2.00 | $12.00 |
| Gemini 3 Flash | $0.50 | $3.00 |
| Gemini 3.1 Flash-Lite | $0.25 | $1.50 |

*来源：阿里云百炼定价页（一手）；Google AI Dev 定价页（一手）*

**判断**：这个价格差本身就是不对称竞争的杠杆。Google 如果降价到接近 Qwen 的水平，会直接冲击 Google Cloud 的利润（Cloud 是 Alphabet 核心现金牛），这是结构性不对称。中国厂商用 API 收入补贴定价是可行的（尤其是邀测期免费、后续正式定价仍有成本优势），Google 没有这个灵活度。这个价格不只是"便宜"，它是在 Google 无法还手的位置插刀。

---

### 5. 真正的全球市场渗透信号：OmniGAIA 评分揭示的能力天花板

**发现**：在 OmniGAIA（工具使用/Agent 任务）评测中，Gemini 3.1 Pro **68.9** vs Qwen3.5-Omni-Plus **57.2**，差距明显。这是 benchmark 表格里差距最大的一项（-11.7）。

**数据**：OmniGAIA 是测试模型在复杂音视频 Agent 场景下调用工具完成任务的能力，直接对应企业级自动化场景。

**判断**：在多模态 Agent 能力上，Gemini 3.1 Pro 仍然领先超过 10 个百分点。这意味着 Qwen3.5-Omni 在理解和生成层面已经接近对标，但在「让 AI 自主完成复杂任务」这个维度上仍有差距。对企业买家来说，这是实质性的区别——一个做理解的模型和一个能自主行动的 Agent 是完全不同的产品价值。Qwen 的定价优势在简单 API 调用场景极具吸引力，但无法覆盖需要 Agent 能力的高价值场景。

*来源：Qwen 官博 OmniGAIA benchmark 数据（一手）*

---

## 03. 四层穿透分析

**L1 现象**：Qwen3.5-Omni 在音频理解领域的主流评测中全面超越 Gemini-3.1 Pro，定价约为其 1/18（人民币），在中国内地通过百炼平台提供 API 服务；权重闭源，HN 零评论，Reddit 最高赞批评集中在 benchmark 对比对象被替换和权重闭源两点。

**L2 机制**：① Hybrid-Attention MoE 架构是低成本的技术来源，推理时只激活部分参数，单次推理成本远低于 Dense 模型——这是 DeepSeek-v3 体系的延伸，中国厂商在 MoE 工程化上已形成体系性积累；② 权重闭源是商业化策略，不是技术原因——Qwen3.5 文本版开源，Omni 闭源，是分层变现；③ Gemini 降价空间受限：Google Cloud 毛利率核心依赖，不能为了 AI API 市场份额牺牲 Cloud 利润；④ HN 零评论 vs Reddit 292票：说明工程师对它的兴趣停在"看"阶段，不是"用"阶段——闭源是主因。

**L3 洞察**：哥看完日报会漏掉的判断——**「215项SOTA」的真正意义不是性能，而是 PR 策略**。阿里知道这个模型在 Agent 能力上输给 Gemini，所以刻意选择了 ASR、S2TT、语音生成这些细分评测来堆出215个SOTA，并在视觉/文本部分换掉了对比对象。这是典型的"benchmark engineering"——不是造假，而是选题目。真正的竞争差距在 OmniGAIA（-11.7分）上，这一项直接对应企业 Agent 采购决策。**定价上的碾压是真实的；性能上的"对标"是精心演出的。**

**L4 趋势**：
- **乐观路径**：Qwen3.5-Omni 在内容理解（视频字幕、音频转写、多语言 ASR）这些不需要 Agent 能力的场景上，未来6个月内会拿下大量 API 份额——尤其是海外开发者通过 OpenRouter 使用，定价优势极端显著；
- **风险路径**：如果 Google 加速推进 Gemini 3.1 Pro 在 Agent 和工具调用上的能力（OmniGAIA 从 68.9 继续拉大），Qwen 在高价值 Agent 场景会长期缺位，被困在"便宜但做不了复杂事情"的低端市场；权重若长期不开源，工程师社区的冷淡将成为生态建设的天花板。

---

## 04. 原创框架

**「定价护城河 vs 能力护城河」的双轨竞争**

多模态 AI 竞争正在分化为两个完全不同的竞争轨道：
1. **定价护城河轨道**：Qwen3.5-Omni、MiniMax、阶跃星辰——用 MoE 架构把成本打到 Google 无法还手的水平，抢占内容处理、批量 ASR/S2TT 等高频调用场景；
2. **能力护城河轨道**：Gemini 3.1 Pro、GPT-4o——在 Agent 任务、复杂工具调用上保持能力领先，锁定愿意付高价的企业 Agent 采购预算。

这两条轨道的买家是不同的人：前者是开发者/内容公司；后者是企业 IT 决策者。中国厂商的策略如果能同时在两条轨道上竞争（既便宜又能做 Agent），就能打赢。但目前 OmniGAIA 的数据说明他们只拿下了第一条轨道。

---

## 05. 判断更新

**关联问题**：`04-opinion-log/model-landscape.md`

**调研前判断（上一版）**：中国多模态已进入「价格+性能」双轮驱动阶段，竞争叙事从"追赶"变"压制"。信心：★★★★☆

**调研后更新**：判断需要细化——**「压制」只发生在内容处理轨道上，不发生在 Agent 能力轨道**。Gemini 3.1 Pro 在 OmniGAIA 上的优势（68.9 vs 57.2）是一个高价值场景的护城河，中国厂商暂时没有突破。与此同时，权重闭源策略让工程师社区的参与度极低（HN 零评论），生态飞轮尚未转起来。上一版过于乐观，需要引入"双轨竞争"的分析框架，分场景给出判断。

**信心变化**：信心不降，但判断颗粒度从★★★★（整体领先）→ ★★★★（内容处理领域领先，Agent 领域落后）

**核心驱动**：OmniGAIA benchmark 一手数据（官博）+ Reddit 工程师实测（社区独立）+ benchmark 对比对象替换的质疑（74票，独立）

---

*调研日期：2026-03-31 | 一手来源：4 个（官博 benchmark、Gemini 定价页、阿里云百炼定价）| 独立来源：3 个（Reddit 292票帖、HN 搜索、Reddit 实测）| 反面证据：3 条（OmniGAIA 差距、benchmark 换对象、稀有语言 TTS 极差）*
