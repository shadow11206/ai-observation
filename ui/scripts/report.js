/**
 * report.js — 日报详情页
 * 读取 URL 参数 ?date=YYYY-MM-DD，加载对应的 JSON 日报并渲染 6 个模块
 */

const REPORTS_BASE = '../01-daily-reports';

// 解析 URL 参数
function getDateParam() {
  const params = new URLSearchParams(window.location.search);
  return params.get('date') || getTodayStr();
}

function getTodayStr() {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function getMonthStr(dateStr) {
  return dateStr.slice(0, 7);
}

function formatDateLabel(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日 · 星期${weekdays[d.getDay()]}`;
}

// 渲染函数 —— 6 个模块
function renderReport(data) {
  const content = document.getElementById('report-content');
  const loading = document.getElementById('loading');
  if (loading) loading.remove();

  // 更新头部
  const dateLabel = formatDateLabel(data.date);
  document.title = `${data.date} 日报 — AI Observation`;
  document.getElementById('header-eyebrow').textContent = dateLabel;
  document.getElementById('header-title').textContent = data.summary_one_line || 'AI 日报';
  document.getElementById('header-summary').textContent = '';
  document.getElementById('sidebar-date').textContent = dateLabel;
  document.getElementById('sidebar-summary').textContent = data.summary_one_line || '';

  content.innerHTML = `
    ${renderTopItems(data.top_items || [])}
    ${renderModelTech(data.model_tech || [])}
    ${renderCompany(data.company_product || [])}
    ${renderOpinions(data.opinions || [])}
    ${renderDeepDive(data.deep_dive_suggestions || [])}
    ${renderSnapshot(data.snapshot || {})}
  `;

  // 初始化侧边栏高亮
  initSidebarHighlight();
}

function renderTopItems(items) {
  return `
    <section id="top-items">
      <h2 class="section-title"><span class="section-icon">📌</span> 今日最重要</h2>
      ${items.length === 0
        ? '<div class="section-empty">今日暂无重点内容</div>'
        : items.map(item => `
          <div class="top-item">
            <div class="top-item-rank">${String(item.rank ?? 1).padStart(2, '0')}</div>
            <div style="flex:1;min-width:0">
              <div class="top-item-title">${item.title || ''}</div>
              ${item.finding ? `<div class="top-item-finding"><span class="finding-label">核心发现</span>${item.finding}</div>` : ''}
              ${(item.key_data || []).length ? `
                <div class="key-data-row">
                  <span class="finding-label">关键数据</span>
                  <div class="key-data-chips">${(item.key_data || []).map(d => `<span class="key-chip">${d}</span>`).join('')}</div>
                </div>` : ''}
              ${item.judgment ? `<div class="top-item-judgment"><span class="finding-label judgment-label">影响判断</span>${item.judgment}</div>` : ''}
              <div class="top-item-footer">
                <div class="top-item-meta">
                  ${item.source ? `<span style="font-size:12px;color:var(--text-tertiary)">来源：${item.source}</span>` : ''}
                  ${item.confidence ? `<span class="confidence-stars">${'★'.repeat(item.confidence)}${'☆'.repeat(5 - item.confidence)}</span>` : ''}
                </div>
                ${item.url ? `<a href="${item.url}" target="_blank" rel="noopener" class="source-btn">原文 →</a>` : ''}
              </div>
            </div>
          </div>
        `).join('')}
    </section>
  `;
}

function renderNewsCard(item) {
  return `
    <div class="news-item">
      <div class="news-item-header">
        <div class="news-item-title">${item.title || ''}</div>
        <div class="news-importance">${'⭐'.repeat(Math.min(Math.max(item.importance || 2, 1), 5))}</div>
      </div>
      <div class="news-item-source">${item.source || ''}</div>
      ${item.finding ? `<div class="news-finding"><span class="finding-label">核心发现</span>${item.finding}</div>` : (item.summary ? `<div class="news-item-summary">${item.summary}</div>` : '')}
      ${(item.key_data || []).length ? `
        <div class="key-data-row">
          <span class="finding-label">关键数据</span>
          <div class="key-data-chips">${(item.key_data || []).map(d => `<span class="key-chip">${d}</span>`).join('')}</div>
        </div>` : ''}
      ${item.judgment ? `<div class="news-judgment"><span class="finding-label judgment-label">影响判断</span>${item.judgment}</div>` : ''}
      <div class="news-item-footer">
        ${item.confidence ? `<span class="confidence-stars">${'★'.repeat(item.confidence)}${'☆'.repeat(5 - item.confidence)}</span>` : '<span></span>'}
        ${item.url ? `<a href="${item.url}" target="_blank" rel="noopener" class="source-btn">原文 →</a>` : ''}
      </div>
    </div>
  `;
}

function renderModelTech(items) {
  return `
    <section id="model-tech">
      <h2 class="section-title"><span class="section-icon">🔬</span> 模型 / 技术动态</h2>
      ${items.length === 0
        ? '<div class="section-empty">今日无值得关注的模型技术动态</div>'
        : items.map(item => renderNewsCard(item)).join('')}
    </section>
  `;
}

function renderCompany(items) {
  return `
    <section id="company">
      <h2 class="section-title"><span class="section-icon">🏢</span> 公司 / 产品动态</h2>
      ${items.length === 0
        ? '<div class="section-empty">今日无值得关注的公司产品动态</div>'
        : items.map(item => renderNewsCard(item)).join('')}
    </section>
  `;
}


function renderOpinions(items) {
  return `
    <section id="opinions">
      <h2 class="section-title"><span class="section-icon">💡</span> 追踪人物观点</h2>
      ${items.length === 0
        ? '<div class="section-empty">今日追踪人物无新公开发言（Twitter 等社交媒体将在 Level 2 升级后接入）</div>'
        : items.map(op => `
          <div class="opinion-item">
            <div class="opinion-item-header">
              <span class="person-level level-${(op.level || 'L2').toLowerCase()}">${op.level || 'L2'}</span>
              <span class="opinion-person">${op.person || ''}</span>
              ${op.source ? `<a href="${op.source}" target="_blank" rel="noopener" style="font-size:12px;color:var(--accent);margin-left:auto">来源 →</a>` : ''}
            </div>
            <div class="opinion-quote">${op.quote || ''}</div>
          </div>
        `).join('')}
    </section>
  `;
}

function renderDeepDive(items) {
  return `
    <section id="deep-dive">
      <h2 class="section-title"><span class="section-icon">🔭</span> 值得深挖？</h2>
      ${items.length === 0
        ? '<div class="section-empty">今日无特别建议深挖的话题</div>'
        : items.map(item => `
          <div class="deep-dive-item">
            <div>
              <span class="deep-dive-priority priority-${item.priority || 'medium'}">${item.priority === 'high' ? '高优先' : '建议'}</span>
            </div>
            <div>
              <div class="deep-dive-topic">${item.topic || ''}</div>
              <div class="deep-dive-reason">${item.reason || ''}</div>
            </div>
          </div>
        `).join('')}
    </section>
  `;
}

// ── 数据快照辅助 ──────────────────────────────────────
// pipeline_tag → 中文说明（前端 fallback，覆盖旧数据没有 label 字段的情况）
const PIPELINE_LABEL = {
  'text-generation': '文本生成',
  'text2text-generation': '文本生成',
  'image-text-to-text': '多模态理解',
  'image-to-text': '图片描述',
  'text-to-image': '文生图',
  'text-to-video': '文生视频',
  'image-to-video': '图生视频',
  'text-to-speech': '文字转语音',
  'automatic-speech-recognition': '语音识别',
  'feature-extraction': '向量嵌入',
  'sentence-similarity': '语义相似度',
  'token-classification': '命名实体识别',
  'translation': '翻译',
  'summarization': '摘要生成',
  'question-answering': '问答',
  'image-classification': '图像分类',
  'object-detection': '目标检测',
  'depth-estimation': '深度估计',
};

function getModelLabel(m) {
  if (m.label) return m.label;
  if (m.pipeline_tag) return PIPELINE_LABEL[m.pipeline_tag] || m.pipeline_tag;
  // fallback：从 tags 里猜
  const tags = m.tags || [];
  if (tags.includes('text-to-speech') || tags.includes('tts')) return '文字转语音';
  if (tags.includes('text-to-video')) return '文生视频';
  if (tags.includes('image-text-to-video')) return '图生视频';
  if (tags.includes('gguf') || tags.includes('safetensors')) return '开源模型';
  if (tags.includes('asr') || tags.includes('cohere_asr')) return '语音识别';
  return '';
}

function getModelShortName(m) {
  if (m.short_name) return m.short_name;
  const name = m.name || '';
  return name.includes('/') ? name.split('/')[1] : name;
}

function getTrendBadge(m) {
  if (m.trend === 'new') return '<span style="font-size:10px;font-weight:600;color:#fff;background:#34C759;border-radius:4px;padding:1px 5px;letter-spacing:0.03em;">NEW</span>';
  if (m.trend === 'same') return '<span style="font-size:11px;color:var(--text-tertiary)">连续上榜</span>';
  return '';
}

function renderSnapshot(snapshot) {
  const hf = snapshot.hf_trending || [];
  const gh = snapshot.github_trending || [];
  const hfSummary = snapshot.hf_summary || '';

  // 连续上榜模型（trend === 'same'）
  const continuousModels = hf.filter(m => m.trend === 'same');

  return `
    <section id="snapshot">
      <h2 class="section-title"><span class="section-icon">⚡</span> 今日数据快照</h2>

      ${hf.length === 0 ? '<div style="font-size:13px;color:var(--text-tertiary);padding:1rem 0">暂无数据</div>' : `

        ${hfSummary ? `
          <div style="font-size:14px;color:var(--text-secondary);background:var(--bg-card);border-radius:10px;padding:0.75rem 1rem;margin-bottom:1.25rem;line-height:1.6;">
            💬 ${hfSummary}
          </div>` : ''}

        ${continuousModels.length > 0 ? `
          <div style="font-size:12px;font-weight:600;color:var(--text-tertiary);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.6rem;">连续上榜</div>
          <div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin-bottom:1.25rem;">
            ${continuousModels.map(m => `
              <a href="${m.url || '#'}" target="_blank" rel="noopener"
                style="font-size:12px;color:var(--accent);background:rgba(0,122,255,0.06);border:1px solid rgba(0,122,255,0.15);border-radius:6px;padding:2px 8px;text-decoration:none;white-space:nowrap;">
                ${getModelShortName(m)}
              </a>`).join('')}
          </div>` : ''}

        <div style="font-size:12px;font-weight:600;color:var(--text-tertiary);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.6rem;">Hugging Face Trending</div>
        <div style="background:var(--bg-card);border-radius:12px;overflow:hidden;">
          ${hf.slice(0, 8).map((m, i) => {
            const label = getModelLabel(m);
            const shortName = getModelShortName(m);
            const org = m.name && m.name.includes('/') ? m.name.split('/')[0] : '';
            const trendBadge = getTrendBadge(m);
            return `
              <div style="display:flex;align-items:center;gap:0.75rem;padding:0.7rem 1rem;${i > 0 ? 'border-top:1px solid var(--border-light)' : ''}">
                <div style="font-size:13px;font-weight:500;color:var(--text-tertiary);min-width:1.25rem;text-align:right;">${i + 1}</div>
                <div style="flex:1;min-width:0;">
                  <div style="display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap;">
                    <a href="${m.url || '#'}" target="_blank" rel="noopener"
                      style="font-size:14px;font-weight:600;color:var(--text-primary);text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:280px;"
                      title="${m.name || ''}">${shortName}</a>
                    ${trendBadge}
                  </div>
                  <div style="display:flex;align-items:center;gap:0.5rem;margin-top:2px;flex-wrap:wrap;">
                    ${org ? `<span style="font-size:11px;color:var(--text-tertiary);">${org}</span>` : ''}
                    ${label ? `<span style="font-size:11px;color:#fff;background:var(--accent);border-radius:4px;padding:0px 5px;">${label}</span>` : ''}
                    ${m.card_desc ? `<span style="font-size:11px;color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px;">${m.card_desc}</span>` : ''}
                  </div>
                </div>
                <div style="font-size:13px;color:var(--text-tertiary);white-space:nowrap;">
                  ❤️ ${(m.likes || 0).toLocaleString()}
                </div>
              </div>`;
          }).join('')}
        </div>

        ${gh.length > 0 ? `
          <div style="font-size:12px;font-weight:600;color:var(--text-tertiary);letter-spacing:0.08em;text-transform:uppercase;margin:1.25rem 0 0.6rem;">GitHub Trending AI</div>
          <div style="background:var(--bg-card);border-radius:12px;overflow:hidden;">
            ${gh.slice(0, 5).map((r, i) => `
              <div style="display:flex;align-items:flex-start;gap:0.75rem;padding:0.7rem 1rem;${i > 0 ? 'border-top:1px solid var(--border-light)' : ''}">
                <div style="flex:1;min-width:0;">
                  <a href="${r.url || '#'}" target="_blank" rel="noopener"
                    style="font-size:14px;font-weight:600;color:var(--text-primary);text-decoration:none;">${r.name || ''}</a>
                  ${r.desc ? `<div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">${r.desc}</div>` : ''}
                </div>
                <div style="font-size:12px;color:var(--text-tertiary);white-space:nowrap;">⭐ ${(r.stars || 0).toLocaleString()} · ${r.language || '—'}</div>
              </div>`).join('')}
          </div>` : ''}

        ${(snapshot.openrouter_ranking || []).length > 0 ? (() => {
          const or = snapshot.openrouter_ranking;
          return `
            <div style="font-size:12px;font-weight:600;color:var(--text-tertiary);letter-spacing:0.08em;text-transform:uppercase;margin:1.25rem 0 0.6rem;">
              OpenRouter · 模型调用排行
              <a href="https://openrouter.ai/rankings?view=day" target="_blank" rel="noopener"
                style="font-size:11px;font-weight:400;color:var(--accent);text-transform:none;margin-left:0.5rem;text-decoration:none;">查看完整榜单 →</a>
            </div>
            <div style="background:var(--bg-card);border-radius:12px;overflow:hidden;">
              ${or.slice(0, 10).map((m, i) => {
                const changeColor = m.change > 0 ? '#34C759' : m.change < 0 ? '#FF3B30' : 'var(--text-tertiary)';
                const changeStr = m.change > 0 ? `+${m.change}%` : `${m.change}%`;
                return `
                  <div style="display:flex;align-items:center;gap:0.75rem;padding:0.65rem 1rem;${i > 0 ? 'border-top:1px solid var(--border-light)' : ''}">
                    <div style="font-size:12px;font-weight:500;color:var(--text-tertiary);min-width:1.25rem;text-align:right;">${m.rank}</div>
                    <div style="flex:1;min-width:0;">
                      <div style="display:flex;align-items:baseline;gap:0.35rem;">
                        <a href="${m.url || '#'}" target="_blank" rel="noopener"
                          style="font-size:14px;font-weight:600;color:var(--text-primary);text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px;"
                          title="${m.slug || ''}">${m.name || ''}</a>
                        <span style="font-size:11px;color:var(--text-tertiary);">${m.org || ''}</span>
                      </div>
                    </div>
                    <div style="display:flex;align-items:center;gap:0.6rem;white-space:nowrap;">
                      <span style="font-size:12px;color:var(--text-secondary);">${m.total_tokens_str || ''}</span>
                      <span style="font-size:11px;font-weight:600;color:${changeColor};">${changeStr}</span>
                    </div>
                  </div>`;
              }).join('')}
            </div>`;
        })() : ''}
      `}
    </section>
  `;
}

// 侧边栏滚动高亮
function initSidebarHighlight() {
  const sections = document.querySelectorAll('.report-content section[id]');
  const navLinks = document.querySelectorAll('.sidebar-nav a');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        navLinks.forEach(link => {
          link.classList.toggle('active', link.getAttribute('href') === `#${entry.target.id}`);
        });
      }
    });
  }, { rootMargin: '-20% 0px -70% 0px' });

  sections.forEach(s => observer.observe(s));
}

// 错误状态
function renderError(dateStr) {
  const content = document.getElementById('report-content');
  const loading = document.getElementById('loading');
  if (loading) loading.remove();

  document.getElementById('header-title').textContent = `${dateStr} 日报`;
  document.getElementById('header-summary').textContent = '当日日报尚未生成，请明天再来查看';

  content.innerHTML = `
    <div style="padding:4rem 0; text-align:center; color:var(--text-tertiary);">
      <div style="font-size:3rem; margin-bottom:1rem;">📭</div>
      <div style="font-size:16px; margin-bottom:0.5rem;">${dateStr} 的日报暂未生成</div>
      <div style="font-size:14px; margin-bottom:2rem;">日报由 GitHub Actions 每天 09:00 自动生成</div>
      <a href="daily.html" class="btn-ghost" style="display:inline-flex;">← 返回日报列表</a>
    </div>
  `;
}

// 主流程
async function init() {
  const dateStr = getDateParam();
  const month = getMonthStr(dateStr);
  const url = `${REPORTS_BASE}/${month}/${dateStr}.json`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderReport(data);
  } catch (e) {
    console.warn('日报加载失败：', e);
    renderError(dateStr);
  }
}

init();
