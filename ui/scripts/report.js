/**
 * report.js — 日报详情页
 * 读取 URL 参数 ?date=YYYY-MM-DD，加载对应的 JSON 日报并渲染各模块
 */

const REPORTS_BASE = '../01-daily-reports';

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

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── 渲染主函数 ──────────────────────────────────────────────────
function renderReport(data) {
  const content = document.getElementById('report-content');
  const loading = document.getElementById('loading');
  if (loading) loading.remove();

  const dateLabel = formatDateLabel(data.date);
  document.title = `${data.date} 日报 — AI Observation`;
  document.getElementById('header-eyebrow').textContent = dateLabel;
  document.getElementById('header-title').textContent = data.summary_one_line || 'AI 日报';
  document.getElementById('header-summary').textContent = '';
  document.getElementById('sidebar-date').textContent = dateLabel;
  document.getElementById('sidebar-summary').textContent = data.summary_one_line || '';

  content.innerHTML = [
    renderTopItems(data.top_items || []),
    renderModelTech(data.model_tech || []),
    renderCompany(data.company_product || []),
    // opinions 模块：现阶段数据质量不足，暂时隐藏
    renderDeepDive(data.deep_dive_suggestions || []),
    renderSnapshot(data.snapshot || {}),
  ].join('');

  initSidebarHighlight();
}

// ── 今日最重要 ──────────────────────────────────────────────────
function renderTopItems(items) {
  return `
    <section id="top-items">
      <h2 class="section-title"><span class="section-icon">📌</span> 今日最重要</h2>
      ${items.length === 0
        ? '<div class="section-empty">今日暂无重点内容</div>'
        : items.map((item, idx) => `
          <div class="top-item">
            <div class="top-item-rank">${String((item.rank ?? idx + 1)).padStart(2, '0')}</div>
            <div class="top-item-body">
              <div class="top-item-title">${esc(item.title)}</div>
              ${item.finding ? `
                <div class="item-row">
                  <span class="row-label finding">核心发现</span>
                  <span class="row-text">${esc(item.finding)}</span>
                </div>` : ''}
              ${(item.key_data || []).length ? `
                <div class="item-row">
                  <span class="row-label key">关键数据</span>
                  <div class="chips">${(item.key_data || []).map(d => `<span class="chip">${esc(d)}</span>`).join('')}</div>
                </div>` : ''}
              ${item.judgment ? `
                <div class="judgment-block">
                  <span class="row-label judgment">影响判断</span>
                  <span class="row-text">${esc(item.judgment)}</span>
                </div>` : ''}
              <div class="item-footer">
                ${item.source ? `<span class="item-source">来源：${esc(item.source)}</span>` : '<span></span>'}
                ${item.url ? `<a href="${item.url}" target="_blank" rel="noopener" class="source-link">原文 →</a>` : ''}
              </div>
            </div>
          </div>
        `).join('')}
    </section>`;
}

// ── 通用新闻卡片（模型技术 / 公司产品共用）──────────────────────
function renderNewsCard(item) {
  return `
    <div class="news-card">
      <div class="news-card-header">
        <div class="news-card-title">${esc(item.title)}</div>
        ${item.importance ? `<div class="news-stars">${'★'.repeat(Math.min(Math.max(item.importance, 1), 5))}</div>` : ''}
      </div>
      <div class="news-card-source">${esc(item.source || '')}</div>
      ${item.finding ? `
        <div class="item-row">
          <span class="row-label finding">核心发现</span>
          <span class="row-text">${esc(item.finding)}</span>
        </div>` : (item.summary ? `<div class="news-card-summary">${esc(item.summary)}</div>` : '')}
      ${(item.key_data || []).length ? `
        <div class="item-row">
          <span class="row-label key">关键数据</span>
          <div class="chips">${(item.key_data || []).map(d => `<span class="chip">${esc(d)}</span>`).join('')}</div>
        </div>` : ''}
      ${item.judgment ? `
        <div class="judgment-block">
          <span class="row-label judgment">影响判断</span>
          <span class="row-text">${esc(item.judgment)}</span>
        </div>` : ''}
      <div class="item-footer">
        <span></span>
        ${item.url ? `<a href="${item.url}" target="_blank" rel="noopener" class="source-link">原文 →</a>` : ''}
      </div>
    </div>`;
}

