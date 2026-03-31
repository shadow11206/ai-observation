/**
 * research.js — 深度调研列表页 + 详情页共用逻辑
 */

// ===================== 列表页 =====================
const RESEARCH_INDEX = 'data/research-index.json';
const RESEARCH_BASE  = '../02-deep-research';

let allItems = [];
let currentFilter = 'all';

async function initResearchList() {
  const grid  = document.getElementById('research-grid');
  const stats = document.getElementById('research-stats');
  if (!grid) return;

  try {
    const res  = await fetch(RESEARCH_INDEX);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    allItems = data.items || [];

    renderStats(data, stats);
    renderGrid(allItems, grid);
    initFilters();
  } catch (e) {
    grid.innerHTML = `
      <div class="research-empty">
        <div class="research-empty-icon">🔬</div>
        <div class="research-empty-text">暂无调研报告</div>
      </div>`;
  }
}

function renderStats(data, el) {
  if (!el) return;
  el.innerHTML = `
    <span>${data.total} 篇调研报告</span>
    <span style="margin:0 0.4rem;color:var(--border)">·</span>
    <span>最近更新：${data.updated_at || ''}</span>
  `;
}

function renderGrid(items, grid) {
  grid.innerHTML = '';
  if (items.length === 0) {
    grid.innerHTML = `
      <div class="research-empty">
        <div class="research-empty-icon">🔍</div>
        <div class="research-empty-text">该分类暂无调研报告</div>
      </div>`;
    return;
  }
  items.forEach(item => {
    grid.appendChild(createCard(item));
  });
  // 滚动进入动画
  if (window.IntersectionObserver) {
    const cards = grid.querySelectorAll('.research-card');
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.style.opacity = '1';
          e.target.style.transform = 'translateY(0)';
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.05 });
    cards.forEach((c, i) => {
      c.style.opacity = '0';
      c.style.transform = 'translateY(12px)';
      c.style.transition = `opacity 0.4s ease ${i * 0.06}s, transform 0.4s ease ${i * 0.06}s`;
      obs.observe(c);
    });
  }
}

function createCard(item) {
  const a = document.createElement('a');
  a.className = 'research-card';
  a.href = `research-detail.html?id=${encodeURIComponent(item.id)}&category=${item.category}`;

  const delta = item.confidence_delta || 0;
  let judgmentBadge = '';
  if (delta > 0) {
    judgmentBadge = `<span class="judgment-badge">判断升级 +${delta}★</span>`;
  } else if (delta < 0) {
    judgmentBadge = `<span class="judgment-badge negative">判断修正 ${delta}★</span>`;
  }

  const tags = (item.tags || []).slice(0, 4).map(t =>
    `<span class="research-tag">${t}</span>`
  ).join('');

  const fromReport = item.from_report
    ? `<a href="report.html?date=${item.from_report}" onclick="event.stopPropagation()"
         style="font-size:12px;color:var(--text-tertiary);transition:color 0.2s"
         onmouseover="this.style.color='var(--accent)'" onmouseout="this.style.color='var(--text-tertiary)'">
         来源日报 ${item.from_report}
       </a>`
    : '';

  a.innerHTML = `
    <div class="research-card-meta">
      <span class="research-type-badge">${item.category_label || item.category}</span>
      <span class="research-date">${formatDate(item.date)}</span>
      ${item.confidence_rating
        ? `<span class="research-confidence">${item.confidence_rating}</span>`
        : ''}
    </div>
    <div class="research-card-title">${item.title}</div>
    <div class="research-card-tldr">${item.tldr || ''}</div>
    <div class="research-card-footer">
      <div class="research-tags">${tags}</div>
      <div style="display:flex;align-items:center;gap:0.75rem;flex-shrink:0">
        ${judgmentBadge}
        ${item.sources_count ? `<span class="research-sources">${item.sources_count} 个来源</span>` : ''}
        ${fromReport}
      </div>
    </div>
  `;
  return a;
}

function initFilters() {
  document.querySelectorAll('.filter-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter || 'all';
      const filtered = currentFilter === 'all'
        ? allItems
        : allItems.filter(i => i.category === currentFilter);
      renderGrid(filtered, document.getElementById('research-grid'));
    });
  });
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00');
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`;
}

// 入口
if (document.getElementById('research-grid')) {
  document.addEventListener('DOMContentLoaded', initResearchList);
}
