/* ── Estado ──────────────────────────────────────────────────────────────── */
let _pollTimer   = null;
let _runStart    = null;
let _elapsedInt  = null;
let _lastRunId   = null;
let _selDays     = [0, 1, 2, 3, 4];

/* ── Init ────────────────────────────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', () => {
  loadConfig();
  startPoll();
});

/* ── Tabs ────────────────────────────────────────────────────────────────── */
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === name)
  );
  document.querySelectorAll('.tab-pane').forEach(p =>
    p.classList.toggle('active', p.id === 'tab-' + name)
  );
  if (name === 'config')    loadConfig();
  if (name === 'dashboard') loadDashboard();
  if (name === 'reports')   loadReports();
}

/* ── Status polling ──────────────────────────────────────────────────────── */
function startPoll() {
  if (_pollTimer) return;
  _pollTimer = setInterval(pollStatus, 2000);
}

async function pollStatus() {
  try {
    const s = await api('/api/status');
    updateStatusChip(s);

    if (s.is_running) {
      showProgress(true);
      if (!_runStart) _runStart = new Date();
      updateElapsed();
    } else {
      showProgress(false);
      _runStart = null;
      clearInterval(_elapsedInt);
      _elapsedInt = null;
      setBtnRun(false);

      if (s.last_error) {
        document.getElementById('run-error').textContent = '✗ ' + s.last_error;
        document.getElementById('run-error').classList.remove('hidden');
      } else {
        document.getElementById('run-error').classList.add('hidden');
      }

      if (s.last_run_id && s.last_run_id !== _lastRunId) {
        _lastRunId = s.last_run_id;
        const active = document.querySelector('.tab-btn.active')?.dataset.tab;
        if (active === 'reports')   loadReports();
        if (active === 'dashboard') loadDashboard();
        document.getElementById('run-last').textContent =
          'Última: ' + new Date().toLocaleTimeString('pt-BR');
      }
    }
  } catch (_) { /* servidor pode estar iniciando */ }
}

function updateStatusChip(s) {
  const el = document.getElementById('audit-status');
  if (s.is_running) {
    el.className = 'chip chip-running';
    el.textContent = '⏳ Em andamento';
  } else {
    el.className = 'chip chip-idle';
    el.textContent = 'Aguardando';
  }
}

function showProgress(show) {
  document.getElementById('run-progress').classList.toggle('hidden', !show);
}

function updateElapsed() {
  if (_elapsedInt) return;
  _elapsedInt = setInterval(() => {
    if (!_runStart) return;
    const s = Math.round((Date.now() - _runStart) / 1000);
    const txt = s < 60 ? s + 's' : Math.floor(s/60) + 'm ' + (s%60) + 's';
    document.getElementById('run-elapsed').textContent = txt;
  }, 1000);
}

/* ── Rodar agora ─────────────────────────────────────────────────────────── */
async function runNow() {
  setBtnRun(true);
  document.getElementById('run-error').classList.add('hidden');
  try {
    await api('/api/run', 'POST');
    _runStart = new Date();
    showProgress(true);
  } catch (e) {
    setBtnRun(false);
    alert('Erro: ' + (e.detail || e.message || 'Verifique os logs'));
  }
}

function setBtnRun(running) {
  const btn = document.getElementById('btn-run');
  btn.disabled = running;
  btn.textContent = running ? '⏳ Em andamento…' : '▶ Rodar Auditoria Agora';
}

/* ── Config ──────────────────────────────────────────────────────────────── */
async function loadConfig() {
  try {
    const cfg = await api('/api/config');
    renderPages(cfg.pages);
    renderFlows(cfg.flows);
    document.getElementById('url-filter').value = cfg.url_filter || '';
    await loadSchedule();
    await loadGA4();
  } catch (e) { console.error('loadConfig:', e); }
}

/* páginas */
function renderPages(pages) {
  const el = document.getElementById('pages-list');
  if (!pages.length) { el.innerHTML = '<div class="empty">Nenhuma página configurada</div>'; return; }
  el.innerHTML = '<div class="item-list">' + pages.map(p => `
    <div class="item-row">
      <div class="item-info">
        <div class="item-name">${esc(p.name)}</div>
        <div class="item-sub">
          <span>${esc(p.url)}</span>
          ${p.viewports.map(v => `<span class="vp-badge">${v}</span>`).join('')}
          ${p.lighthouse_skip ? '<span class="mo-badge">sem Lighthouse</span>' : ''}
        </div>
      </div>
      <label class="sw">
        <input type="checkbox" ${p.active ? 'checked' : ''}
               onchange="togglePage(${JSON.stringify(p.name)}, this.checked)">
        <span class="sw-slider"></span>
      </label>
    </div>
  `).join('') + '</div>';
}

