(() => {
  'use strict';

  const App = window.App || {};
  const Dom = App.dom || {};
  const $ = Dom.$ || ((sel, root = document) => root.querySelector(sel));
  const runNowOrOnReady =
    Dom.runNowOrOnReady ||
    (fn => (document.readyState !== 'loading'
      ? fn()
      : document.addEventListener('DOMContentLoaded', fn, { once: true })));

  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = String(val);
  }

  const normalizeStatus =
    App.format?.normalizeStatus ||
    (v => {
      if (typeof v === 'boolean') return v ? 'Ativo' : 'Inativo';
      const t = String(v || '').trim().toLowerCase();
      if (t === 'ativo' || t === 'ativa' || t === 'true' || t === '1') return 'Ativo';
      if (t === 'inativo' || t === 'inativa' || t === 'false' || t === '0') return 'Inativo';
      return t ? t[0].toUpperCase() + t.slice(1) : '—';
    });

  async function getMetricsFromPrefetch() {
    const metrics =
      (await App.prefetch?.getWithRevalidate?.('dashboard_metrics')) ||
      (await App.prefetch?.get?.('dashboard_metrics'));
    return metrics || null;
  }

  async function getMetricsFromPhp() {
    try {
      const res = await fetch('processa_dashboard.php?action=metrics', {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json().catch(() => null);
      const data = json?.data || json;
      if (!data) return null;
      const { total_turmas, total_alunos, turmas_ativas, turmas_incompletas } = data;
      if ([total_turmas, total_alunos, turmas_ativas].some(v => v == null)) return null;
      return {
        total_turmas,
        total_alunos,
        turmas_ativas,
        turmas_incompletas: Number.isFinite(turmas_incompletas) ? turmas_incompletas : 0
      };
    } catch {
      return null;
    }
  }

  async function getTurmasFromPrefetch() {
    if (App.prefetch?.forView) {
      await App.prefetch.forView('dashboard');
    }
    const turmas =
      (await App.prefetch?.getWithRevalidate?.('turmas')) ||
      (await App.cache?.get?.('turmas')) ||
      null;
    return Array.isArray(turmas) ? turmas : null;
  }

  async function scanDetailsAndAggregate(turmas, {
    baseUrl = 'http://localhost:8000/api/turmas',
    maxConcurrency = 6,
    maxItems = 300,
    timeoutMs = 15000
  } = {}) {
    const items = turmas.slice(0, maxItems);

    const controller = new AbortController();
    const kill = setTimeout(() => controller.abort(), timeoutMs);
    let idx = 0, active = 0;

    let totalAlunos = 0;
    let ucsSemInstrutor = 0;

    return await new Promise((resolve) => {
      const next = () => {
        if (idx >= items.length && active === 0) {
          clearTimeout(kill);
          resolve({ totalAlunos, ucsSemInstrutor });
          return;
        }
        while (active < maxConcurrency && idx < items.length) {
          const t = items[idx++];
          const id = t?.id || t?._id || t?.id_turma;
          if (!id) continue;
          active++;
          fetch(`${baseUrl}/${encodeURIComponent(id)}`, {
            signal: controller.signal,
            credentials: 'include',
            headers: { 'Accept': 'application/json' }
          })
            .then(r => r.ok ? r.json() : null)
            .then(doc => {
              const n = Number(doc?.num_alunos);
              if (!Number.isNaN(n) && n > 0) totalAlunos += n;

              const ucs = Array.isArray(doc?.unidades_curriculares) ? doc.unidades_curriculares : [];
              for (const uc of ucs) {
                const v = uc?.id_instrutor;
                if (v === undefined || v === null || v === '') {
                  ucsSemInstrutor += 1;
                }
              }
            })
            .catch(() => { /* ignorar erros individuais */ })
            .finally(() => { active--; next(); });
        }
      };
      next();
    });
  }

  async function computeMetricsFromTurmas() {
    const turmas = await getTurmasFromPrefetch();
    if (!turmas) return null;

    const total_turmas = turmas.length;

    let turmas_ativas = 0;
    for (const t of turmas) {
      if (normalizeStatus(t?.status) === 'Ativo') turmas_ativas++;
    }

    const { totalAlunos, ucsSemInstrutor } =
      await scanDetailsAndAggregate(turmas).catch(() => ({ totalAlunos: 0, ucsSemInstrutor: 0 }));

    return {
      total_turmas,
      total_alunos: totalAlunos,
      turmas_ativas,
      turmas_incompletas: ucsSemInstrutor
    };
  }

  async function loadMetrics() {
    try {
      let metrics = await getMetricsFromPrefetch();
      if (!metrics) metrics = await getMetricsFromPhp();
      if (!metrics) metrics = await computeMetricsFromTurmas();

      const {
        total_turmas = 0,
        total_alunos = 0,
        turmas_ativas = 0,
        turmas_incompletas = 0,
      } = metrics || {};

      setText('totalTurmas', total_turmas);
      setText('totalAlunos', total_alunos);
      setText('turmasAtivas', turmas_ativas);
      setText('turmasIncompletas', turmas_incompletas);
    } catch (err) {
      console.error('Erro ao carregar métricas do dashboard:', err);
      setText('totalTurmas', '—');
      setText('totalAlunos', '—');
      setText('turmasAtivas', '—');
      setText('turmasIncompletas', '—');
    }
  }

  function setupMenuToggle() {
    const menuToggle = $('#menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const container = document.querySelector('.dashboard-container');

    if (!menuToggle || !sidebar || !container) return;

    menuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('active');
      container.classList.toggle('sidebar-active');
    });

    container.addEventListener('click', (ev) => {
      if (
        container.classList.contains('sidebar-active') &&
        !sidebar.contains(ev.target) &&
        !menuToggle.contains(ev.target)
      ) {
        sidebar.classList.remove('active');
        container.classList.remove('sidebar-active');
      }
    });
  }

  let __chartTurnosInstance = null;
  let __chartAreasInstance = null;

  async function chartTurnos() {
    try {
      const res = await fetch('http://localhost:8000/api/dashboard/alunos_por_turno', {
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const container = document.getElementById('distribuicaoTurno');
      if (!container) return;
      let canvas = document.getElementById('chartjs-bar');
      if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.id = 'chartjs-bar';
        canvas.height = 120;
        container.innerHTML = '';
        container.appendChild(canvas);
      }

      if (__chartTurnosInstance?.destroy) {
        __chartTurnosInstance.destroy();
        __chartTurnosInstance = null;
      }

      __chartTurnosInstance = new Chart(canvas, {
        type: "bar",
        data: {
          labels: ["Manhã", "Tarde", "Noite"],
          datasets: [{
            label: "Alunos",
            backgroundColor: window.theme?.primary || "#2c93a5ff",
            borderColor: window.theme?.primary || "#2c93a5ff",
            hoverBackgroundColor: window.theme?.primary || "#1d616dff",
            hoverBorderColor: window.theme?.primary || "#1d616dff",
            data: [data["Manhã"] || 0, data["Tarde"] || 0, data["Noite"] || 0],
            barPercentage: .75,
            categoryPercentage: .5
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
        }
      });
    } catch (err) {
      console.error("Erro ao carregar gráfico de turnos:", err);
    }
  }

  function extractLabelsValues(anyPayload) {
    if (Array.isArray(anyPayload)) {
      const labels = anyPayload.map(r => (r && (r._id ?? r.id ?? '(Sem área)')));
      const values = anyPayload.map(r => Number(r?.qtd_turmas ?? r?.qtd ?? r?.count ?? 0));
      if (labels.length && values.length) return { labels, values };
    }
    const obj = anyPayload?.data || anyPayload || {};
    if (Array.isArray(obj.labels) && Array.isArray(obj.data)) {
      return { labels: obj.labels, values: obj.data };
    }
    if (Array.isArray(obj.items)) {
      const labels = obj.items.map(r => (r && (r._id ?? r.id ?? '(Sem área)')));
      const values = obj.items.map(r => Number(r?.qtd_turmas ?? r?.qtd ?? r?.count ?? 0));
      if (labels.length && values.length) return { labels, values };
    }
    return { labels: [], values: [] };
  }

  async function tryFetchPie(url, fetchOpts) {
    const res = await fetch(url, fetchOpts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json().catch(() => null);
    const { labels, values } = extractLabelsValues(payload);
    if (labels.length && values.length) return { labels, values };
    throw new Error('payload vazio');
  }

  async function chartAreas() {
    try {
      const attempts = [
        { url: 'processa_dashboard.php?action=areas_tecnologicas', opts: { credentials: 'same-origin', headers: { 'Accept': 'application/json' } } },
        { url: 'http://localhost:8000/api/dashboard/areas_tecnologicas_pie', opts: { credentials: 'include', headers: { 'Accept': 'application/json' } } },
        { url: 'processa_dashboard.php?action=areas_tecnologicas_pie', opts: { credentials: 'same-origin', headers: { 'Accept': 'application/json' } } },
        { url: 'http://localhost:8000/api/dashboard/areas_tecnologicas', opts: { credentials: 'include', headers: { 'Accept': 'application/json' } } },
      ];
      let labels = [], values = [];
      for (const a of attempts) {
        try {
          const r = await tryFetchPie(a.url, a.opts);
          labels = r.labels; values = r.values;
          console.debug('[pie] usando', a.url, { labels, values });
          break;
        } catch (e){
          console.debug('[pie] falhou', a.url, e); 
         }
      }
      if (!labels.length || !values.length) {
        labels = ['Sem dados'];
        values = [1];
      }

      const container = document.getElementById('distribuicaoArea');
      if (!container) return;

      let canvas = document.getElementById('chartjs-pie');
      if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.id = 'chartjs-pie';
        canvas.style.minHeight = '240px';
        container.innerHTML = '';
        container.appendChild(canvas);
      }

      if (__chartAreasInstance?.destroy) {
        __chartAreasInstance.destroy();
        __chartAreasInstance = null;
      }

      const basePalette = [
        window.theme?.primary || '#4F46E5',
        window.theme?.success || '#22C55E',
        window.theme?.warning || '#F59E0B',
        window.theme?.info || '#0EA5E9',
        window.theme?.danger || '#EF4444',
        '#8B5CF6', '#10B981', '#EAB308', '#06B6D4', '#F97316', '#84CC16'
      ];
      const colors = labels.map((_, i) => basePalette[i % basePalette.length]);

      __chartAreasInstance = new Chart(canvas, {
        type: 'pie',
        data: {
          labels,
          datasets: [{
            data: values,
            backgroundColor: colors,
            borderColor: 'transparent'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: true, position: 'bottom' },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const total = values.reduce((a, b) => a + (Number(b) || 0), 0) || 0;
                  const val = Number(ctx.raw) || 0;
                  const pct = total ? ((val / total) * 100).toFixed(1) : '0.0';
                  return `${ctx.label}: ${val} (${pct}%)`;
                }
              }
            }
          }
        }
      });
    } catch (err) {
      console.error('Erro ao carregar gráfico de áreas:', err);
    }
  }

  runNowOrOnReady(async () => {
    setupMenuToggle();
    await loadMetrics();
    await chartTurnos();
    await chartAreas(); 
  });
})();
