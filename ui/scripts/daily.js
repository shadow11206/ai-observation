/**
 * daily.js — 日报列表页
 * 从 01-daily-reports/ 目录加载最近 30 天的 .json 日报，渲染为卡片列表
 * 并在顶部渲染日期导航器（按月分组，有日报的日期高亮可点击）
 */

const REPORTS_BASE = '../01-daily-reports';
const LIST_CONTAINER = document.getElementById('report-list');
const EMPTY_STATE = document.getElementById('empty-state');
const DATE_NAV = document.getElementById('date-nav');

// 生成最近 N 天的日期列表
function getRecentDates(n = 60) {
  const dates = [];
  const now = new Date();
  for (let i = 0; i < n; i++) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    dates.push({ date: `${yyyy}-${mm}-${dd}`, month: `${yyyy}-${mm}` });
  }
  return dates;
}

// 尝试加载某一天的日报 JSON
async function fetchReport(dateInfo) {
  const url = `${REPORTS_BASE}/${dateInfo.month}/${dateInfo.date}.json`;
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function isToday(dateStr) {
  const now = new Date();
  const d = new Date(dateStr + 'T00:00:00');
  return now.toDateString() === d.toDateString();
}

// 渲染日期导航器
function renderDateNav(dates, availableDates) {
  if (!DATE_NAV) return;

  const availableSet = new Set(availableDates);

  // 按月分组
  const monthMap = new Map();
  dates.forEach(({ date, month }) => {
    if (!monthMap.has(month)) monthMap.set(month, []);
    monthMap.get(month).push(date);
  });

  const MONTH_CN = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月'];

  let html = '<div class="date-nav">';

  monthMap.forEach((days, month) => {
    const [yyyy, mm] = month.split('-');
    const monthLabel = `${yyyy} 年 ${MONTH_CN[parseInt(mm, 10) - 1]}`;

    html += `<div class="date-nav-month">${monthLabel}</div><div class="date-nav-grid">`;

    days.forEach(date => {
      const dd = date.split('-')[2];
      const hasReport = availableSet.has(date);
      const today = isToday(date);

      if (hasReport) {
        const cls = today ? 'date-nav-item has-report is-today' : 'date-nav-item has-report';
        html += `<a href="report.html?date=${date}" class="${cls}" title="查看 ${date} 日报">${parseInt(dd, 10)}</a>`;
      } else {
        html += `<span class="date-nav-item">${parseInt(dd, 10)}</span>`;
      }
    });

    html += '</div>';
  });

  html += '</div>';
  DATE_NAV.innerHTML = html;
}

// 渲染单张日报卡片（摘要模式）
function renderCard(data) {
  const { date, top_items = [], summary_one_line = '' } = data;
  const d = new Date(date + 'T00:00:00');
  const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
  const dateLabel = `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日 · 星期${weekdays[d.getDay()]}`;

  // 收集 key_data（优先）或 tags（fallback）
  const allKeyData = [...new Set(top_items.flatMap(i => i.key_data || i.tags || []))];

  const card = document.createElement('div');
  card.className = 'daily-report reveal';

  card.innerHTML = `
    <div class="daily-report-header">
      <span class="daily-report-date">${dateLabel}</span>
      ${isToday(date) ? '<span class="daily-badge">最新</span>' : ''}
    </div>
    <div class="daily-report-body">
      ${summary_one_line ? `<p style="font-size:15px;color:var(--text-secondary);margin-bottom:1.25rem;font-style:italic;">${summary_one_line}</p>` : ''}
      <div class="daily-highlights">
        <div class="daily-highlight-title">今日最重要</div>
        ${top_items.slice(0, 2).map(item => `
          <div class="daily-highlight-item">
            <span class="highlight-num">${String(item.rank || 1).padStart(2, '0')}</span>
            <span class="highlight-text">
              <strong>${item.title || ''}</strong>
              ${item.judgment ? ` — ${item.judgment}` : ''}
            </span>
          </div>
        `).join('') || '<div style="padding:0.75rem 0;color:var(--text-tertiary);font-size:14px;">暂无内容</div>'}
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:1.25rem;flex-wrap:wrap;gap:0.75rem;">
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
          ${allKeyData.slice(0, 4).map(chip => `<span class="key-chip">${chip}</span>`).join('')}
        </div>
        <a href="report.html?date=${date}" class="report-link" style="font-size:14px;white-space:nowrap;">阅读全文 →</a>
      </div>
    </div>
  `;

  return card;
}

// 主流程
async function init() {
  const dates = getRecentDates(60);

  // 并发加载
  const results = await Promise.all(dates.map(fetchReport));
  const reports = results.filter(Boolean);
  const availableDates = reports.map(r => r.date);

  // 渲染日期导航器
  renderDateNav(dates, availableDates);

  if (reports.length === 0) {
    EMPTY_STATE.style.display = 'block';
    return;
  }

  reports.forEach(r => {
    const card = renderCard(r);
    LIST_CONTAINER.appendChild(card);
  });

  // 初始化 reveal 动画
  requestAnimationFrame(() => {
    document.querySelectorAll('.reveal').forEach(el => {
      if (typeof revealObserver !== 'undefined') revealObserver.observe(el);
    });
  });
}

init();
