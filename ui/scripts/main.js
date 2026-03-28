/* AI Observation — main.js */

// ── 近期日报动态渲染 ───────────────────────────────────────────
(function loadLatestReports() {
  const container = document.getElementById('latest-reports');
  if (!container) return;

  fetch('data/daily-index.json')
    .then(r => r.json())
    .then(data => {
      const reports = (data.reports || []).slice(0, 3);
      if (!reports.length) return;

      container.innerHTML = reports.map(r => `
        <div class="report-card">
          <div class="report-date">${r.date}</div>
          <h3 class="report-title">${escHtml(r.title)}</h3>
          <p class="report-excerpt">${escHtml(r.excerpt)}</p>
          <a href="report.html?date=${r.date}" class="report-link">阅读全文 →</a>
        </div>
      `).join('');
    })
    .catch(() => {
      // 静默降级：保留 HTML 中的静态内容
    });

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}());

// ── Nav scroll effect ──────────────────────────────────────────
const nav = document.getElementById('nav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('nav--scrolled', window.scrollY > 20);
  }, { passive: true });
}

// ── Scroll reveal ──────────────────────────────────────────────
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

// ── Filter chips ───────────────────────────────────────────────
document.querySelectorAll('.filter-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    chip.closest('.daily-filters')
        .querySelectorAll('.filter-chip')
        .forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
  });
});

// ── Stats counter animation ────────────────────────────────────
function animateCounter(el, target, duration = 1200) {
  const start = performance.now();
  const update = (time) => {
    const progress = Math.min((time - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(ease * target);
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

// ── Stats bar：追踪天数 + 从 tracking.json 读取人物/公司真实数量 ──
const statDays      = document.getElementById('stat-days');
const statPeople    = document.getElementById('stat-people');
const statCompanies = document.getElementById('stat-companies');

if (statDays || statPeople || statCompanies) {
  const startDate = new Date('2026-03-24');
  const today = new Date();
  const days = Math.max(1, Math.floor((today - startDate) / (1000 * 60 * 60 * 24)));

  // 当 stats-bar 进入视口时触发动画
  const statsObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      if (statDays) animateCounter(statDays, days);
      statsObserver.disconnect();
    }
  }, { threshold: 0.5 });

  const statsBar = document.querySelector('.stats-bar');
  if (statsBar) statsObserver.observe(statsBar);

  // 从 tracking.json 读取追踪人物 / 追踪公司真实数量，同步更新 feature-card 文案
  fetch('data/tracking.json')
    .then(r => r.json())
    .then(data => {
      const m = data.meta || {};
      if (statPeople)    animateCounter(statPeople,    m.people_total  || 0);
      if (statCompanies) animateCounter(statCompanies, m.company_count || 0);

      // feature-card 追踪体系描述
      const featureDesc = document.getElementById('feature-tracking-desc');
      if (featureDesc && (m.people_total || m.company_count)) {
        featureDesc.textContent =
          `L1 实践者 / L2 观察者 / L3 决策者，三级优先级，覆盖 ${m.people_total || 0} 位人物和 ${m.company_count || 0} 家公司`;
      }

      // pipeline 节点追踪体系描述
      const pipelineDesc = document.getElementById('pipeline-tracking-desc');
      if (pipelineDesc && m.people_total) {
        pipelineDesc.textContent = `${m.people_total}+ 信号源`;
      }
    })
    .catch(() => {
      // 静默降级：保留 HTML 中的初始值
    });
}