async function togglePage(name, active) {
  await api(`/api/config/pages/${encodeURIComponent(name)}/active`, 'POST', { active });
}

/* fluxos */
function renderFlows(flows) {
  const el = document.getElementById('flows-list');
  if (!flows.length) { el.innerHTML = '<div class="empty">Nenhum fluxo configurado</div>'; return; }
  el.innerHTML = '<div class="item-list">' + flows.map(f => `
    <div class="item-row">
      <div class="item-info">
        <div class="item-name">${esc(f.name)}</div>
        <div class="item-sub">
          <span>${esc(f.id)}</span>
          ${f.viewports.map(v => `<span class="vp-badge">${v}</span>`).join('')}
          ${f.run_mode === 'manual_only' ? '<span class="mo-badge">manual only</span>' : ''}
        </div>
      </div>
      <label class="sw">
        <input type="checkbox" ${f.active ? 'checked' : ''}
               onchange="toggleFlow(${JSON.stringify(f.id)}, this.checked)">
        <span class="sw-slider"></span>
      </label>
    </div>
  `).join('') + '</div>';
}

async function toggleFlow(id, active) {
  await api(`/api/config/flows/${encodeURIComponent(id)}/active`, 'POST', { active });
}

/* filtro de URL */
async function saveUrlFilter() {
  const val = document.getElementById('url-filter').value;
  await api('/api/config/url-filter', 'POST', { url_filter: val });
  flash('filter-msg');
}

/* ── Agendamento ─────────────────────────────────────────────────────────── */
async function loadSchedule() {
  const s = await api('/api/schedule');
  document.getElementById('sched-enabled').checked = s.enabled;
  document.getElementById('sched-time').value = s.time || '09:00';
  _selDays = s.days || [0, 1, 2, 3, 4];
  onSchedToggle();
  renderDays();
}

function onSchedToggle() {
  const on = document.getElementById('sched-enabled').checked;
  document.getElementById('sched-opts').classList.toggle('hidden', !on);
}

function renderDays() {
  const names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];
  document.getElementById('days-row').innerHTML = names.map((n, i) =>
    `<button class="day-btn ${_selDays.includes(i) ? 'sel' : ''}"
             onclick="toggleDay(${i})">${n}</button>`
  ).join('');
}

function toggleDay(d) {
  const idx = _selDays.indexOf(d);
  idx >= 0 ? _selDays.splice(idx, 1) : _selDays.push(d);
  renderDays();
}

async function saveSchedule() {
  const enabled = document.getElementById('sched-enabled').checked;
  const time    = document.getElementById('sched-time').value;
  await api('/api/schedule', 'POST', { enabled, time, days: _selDays });
  flash('sched-msg');
}

