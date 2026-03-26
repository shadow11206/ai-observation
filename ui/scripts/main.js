/* AI Observation — main.js */

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

// 追踪天数动态计算
const statDays = document.getElementById('stat-days');
if (statDays) {
  const startDate = new Date('2026-03-24');
  const today = new Date();
  const days = Math.max(1, Math.floor((today - startDate) / (1000 * 60 * 60 * 24)));

  const statsObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      animateCounter(statDays, days);
      statsObserver.disconnect();
    }
  }, { threshold: 0.5 });

  const statsBar = document.querySelector('.stats-bar');
  if (statsBar) statsObserver.observe(statsBar);
}