function renderModelTech(items) {
  return `
    <section id="model-tech">
      <h2 class="section-title"><span class="section-icon">🔬</span> 模型 / 技术动态</h2>
      ${items.length === 0
        ? '<div class="section-empty">今日无值得关注的模型技术动态</div>'
        : items.map(item => renderNewsCard(item)).join('')}
    </section>`;
}

function renderCompany(items) {
  return `
    <section id="company">
      <h2 class="section-title"><span class="section-icon">🏢</span> 公司 / 产品动态</h2>
      ${items.length === 0
        ? '<div class="section-empty">今日无值得关注的公司产品动态</div>'
        : items.map(item => renderNewsCard(item)).join('')}
    </section>`;
}

// ── 值得深挖 ──────────────────────────────────────────────────
function renderDeepDive(items) {
  return `
    <section id="deep-dive">
      <h2 class="section-title"><span class="section-icon">🔭</span> 值得深挖？</h2>
      ${items.length === 0
        ? '<div class="section-empty">今日无特别建议深挖的话题</div>'
        : items.map(item => `
          <div class="deep-dive-item">
            <span class="deep-dive-priority priority-${item.priority || 'medium'}">${item.priority === 'high' ? '高优先' : '建议'}</span>
            <div>
              <div class="deep-dive-topic">${esc(item.topic)}</div>
              <div class="deep-dive-reason">${esc(item.reason)}</div>
            </div>
          </div>
        `).join('')}
    </section>`;
}

// ── 数据快照 ──────────────────────────────────────────────────
function renderSnapshot(snapshot) {
  const hf = snapshot.hf_trending || [];
  const gh = snapshot.github_trending || [];
  return `
    <section id="snapshot">
      <h2 class="section-title"><span class="section-icon">⚡</span> 今日数据快照</h2>
      <div class="snapshot-grid">
        <div class="snapshot-panel">
          <div class="snapshot-panel-title">Hugging Face Trending</div>
          ${hf.length === 0
            ? '<div style="font-size:13px;color:var(--text-tertiary);padding:0.5rem 0">暂无数据</div>'
            : hf.slice(0, 6).map(m => `
              <div class="snapshot-item">
                <div class="snapshot-item-name">
                  ${m.url ? `<a href="${m.url}" target="_blank" rel="noopener">${esc(m.name)}</a>` : esc(m.name)}
                </div>
                <div class="snapshot-item-stat">❤️ ${(m.likes || 0).toLocaleString()}</div>
              </div>`).join('')}
        </div>
        <div class="snapshot-panel">
          <div class="snapshot-panel-title">GitHub Trending AI</div>
          ${gh.length === 0
            ? '<div style="font-size:13px;color:var(--text-tertiary);padding:0.5rem 0">暂无数据</div>'
            : gh.slice(0, 6).map(r => `
              <div class="snapshot-item">
                <div class="snapshot-item-name">
                  ${r.url ? `<a href="${r.url}" target="_blank" rel="noopener" title="${esc(r.desc || '')}">${esc(r.name)}</a>` : esc(r.name)}
                </div>
                <div class="snapshot-item-stat">⭐ ${(r.stars || 0).toLocaleString()} · ${r.language || '—'}</div>
              </div>`).join('')}
        </div>
      </div>
    </section>`;
}

// ── 侧边栏滚动高亮 ────────────────────────────────────────────
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

// ── 错误状态 ──────────────────────────────────────────────────
function renderError(dateStr) {
  const content = document.getElementById('report-content');
  const loading = document.getElementById('loading');
  if (loading) loading.remove();
  document.getElementById('header-title').textContent = `${dateStr} 日报`;
  document.getElementById('header-summary').textContent = '当日日报尚未生成';
  content.innerHTML = `
    <div style="padding:4rem 0;text-align:center;color:var(--text-tertiary);">
      <div style="font-size:3rem;margin-bottom:1rem;">📭</div>
      <div style="font-size:16px;margin-bottom:0.5rem;">${dateStr} 的日报暂未生成</div>
      <div style="font-size:14px;margin-bottom:2rem;">日报由 GitHub Actions 每天 09:00 自动生成</div>
      <a href="daily.html" class="btn-ghost" style="display:inline-flex;">← 返回日报列表</a>
    </div>`;
}

// ── 主流程 ────────────────────────────────────────────────────
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