/* ── Dashboard ───────────────────────────────────────────────────────────── */
async function loadDashboard() {
  try {
    const d = await api('/api/dashboard');

    /* stats */
    const rateClass = d.avg_pass_rate >= 90 ? 'ok' : d.avg_pass_rate >= 70 ? 'warn' : 'fail';
    document.getElementById('stats-grid').innerHTML = `
      <div class="stat-card"><div class="stat-label">Total de execuções</div><div class="stat-val neu">${d.total_runs}</div></div>
      <div class="stat-card"><div class="stat-label">Taxa de sucesso (média)</div><div class="stat-val ${rateClass}">${d.avg_pass_rate}%</div></div>
      <div class="stat-card"><div class="stat-label">Última auditoria</div><div class="stat-val neu" style="font-size:16px">${d.last_run_date}</div></div>
      <div class="stat-card"><div class="stat-label">Falhas (últ. 5 runs)</div><div class="stat-val ${d.recent_failures > 0 ? 'fail' : 'ok'}">${d.recent_failures}</div></div>
    `;

    /* tendência */
    const chart = document.getElementById('trend-chart');
    if (!d.trend.length) {
      chart.innerHTML = '<div class="empty">Sem histórico suficiente</div>';
    } else {
      chart.innerHTML = d.trend.map(t => {
        const color = t.pass_rate >= 90 ? 'var(--ok)' : t.pass_rate >= 70 ? 'var(--warn)' : 'var(--fail)';
        const h = Math.max(4, t.pass_rate);
        return `<div class="trend-col">
          <div class="trend-bar" style="height:${h}%;background:${color}"
               data-tip="${t.pass_rate}% — ${t.date}${t.total_falhou ? ' ('+t.total_falhou+' falha(s))' : ''}"></div>
          <div class="trend-lbl">${t.date.slice(5)}</div>
        </div>`;
      }).join('');
    }

    /* top falhas */
    const tf = document.getElementById('top-failures');
    if (!d.top_failures.length) {
      tf.innerHTML = '<div class="empty">Nenhuma falha registrada</div>';
    } else {
      tf.innerHTML = `<table class="tbl">
        <thead><tr><th>#</th><th>Checagem</th><th>Ocorrências</th></tr></thead>
        <tbody>${d.top_failures.map((f, i) => `
          <tr>
            <td>${i + 1}</td>
            <td>${esc(f.check_name)}</td>
            <td><strong style="color:var(--fail)">${f.count}</strong></td>
          </tr>`).join('')}
        </tbody>
      </table>`;
    }
  } catch (e) { console.error('loadDashboard:', e); }
}

/* ── Relatórios ──────────────────────────────────────────────────────────── */
async function loadReports() {
  const el = document.getElementById('runs-wrap');
  try {
    const runs = await api('/api/runs');
    if (!runs.length) { el.innerHTML = '<div class="empty">Nenhuma execução encontrada</div>'; return; }

    el.innerHTML = `<table class="tbl">
      <thead>
        <tr>
          <th>Data</th><th>Duração</th><th>Status</th><th>Resultado</th>
          <th style="text-align:right">OK</th>
          <th style="text-align:right">Falhas</th>
          <th style="text-align:right">Erros</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${runs.map(r => {
        const date  = fmtDate(r.started_at);
        const dur   = calcDur(r.started_at, r.finished_at);
        const stBadge  = statusBadge(r.status);
        const resBadge = resultBadge(r.resultado);
        const btn = r.status === 'concluida'
          ? `<button class="btn btn-secondary btn-sm" onclick="viewReport('${r.run_id}','${date}')">Ver relatório</button>`
          : '';
        return `<tr>
          <td>${date}</td>
          <td>${dur}</td>
          <td>${stBadge}</td>
          <td>${resBadge}</td>
          <td style="text-align:right">${r.total_passou ?? '—'}</td>
          <td style="text-align:right;color:var(--fail)">${r.total_falhou ?? '—'}</td>
          <td style="text-align:right;color:var(--warn)">${r.total_erro ?? '—'}</td>
          <td>${btn}</td>
        </tr>`;
      }).join('')}
      </tbody>
    </table>`;
  } catch (e) { el.innerHTML = '<div class="empty">Erro ao carregar relatórios</div>'; }
}

function viewReport(runId, date) {
  document.getElementById('modal-title').textContent = 'Relatório — ' + date;
  document.getElementById('modal-iframe').src = `/api/runs/${runId}/report`;
  document.getElementById('modal').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  document.getElementById('modal-iframe').src = 'about:blank';
}

/* ── GA4 ─────────────────────────────────────────────────────────────────── */
async function loadGA4() {
  const el = document.getElementById('ga4-section');
  try {
    const cfg = await api('/api/ga4/config');
    if (!cfg.configured) {
      el.innerHTML = `
        <div class="ga4-form">
          <p class="muted" style="margin-bottom:8px">Configure o GA4 para descobrir as páginas mais visitadas.</p>
          <div class="ga4-input-row">
            <label>Property ID</label>
            <input class="ga4-input" type="text" id="ga4-prop" placeholder="123456789" value="${esc(cfg.property_id)}">
          </div>
          <div class="ga4-input-row">
            <label>Credencial JSON</label>
            <input class="ga4-input" type="text" id="ga4-cred" placeholder="C:/caminho/credencial.json" value="${esc(cfg.credentials_path)}">
          </div>
          <div class="form-row" style="margin-top:4px">
            <button class="btn btn-primary" onclick="saveGA4()">Salvar e conectar</button>
            <span id="ga4-msg"></span>
          </div>
          <details style="margin-top:14px">
            <summary>Como obter as credenciais GA4?</summary>
            <ol>
              <li>Acesse <strong>console.cloud.google.com</strong></li>
              <li>Crie um projeto e ative a <strong>Google Analytics Data API</strong></li>
              <li>Em IAM → Contas de serviço: crie uma conta e baixe a chave JSON</li>
              <li>No GA4: Admin → Gerenciamento de acesso → adicione o e-mail da conta como Viewer</li>
              <li>Property ID: Admin → Detalhes da propriedade</li>
            </ol>
          </details>
        </div>`;
    } else {
      el.innerHTML = `
        <div class="ga4-connected">
          <span class="badge b-ok">✓ Conectado</span>
          <span class="muted">Property ${esc(cfg.property_id)}</span>
          <button class="btn btn-secondary btn-sm" onclick="loadGA4Pages()">Atualizar lista</button>
          <button class="btn btn-secondary btn-sm" onclick="resetGA4()">Reconfigurar</button>
        </div>
        <div id="ga4-pages"><div class="loading">Carregando…</div></div>`;
      loadGA4Pages();
    }
  } catch (e) { el.innerHTML = '<div class="empty">Erro ao carregar configuração GA4</div>'; }
}

async function saveGA4() {
  const property_id      = document.getElementById('ga4-prop').value.trim();
  const credentials_path = document.getElementById('ga4-cred').value.trim();
  const msg = document.getElementById('ga4-msg');
  if (!property_id || !credentials_path) {
    msg.className = 'err-msg'; msg.textContent = '✗ Preencha todos os campos'; return;
  }
  await api('/api/ga4/config', 'POST', { property_id, credentials_path });
  loadGA4();
}

async function resetGA4() {
  await api('/api/ga4/config', 'POST', { property_id: '', credentials_path: '' });
  loadGA4();
}

async function loadGA4Pages() {
  const el = document.getElementById('ga4-pages');
  if (!el) return;
  el.innerHTML = '<div class="loading">Consultando GA4…</div>';
  try {
    const { pages } = await api('/api/ga4/pages');
    if (!pages.length) { el.innerHTML = '<div class="empty">Nenhuma página encontrada</div>'; return; }
    el.innerHTML = `
      <p class="muted" style="margin-bottom:10px">Top páginas por sessões — últimos 30 dias:</p>
      <table class="tbl">
        <thead><tr><th>#</th><th>Página</th><th>Sessões</th><th>Na auditoria?</th></tr></thead>
        <tbody>${pages.map((p, i) => `
          <tr>
            <td>${i+1}</td>
            <td><code>${esc(p.path)}</code></td>
            <td>${p.sessions.toLocaleString('pt-BR')}</td>
            <td>${p.in_audit ? '<span class="badge b-ok">✓ Sim</span>' : '<span class="badge b-gray">Não</span>'}</td>
          </tr>`).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    el.innerHTML = `<div style="color:var(--fail);font-size:13px">Erro: ${esc(e.detail || e.message)}</div>`;
  }
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */
async function api(url, method = 'GET', body = null) {
  const opts = { method, headers: {} };
  if (body) { opts.body = JSON.stringify(body); opts.headers['Content-Type'] = 'application/json'; }
  const r = await fetch(url, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw data;
  return data;
}

function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtDate(iso) {
  if (!iso) return '—';
  return iso.slice(0,16).replace('T', ' ');
}

function calcDur(start, end) {
  if (!start || !end) return '—';
  const s = Math.round((new Date(end) - new Date(start)) / 1000);
  return s < 60 ? s + 's' : Math.floor(s/60) + 'm ' + (s%60) + 's';
}

function statusBadge(s) {
  const map = { concluida: 'b-ok', falhou: 'b-fail', em_andamento: 'b-warn', cancelada: 'b-gray' };
  return `<span class="badge ${map[s] || 'b-gray'}">${s || '—'}</span>`;
}

function resultBadge(r) {
  if (!r) return '<span class="badge b-gray">—</span>';
  return r === 'tudo_ok'
    ? '<span class="badge b-ok">tudo OK</span>'
    : '<span class="badge b-fail">com falhas</span>';
}

function flash(id) {
  const el = document.getElementById(id);
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 2500);
}
