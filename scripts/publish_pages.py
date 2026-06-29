#!/usr/bin/env python3
"""
Gera o conteúdo estático para GitHub Pages após cada auditoria.
Lê o histórico do SQLite, copia os relatórios HTML e gera o index.html.
Executado como step no GitHub Actions.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from auditor.storage.history import get_recent_runs as _get_recent_runs
    _HAS_AUDITOR = True
except ImportError:
    _get_recent_runs = None  # type: ignore[assignment]
    _HAS_AUDITOR = False

REPORTS_DIR  = ROOT / "reports"
OUTPUT_DIR   = ROOT / "gh-pages-output"
OUTPUT_REPORTS = OUTPUT_DIR / "reports"

OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_REPORTS.mkdir(exist_ok=True)

GITHUB_REPO          = os.environ.get("GITHUB_REPOSITORY", "")
ACTIONS_WORKFLOW_URL = os.environ.get(
    "ACTIONS_WORKFLOW_URL",
    f"https://github.com/{GITHUB_REPO}/actions/workflows/audit.yml" if GITHUB_REPO else "#",
)
MANAGE_WORKFLOW_URL  = (
    f"https://github.com/{GITHUB_REPO}/actions/workflows/manage-pages.yml"
    if GITHUB_REPO else "#"
)
UPDATE_SCHEDULE_URL = (
    f"https://github.com/{GITHUB_REPO}/actions/workflows/update-schedule.yml"
    if GITHUB_REPO else "#"
)
EDIT_PAGES_URL = (
    f"https://github.com/{GITHUB_REPO}/edit/master/config/pages.yaml"
    if GITHUB_REPO else "#"
)
ACTIVATE_ALL_URL = (
    f"https://github.com/{GITHUB_REPO}/actions/workflows/activate-all-pages.yml"
    if GITHUB_REPO else "#"
)
DEACTIVATE_ALL_URL = (
    f"https://github.com/{GITHUB_REPO}/actions/workflows/deactivate-all-pages.yml"
    if GITHUB_REPO else "#"
)
PAGES_BASE = (
    f"https://{GITHUB_REPO.split('/')[0]}.github.io/{GITHUB_REPO.split('/')[-1]}"
    if GITHUB_REPO else ""
)

GOOGLE_CLIENT_ID  = os.environ.get("GOOGLE_CLIENT_ID", "")
_ALLOWED_DOMAINS  = ["minimalclub.com.br", "moonventures.com.br", "hoomy.com.br"]


# ── Copiar relatórios e screenshots ───────────────────────────────────────────

copied = 0
if REPORTS_DIR.exists():
    for html_file in REPORTS_DIR.glob("*.html"):
        shutil.copy2(html_file, OUTPUT_REPORTS / html_file.name)
        copied += 1

screenshots_src = REPORTS_DIR / "screenshots"
if screenshots_src.exists():
    shutil.copytree(screenshots_src, OUTPUT_REPORTS / "screenshots", dirs_exist_ok=True)


# ── Histórico do SQLite ───────────────────────────────────────────────────────

db_path = ROOT / "auditor-history.db"


def _report_url(started_at: str | None) -> str | None:
    """Gera URL do relatório. Não verifica existência local — keep_files:true preserva no gh-pages."""
    if not started_at:
        return None
    try:
        dt = datetime.fromisoformat(started_at)
        return f"reports/{dt.strftime('%Y-%m-%dT%H-%M-%S')}.html"
    except Exception:
        return None


# Tenta ler do SQLite; se não disponível, usa reports.json existente como fallback
runs_raw = (
    _get_recent_runs(limit=200, db_path=db_path)
    if _HAS_AUDITOR and db_path.exists()
    else []
)

if runs_raw:
    runs: list[dict] = [
        {
            "run_id":       r.get("run_id", ""),
            "started_at":   r.get("started_at", ""),
            "finished_at":  r.get("finished_at", ""),
            "status":       r.get("status", ""),
            "resultado":    r.get("resultado") or "",
            "total_checks": r.get("total_checks") or 0,
            "total_passou": r.get("total_passou") or 0,
            "total_falhou": r.get("total_falhou") or 0,
            "total_erro":   r.get("total_erro") or 0,
            "report_url":   _report_url(r.get("started_at")),
        }
        for r in runs_raw
    ]
else:
    # Fallback: usa reports.json pré-populado do gh-pages (copiado pelo workflow antes de rodar)
    _fallback = OUTPUT_DIR / "reports.json"
    if _fallback.exists():
        try:
            runs = json.loads(_fallback.read_text(encoding="utf-8"))
        except Exception:
            runs = []
    else:
        runs = []

(OUTPUT_DIR / "reports.json").write_text(
    json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8"
)


# ── Analytics ─────────────────────────────────────────────────────────────────

def _build_analytics(db: Path) -> dict:
    """Query SQLite for analytics data. Returns {} if unavailable."""
    import sqlite3 as _sq
    try:
        conn = _sq.connect(str(db))
        conn.row_factory = _sq.Row

        top = conn.execute("""
            SELECT cr.check_id, cr.check_name, COUNT(*) as cnt,
                   MAX(ar.started_at) as last_seen
            FROM check_results cr
            JOIN audit_runs ar ON cr.run_id = ar.run_id
            WHERE cr.status IN ('falhou','erro') AND ar.status = 'concluida'
              AND ar.started_at >= datetime('now','-60 days')
            GROUP BY cr.check_id, cr.check_name
            ORDER BY cnt DESC LIMIT 15
        """).fetchall()
        top_failures = [
            {"check_id": r["check_id"], "check_name": r["check_name"],
             "fail_count": r["cnt"],
             "last_seen": (r["last_seen"] or "")[:10]}
            for r in top
        ]

        daily_rows = conn.execute("""
            SELECT date(started_at) as date, COUNT(*) as run_count,
                   SUM(COALESCE(total_passou,0)) as tp,
                   SUM(COALESCE(total_falhou,0)) as tf,
                   SUM(COALESCE(total_erro,0)) as te,
                   SUM(COALESCE(total_checks,0)) as tc
            FROM audit_runs WHERE status='concluida'
              AND started_at >= datetime('now','-90 days')
            GROUP BY date(started_at) ORDER BY date ASC
        """).fetchall()
        daily = [
            {"date": r["date"], "run_count": r["run_count"],
             "total_checks": r["tc"] or 0, "total_passou": r["tp"] or 0,
             "total_falhou": r["tf"] or 0, "total_erro": r["te"] or 0,
             "pass_rate": round((r["tp"] or 0) / (r["tc"] or 1) * 100)}
            for r in daily_rows
        ]

        hl = conn.execute("""
            SELECT cr.check_name, COUNT(*) as total,
                   SUM(CASE WHEN cr.status='passou' THEN 1 ELSE 0 END) as ok
            FROM check_results cr JOIN audit_runs ar ON cr.run_id = ar.run_id
            WHERE ar.status='concluida' AND ar.started_at >= datetime('now','-30 days')
            GROUP BY cr.check_name HAVING total >= 3
            ORDER BY ok * 1.0 / total DESC
        """).fetchall()
        always_ok = [r["check_name"] for r in hl if r["ok"] == r["total"]][:8]
        attention  = [r["check_name"] for r in hl
                      if (r["ok"] or 0) < r["total"]
                      and (r["ok"] or 0) / (r["total"] or 1) < 0.8][:8]

        conn.close()
        return {"top_failures": top_failures, "daily": daily,
                "highlights": {"always_ok": always_ok, "attention": attention}}
    except Exception as exc:
        print(f"Aviso: analytics não gerado — {exc}")
        return {}


analytics: dict = {}
if _HAS_AUDITOR and db_path.exists():
    analytics = _build_analytics(db_path)
else:
    _fa = OUTPUT_DIR / "analytics.json"
    if _fa.exists():
        try:
            analytics = json.loads(_fa.read_text(encoding="utf-8"))
        except Exception:
            pass

(OUTPUT_DIR / "analytics.json").write_text(
    json.dumps(analytics, ensure_ascii=False, indent=2), encoding="utf-8"
)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _auth_css() -> str:
    if not GOOGLE_CLIENT_ID:
        return ""
    return """
    #auth-overlay {
      position: fixed; inset: 0; background: rgba(10,10,30,.84);
      backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
      z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 24px;
    }
    .login-card {
      background: #fff; border-radius: 16px; padding: 40px 36px;
      max-width: 400px; width: 100%; box-shadow: 0 20px 60px rgba(0,0,0,.25);
      display: flex; flex-direction: column; align-items: center; gap: 0; text-align: center;
    }
    .login-brand { font-size: 20px; font-weight: 800; color: #4f46e5; margin-bottom: 22px; }
    .login-title { font-size: 22px; font-weight: 700; color: #111827; margin-bottom: 8px; }
    .login-desc  { font-size: 14px; color: #6b7280; line-height: 1.6; margin-bottom: 28px; }
    #google-btn  { margin-bottom: 20px; display: flex; justify-content: center; min-height: 44px; }
    .login-domains { font-size: 11px; color: #6b7280; background: #f9fafb;
                     border-radius: 8px; padding: 10px 14px; line-height: 1.9; width: 100%; }
    .login-domains strong { display: block; margin-bottom: 4px; color: #374151; }
    #auth-error { margin-top: 14px; padding: 10px 14px; background: #fee2e2;
                  color: #991b1b; border-radius: 8px; font-size: 13px;
                  display: none; width: 100%; text-align: left; }
    #user-info  { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #6b7280; }
    #user-info img { width: 24px; height: 24px; border-radius: 50%; }
    .btn-signout { background: none; border: 1px solid #e5e7eb; border-radius: 5px;
                   padding: 3px 9px; cursor: pointer; font-size: 11px; color: #6b7280; }
    .btn-signout:hover { background: #f3f4f6; }
    """


def _auth_overlay_html() -> str:
    if not GOOGLE_CLIENT_ID:
        return ""
    domains_html = "".join(f"<span>@{d}</span><br>" for d in _ALLOWED_DOMAINS)
    return f"""
  <div id="auth-overlay">
    <div class="login-card">
      <div class="login-brand">⚡ Auditor Minimal Club</div>
      <div class="login-title">Acesso restrito</div>
      <div class="login-desc">Faça login com sua conta corporativa para visualizar os relatórios de auditoria.</div>
      <div id="google-btn"></div>
      <div class="login-domains">
        <strong>Domínios autorizados</strong>
        {domains_html}
      </div>
      <div id="auth-error"></div>
    </div>
  </div>"""


def _auth_js() -> str:
    if not GOOGLE_CLIENT_ID:
        return ""
    domains_json = json.dumps(_ALLOWED_DOMAINS)
    return f"""
  const _ALLOWED = {domains_json};
  const _AUTH_KEY = 'auditor_auth_v1';
  const _AUTH_EXP = 7 * 24 * 60 * 60 * 1000;
  const _CLIENT_ID = '{GOOGLE_CLIENT_ID}';

  function _checkStored() {{
    try {{
      const raw = localStorage.getItem(_AUTH_KEY);
      if (!raw) return null;
      const a = JSON.parse(raw);
      if (Date.now() > a.exp) {{ localStorage.removeItem(_AUTH_KEY); return null; }}
      if (!_ALLOWED.includes(a.email.split('@')[1])) {{ localStorage.removeItem(_AUTH_KEY); return null; }}
      return a;
    }} catch(e) {{ return null; }}
  }}

  function _reveal(auth) {{
    const ov = document.getElementById('auth-overlay');
    if (ov) ov.style.display = 'none';
    const ui = document.getElementById('user-info');
    if (ui) {{
      const img = auth.picture
        ? '<img src="' + auth.picture + '" alt="">'
        : '';
      ui.innerHTML = img + '<span>' + auth.name + '</span>'
        + '<button class="btn-signout" onclick="_signOut()">Sair</button>';
    }}
  }}

  function _signOut() {{
    localStorage.removeItem(_AUTH_KEY);
    try {{ google.accounts.id.disableAutoSelect(); }} catch(e) {{}}
    location.reload();
  }}

  function _onCredential(resp) {{
    try {{
      const b64 = resp.credential.split('.')[1].replace(/-/g,'+').replace(/_/g,'/');
      const p = JSON.parse(atob(b64));
      const domain = p.email.split('@')[1];
      if (!_ALLOWED.includes(domain)) {{
        const el = document.getElementById('auth-error');
        el.textContent = 'Acesso negado. O e-mail ' + p.email + ' não pertence a um domínio autorizado.';
        el.style.display = 'block';
        return;
      }}
      const auth = {{ email: p.email, name: p.name || p.email,
                      picture: p.picture || '', exp: Date.now() + _AUTH_EXP }};
      localStorage.setItem(_AUTH_KEY, JSON.stringify(auth));
      _reveal(auth);
    }} catch(e) {{
      const el = document.getElementById('auth-error');
      el.textContent = 'Erro ao processar login. Tente novamente.';
      el.style.display = 'block';
    }}
  }}

  function _initLogin() {{
    if (!window.google || !google.accounts || !google.accounts.id) {{
      setTimeout(_initLogin, 120); return;
    }}
    google.accounts.id.initialize({{ client_id: _CLIENT_ID, callback: _onCredential, auto_select: false }});
    google.accounts.id.renderButton(
      document.getElementById('google-btn'),
      {{ theme: 'outline', size: 'large', text: 'signin_with', locale: 'pt-BR', width: 280 }}
    );
  }}

  (function() {{
    const stored = _checkStored();
    if (stored) {{ window.addEventListener('DOMContentLoaded', function() {{ _reveal(stored); }}); }}
    else {{ window.addEventListener('DOMContentLoaded', _initLogin); }}
  }})();
"""


def _gsi_script_tag() -> str:
    if not GOOGLE_CLIENT_ID:
        return ""
    return '<script src="https://accounts.google.com/gsi/client" async defer></script>'


def _user_info_html() -> str:
    if not GOOGLE_CLIENT_ID:
        return ""
    return '<div id="user-info"></div>'


# ── Carregar config (páginas, fluxos, popups) ─────────────────────────────────

def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


_pages_yaml    = _load_yaml(ROOT / "config" / "pages.yaml")
_audit_yaml    = _load_yaml(ROOT / "config" / "audit-config.yaml")
_schedule_yaml = _load_yaml(ROOT / "config" / "schedule.yaml")

cfg_pages  = _pages_yaml.get("pages") or _audit_yaml.get("critical_pages") or []
cfg_flows  = _audit_yaml.get("flows") or []
cfg_popups = _audit_yaml.get("popups") or []
base_url   = (_audit_yaml.get("store") or {}).get("base_url", "https://www.minimalclub.com.br")

_POPUP_CHECK_LABELS = {
    "dispara_apos_delay":        "Dispara após delay",
    "botao_fechar_visivel":      "Botão fechar visível",
    "fechar_funciona":           "Fechar funciona",
    "nao_bloqueia_scroll":       "Não bloqueia scroll",
    "nao_bloqueia_clique":       "Não bloqueia cliques",
    "nao_dispara_no_checkout":   "Não dispara no checkout",
    "nao_dispara_loop":          "Não reaparece na sessão",
}


def _popup_check_names(checks: list | None) -> list[str]:
    if not checks:
        return []
    result = []
    for item in (checks or []):
        for key, enabled in item.items():
            if enabled:
                result.append(_POPUP_CHECK_LABELS.get(key, key))
    return result


def _esc(s: object) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ── Helpers de HTML ───────────────────────────────────────────────────────────

last = runs[0] if runs else None


def _fmt_date(iso: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        brt = ZoneInfo("America/Sao_Paulo")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(brt).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso[:16].replace("T", " ")


def _status_badge(status: str, resultado: str) -> str:
    if status == "concluida" and resultado == "tudo_ok":
        return '<span class="badge b-ok">✓ Tudo OK</span>'
    if status == "concluida" and resultado == "com_falhas":
        return '<span class="badge b-fail">✗ Com falhas</span>'
    if status == "falhou":
        return '<span class="badge b-err">⚠ Erro</span>'
    if status == "em_andamento":
        return '<span class="badge b-run">↻ Rodando</span>'
    return f'<span class="badge b-gray">{status}</span>'


def _last_run_card() -> str:
    if not last:
        return '<div class="hero-card gray"><p>Nenhuma auditoria registrada ainda.</p></div>'
    date = _fmt_date(last["started_at"]) if last["started_at"] else "—"
    s, r = last["status"], last["resultado"]
    if s == "concluida" and r == "tudo_ok":
        cls, icon, title = "ok", "✓", "Tudo OK"
    elif s == "concluida" and r == "com_falhas":
        cls, icon, title = "fail", "✗", f'{last["total_falhou"]} falha(s) detectada(s)'
    elif s == "falhou":
        cls, icon, title = "err", "⚠", "Auditor com erro"
    else:
        cls, icon, title = "gray", "·", s
    tc, tp, tf, te = last["total_checks"] or 0, last["total_passou"], last["total_falhou"], last["total_erro"]
    rate = f"{round(tp / tc * 100)}%" if tc else "—"
    report_btn = (
        f'<a class="btn btn-outline" href="{last["report_url"]}" target="_blank">Ver relatório completo</a>'
        if last["report_url"] else ""
    )
    return f"""
    <div class="hero-card {cls}">
      <div class="hero-icon">{icon}</div>
      <div class="hero-info">
        <div class="hero-title">{title}</div>
        <div class="hero-date">Última auditoria: {date}</div>
        <div class="hero-stats">
          <span class="stat-pill ok">{tp} passaram</span>
          <span class="stat-pill fail">{tf} falharam</span>
          <span class="stat-pill err">{te} erros</span>
          <span class="stat-pill gray">{rate} taxa de sucesso</span>
        </div>
      </div>
      {report_btn}
    </div>"""


def _rows_html() -> str:
    if not runs:
        return '<tr><td colspan="8" class="empty">Nenhuma auditoria registrada ainda.</td></tr>'
    rows = []
    for r in runs:
        date  = _fmt_date(r["started_at"]) if r["started_at"] else "—"
        badge = _status_badge(r["status"], r["resultado"])
        tc    = r["total_checks"] or "—"
        tp, tf, te = r["total_passou"], r["total_falhou"], r["total_erro"]
        rate  = f"{round(tp / r['total_checks'] * 100)}%" if r["total_checks"] else "—"
        link  = (
            f'<a class="report-link" href="{r["report_url"]}" target="_blank">Ver relatório →</a>'
            if r["report_url"] else '<span class="muted">—</span>'
        )
        rows.append(f"""
        <tr>
          <td>{date}</td><td>{badge}</td>
          <td class="num">{tc}</td><td class="num ok">{tp}</td>
          <td class="num fail">{tf}</td><td class="num err">{te}</td>
          <td class="num">{rate}</td><td>{link}</td>
        </tr>""")
    return "\n".join(rows)


# ── Duração estimada e real ───────────────────────────────────────────────────

def _fmt_duration(secs: int) -> str:
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    if mins < 60:
        return f"{mins} min"
    return f"{mins // 60}h {mins % 60:02d}min"


def _estimate_duration() -> str:
    """Estimativa inicial baseada em fórmula — usada só quando não há histórico real."""
    SECS_PAGE_LH    = 35   # por página/viewport com Lighthouse (calibrado com execuções reais)
    SECS_PAGE_NO_LH = 10   # por página/viewport sem Lighthouse
    SECS_FLOW       = 20   # por fluxo/viewport
    SECS_POPUP      = 30   # por popup/viewport

    total = 0
    for p in cfg_pages:
        if not p.get("active", True):
            continue
        vps = len(p.get("viewports", ["desktop", "mobile"]))
        total += (SECS_PAGE_NO_LH if p.get("lighthouse_skip") else SECS_PAGE_LH) * vps
    for f in cfg_flows:
        if not f.get("active", True):
            continue
        total += SECS_FLOW * len(f.get("viewports", ["desktop", "mobile"]))
    for pop in cfg_popups:
        if not pop.get("active", True):
            continue
        total += SECS_POPUP * len(pop.get("viewports", ["desktop", "mobile"]))
    return _fmt_duration(total)


def _collect_durations(limit: int = 5) -> list[int]:
    """Retorna lista de durações reais (em segundos) das últimas `limit` execuções concluídas."""
    durations: list[int] = []
    for r in runs:
        if r.get("status") == "concluida" and r.get("started_at") and r.get("finished_at"):
            try:
                secs = int((
                    datetime.fromisoformat(r["finished_at"]) -
                    datetime.fromisoformat(r["started_at"])
                ).total_seconds())
                if secs > 0:
                    durations.append(secs)
            except Exception:
                pass
        if len(durations) >= limit:
            break
    return durations


def _duration_hint() -> str:
    """Linha de tempo para exibir perto do botão de rodar.
    Usa média de execuções reais quando disponível; cai para estimativa de fórmula caso contrário."""
    durations = _collect_durations()

    if durations:
        avg_secs = sum(durations) // len(durations)
        last_secs = durations[0]
        n = len(durations)
        label = "Duração típica" if n >= 3 else "Última execução"
        avg_str  = _fmt_duration(avg_secs)
        last_str = _fmt_duration(last_secs)
        if n >= 2 and last_secs != avg_secs:
            return (f"⏱ {label}: <strong>{avg_str}</strong> (média de {n} execuções)"
                    f" &nbsp;·&nbsp; Última: <strong>{last_str}</strong>")
        return f"⏱ {label}: <strong>{avg_str}</strong>"

    # Sem histórico: usa fórmula como estimativa inicial
    est = _estimate_duration()
    n_pages = sum(1 for p in cfg_pages if p.get("active", True))
    return (f"⏱ Estimativa inicial: <strong>{est}</strong> "
            f"({n_pages} pág. ativas — recalibra após a primeira execução)")


# ── Agenda HTML ──────────────────────────────────────────────────────────────

_DIAS_TO_ACTIVE_IDX: dict[str, set[int]] = {
    "Dias úteis (seg–sex)":     {0, 1, 2, 3, 4},
    "Dias úteis + sábado":      {0, 1, 2, 3, 4, 5},
    "Todos os dias":            {0, 1, 2, 3, 4, 5, 6},
    "Apenas fins de semana":    {5, 6},
    "Desativado (não agendar)": set(),
}
_DAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def _agenda_html() -> str:
    dias = _schedule_yaml.get("dias", "Dias úteis (seg–sex)")
    hora = _schedule_yaml.get("hora", "09:00")
    cron = _schedule_yaml.get("cron")

    active_days = _DIAS_TO_ACTIVE_IDX.get(str(dias), set())
    is_disabled = not bool(cron)

    day_pills = "".join(
        f'<div class="day-pill {"day-on" if i in active_days else "day-off"}">{lbl}</div>'
        for i, lbl in enumerate(_DAY_LABELS)
    )

    if is_disabled:
        status_html = '<div class="sched-status sched-status-off">Agendamento desativado — auditoria só roda manualmente</div>'
        hora_html   = '<div class="sched-hora muted">—</div>'
    else:
        status_html = f'<div class="sched-status sched-status-on">Auditoria automática ativa · {_esc(str(dias))} às {_esc(str(hora))} BRT</div>'
        hora_html   = f'<div class="sched-hora">{_esc(str(hora))} <span class="sched-tz">BRT</span></div>'

    cron_hint = (
        f'<div class="sched-cron-hint">Expressão cron (UTC): <code>{_esc(str(cron))}</code></div>'
        if cron else ""
    )

    return f"""
    <div class="card">
      <div class="card-header">Agenda de auditorias automáticas</div>
      <div style="padding:24px 24px 20px;display:flex;flex-direction:column;gap:20px">

        {status_html}

        <div>
          <div class="sched-label">Dias de execução</div>
          <div class="day-pills-row">{day_pills}</div>
          <div class="sched-dias-desc">{_esc(str(dias))}</div>
        </div>

        <div>
          <div class="sched-label">Horário</div>
          {hora_html}
          {cron_hint}
        </div>

        <div class="sched-action-row">
          <a class="btn btn-primary" href="{UPDATE_SCHEDULE_URL}" target="_blank">Alterar agenda</a>
          <span class="actions-hint">
            Abre o GitHub Actions → <strong>Run workflow</strong> → escolha dias e horário → confirme.
            A alteração é aplicada em segundos.
          </span>
        </div>

      </div>
    </div>

    <div class="card">
      <div class="card-header">Como alterar a agenda</div>
      <div style="padding:16px 24px 20px;display:flex;flex-direction:column;gap:12px;font-size:13px;line-height:1.7;color:var(--text)">
        <div style="display:flex;gap:12px;align-items:flex-start">
          <div class="sched-step-num">1</div>
          <div>Clique em <strong>Alterar agenda</strong> acima. Você será direcionado para o workflow no GitHub Actions.</div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start">
          <div class="sched-step-num">2</div>
          <div>Clique no botão <strong>Run workflow</strong> (canto superior direito da lista de execuções).</div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start">
          <div class="sched-step-num">3</div>
          <div>Selecione os <strong>Dias de execução</strong> e o <strong>Horário (BRT)</strong> desejados.</div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start">
          <div class="sched-step-num">4</div>
          <div>Clique em <strong>Run workflow</strong> novamente para confirmar. O workflow atualiza o arquivo de configuração e republica o dashboard automaticamente.</div>
        </div>
      </div>
    </div>"""


# ── Cobertura HTML ────────────────────────────────────────────────────────────

def _cobertura_html() -> str:
    active_pg  = sum(1 for p in cfg_pages  if p.get("active", True))
    active_fl  = sum(1 for f in cfg_flows  if f.get("active", True))
    active_pop = sum(1 for p in cfg_popups if p.get("active", True))

    # Páginas
    pg_cards = ""
    for p in cfg_pages:
        active  = p.get("active", True)
        vps     = p.get("viewports", ["desktop", "mobile"])
        vp_html = "".join(f'<span class="vp-badge">{_esc(v)}</span>' for v in vps)
        lh      = '<span class="mo-badge">sem Lighthouse</span>' if p.get("lighthouse_skip") else ""
        url     = _esc(p.get("url", ""))
        full    = _esc(base_url + p.get("url", ""))
        pg_cards += f"""
        <div class="cob-page-card {'cob-inactive' if not active else ''}">
          <div class="cob-page-status">{'● Ativa' if active else '○ Inativa'}</div>
          <div class="cob-page-name">{_esc(p.get('name',''))}</div>
          <a class="cob-page-url" href="{full}" target="_blank">{url}</a>
          <div class="cob-page-meta">{vp_html}{lh}</div>
        </div>"""

    # Fluxos
    fl_rows = ""
    for f in cfg_flows:
        active   = f.get("active", True)
        vps      = f.get("viewports", [])
        vp_html  = "".join(f'<span class="vp-badge">{_esc(v)}</span>' for v in vps)
        manual   = '<span class="mo-badge">manual only</span>' if f.get("run_mode") == "manual_only" else ""
        off      = '<span class="mo-badge">desativado</span>' if not active else ""
        steps    = len(f.get("steps", []))
        fl_rows += f"""
        <div class="item-row {'cob-row-inactive' if not active else ''}">
          <div class="cob-flow-dot {'dot-on' if active else 'dot-off'}"></div>
          <div class="item-info">
            <div class="item-name">{_esc(f.get('name',''))}</div>
            <div class="item-sub"><span class="muted">{steps} step{'s' if steps != 1 else ''}</span>
              {vp_html}{manual}{off}</div>
          </div>
        </div>"""

    # Popups
    pop_cards = ""
    for p in cfg_popups:
        active  = p.get("active", True)
        vps     = p.get("viewports", [])
        vp_html = "".join(f'<span class="vp-badge">{_esc(v)}</span>' for v in vps)
        checks  = _popup_check_names(p.get("checks"))
        chk_html = "".join(f'<span class="cob-check">✓ {_esc(c)}</span>' for c in checks)
        pop_cards += f"""
        <div class="cob-popup-card {'cob-inactive' if not active else ''}">
          <div class="cob-popup-head">
            <div class="cob-flow-dot {'dot-on' if active else 'dot-off'}"></div>
            <div>
              <div class="item-name">{_esc(p.get('name',''))}</div>
              <div class="item-sub">Disparado em <code>{_esc(p.get('trigger_page',''))}</code> {vp_html}</div>
            </div>
          </div>
          {f'<div class="cob-checks">{chk_html}</div>' if chk_html else ''}
        </div>"""

    como_funciona = """
    <div class="card">
      <div class="card-header">Como funciona a auditoria?</div>
      <div style="padding:20px 24px;display:flex;flex-direction:column;gap:24px">

        <div class="how-section">
          <div class="how-title">🌐 Saúde técnica de cada página</div>
          <div class="how-desc">Para cada página configurada, o auditor abre um navegador real (Chrome) e executa as seguintes verificações:</div>
          <div class="how-checks">
            <div class="how-check"><span class="how-icon">🔗</span><div><strong>Status HTTP</strong><br>Confirma que a página responde com código 200 (OK). Qualquer outro código — como 404 (não encontrada) ou 500 (erro de servidor) — gera uma falha.</div></div>
            <div class="how-check"><span class="how-icon">⚠️</span><div><strong>Erros de JavaScript</strong><br>Lê o console do navegador enquanto a página carrega. Erros de JS podem quebrar funcionalidades invisíveis para o usuário, como o botão de adicionar ao carrinho ou cálculos de desconto.</div></div>
            <div class="how-check"><span class="how-icon">📡</span><div><strong>Requisições com falha</strong><br>Monitora todas as chamadas de rede da página (imagens, scripts, APIs). Se alguma falhar, pode significar que um recurso visual não carregou ou que uma integração está quebrada.</div></div>
            <div class="how-check"><span class="how-icon">⏱️</span><div><strong>Tempo de carregamento</strong><br>Mede quantos milissegundos a página leva para carregar completamente (evento <em>load</em>). O limiar configurado é 5 segundos — acima disso o comprador abandona.</div></div>
            <div class="how-check"><span class="how-icon">🖼️</span><div><strong>LCP — Largest Contentful Paint</strong><br>Mede quando o maior elemento visível aparece na tela (geralmente a foto principal do produto). O Google considera acima de 2.5s uma experiência ruim. O auditor alerta acima de 4s.</div></div>
            <div class="how-check"><span class="how-icon">📐</span><div><strong>CLS — Cumulative Layout Shift</strong><br>Mede se elementos da página "pulam" de posição enquanto outros recursos carregam — por exemplo, um botão que se move antes do usuário conseguir clicar. Uma pontuação acima de 0.25 indica problema.</div></div>
            <div class="how-check"><span class="how-icon">👆</span><div><strong>FID — First Input Delay</strong><br>Mede quanto tempo o site demora para responder ao primeiro clique ou toque do usuário. Acima de 300ms o usuário percebe a lentidão como travamento.</div></div>
          </div>
        </div>

        <div class="how-section">
          <div class="how-title">🧭 Fluxos funcionais</div>
          <div class="how-desc">O auditor simula um comprador real navegando pelo site passo a passo, como se fosse um usuário com o dedo no celular. Se qualquer passo falhar, tira um screenshot automático e registra o erro com o detalhe técnico.</div>
          <div class="how-checks">
            <div class="how-check"><span class="how-icon">🏠</span><div><strong>Descoberta até PDP</strong><br>Abre a home → entra na coleção → clica no primeiro produto → confirma que a página de produto carregou com preço e imagem.</div></div>
            <div class="how-check"><span class="how-icon">👕</span><div><strong>Seleção de variante</strong><br>Verifica se o seletor de tamanho aparece e se, ao selecionar um tamanho, o botão "Adicionar ao carrinho" fica disponível.</div></div>
            <div class="how-check"><span class="how-icon">🛒</span><div><strong>Add to cart</strong><br>Clica em "Adicionar ao carrinho" e confirma que o contador do carrinho aumentou.</div></div>
            <div class="how-check"><span class="how-icon">🏷️</span><div><strong>Desconto progressivo</strong><br>Adiciona um produto da coleção de desconto progressivo e verifica que a mensagem de desconto aparece no carrinho.</div></div>
            <div class="how-check"><span class="how-icon">💳</span><div><strong>Início de checkout</strong><br>Adiciona item, vai ao carrinho, clica em "Finalizar compra" e confirma que o formulário de checkout renderizou com o campo de e-mail.</div></div>
            <div class="how-check"><span class="how-icon">☰</span><div><strong>Menu mobile (hamburger)</strong><br>No mobile, verifica se o botão de menu aparece, se abre ao clicar, e se os links de coleção estão visíveis dentro dele.</div></div>
            <div class="how-check"><span class="how-icon">🔍</span><div><strong>Busca</strong><br>Clica no ícone de busca, digita "camiseta" e verifica se os resultados aparecem. Clica no primeiro resultado e confirma redirecionamento para produto.</div></div>
          </div>
        </div>

        <div class="how-section">
          <div class="how-title">💬 Popup de captura</div>
          <div class="how-desc">Verifica o comportamento do popup Klaviyo que aparece para novos visitantes:</div>
          <div class="how-checks">
            <div class="how-check"><span class="how-icon">⏳</span><div><strong>Dispara após o delay</strong><br>Confirma que o popup aparece após ~3 segundos na home, como configurado.</div></div>
            <div class="how-check"><span class="how-icon">✕</span><div><strong>Botão fechar visível e funcional</strong><br>Verifica que o "X" está sempre visível e que clicar nele remove o popup completamente.</div></div>
            <div class="how-check"><span class="how-icon">🚫</span><div><strong>Não bloqueia a navegação</strong><br>Após fechar o popup, testa que o scroll e os cliques na página voltam a funcionar normalmente.</div></div>
            <div class="how-check"><span class="how-icon">🛒</span><div><strong>Não aparece no checkout</strong><br>Confirma que o popup nunca aparece na página de checkout — o que poderia fazer o comprador desistir na etapa mais crítica do funil.</div></div>
          </div>
        </div>

      </div>
    </div>"""

    return f"""
    <!-- Resumo -->
    <div class="cob-summary">
      <div class="cob-pill"><span class="cob-num">{active_pg}</span><span class="cob-lbl">páginas ativas</span></div>
      <div class="cob-pill"><span class="cob-num">{len(cfg_pages)-active_pg}</span><span class="cob-lbl">inativas</span></div>
      <div class="cob-sep"></div>
      <div class="cob-pill"><span class="cob-num">{active_fl}</span><span class="cob-lbl">fluxos ativos</span></div>
      <div class="cob-pill"><span class="cob-num">{len(cfg_flows)-active_fl}</span><span class="cob-lbl">inativos</span></div>
      <div class="cob-sep"></div>
      <div class="cob-pill"><span class="cob-num">{active_pop}</span><span class="cob-lbl">popup(s) verificado(s)</span></div>
      <div style="display:flex;gap:8px;margin-left:auto;flex-shrink:0;flex-wrap:wrap">
        <a class="btn btn-sm-outline btn-green" href="{ACTIVATE_ALL_URL}" target="_blank"
           title="Ativa TODAS as páginas de uma vez — abre o workflow no GitHub Actions (clique em Run workflow)">
          ✓ Ativar todas
        </a>
        <a class="btn btn-sm-outline btn-red" href="{DEACTIVATE_ALL_URL}" target="_blank"
           title="Desativa TODAS as páginas de uma vez — abre o workflow no GitHub Actions (clique em Run workflow)">
          ○ Desativar todas
        </a>
        <a class="btn btn-sm-outline" href="{EDIT_PAGES_URL}" target="_blank"
           title="Abre o editor do GitHub — cole quantas URLs quiser, uma por linha, e salve">
          ✏ Editar lista
        </a>
        <a class="btn btn-sm-outline" href="{MANAGE_WORKFLOW_URL}" target="_blank"
           title="Formulário rápido para adicionar ou remover URLs via Actions">
          ⚡ Ação rápida
        </a>
      </div>
    </div>

    <!-- Páginas -->
    <div class="card">
      <div class="card-header">Páginas auditadas</div>
      <div style="padding:16px"><div class="cob-pages-grid">{pg_cards}</div></div>
    </div>

    <!-- Fluxos -->
    <div class="card">
      <div class="card-header">Fluxos funcionais</div>
      <div style="padding:12px 16px"><div class="item-list">{fl_rows}</div></div>
    </div>

    <!-- Popups -->
    <div class="card">
      <div class="card-header">Popups verificados</div>
      <div style="padding:12px 16px">{pop_cards if pop_cards else '<div class="empty">Nenhum popup configurado</div>'}</div>
    </div>

    {como_funciona}"""


# ── Analytics JS ─────────────────────────────────────────────────────────────

_ANALYTICS_JS_FUNCS = """
var _anlz_loaded = false;
function loadAnalise() {
  if (_anlz_loaded) return;
  _anlz_loaded = true;
  var d = _ANALYTICS;
  var el = document.getElementById('analise-content');
  if (!d || !d.daily || !d.daily.length) {
    el.innerHTML = '<div style="text-align:center;padding:48px;color:#9ca3af;font-size:13px">Dados de an\\u00e1lise n\\u00e3o dispon\\u00edveis ainda.<br>Execute uma auditoria completa para gerar o hist\\u00f3rico.</div>';
    return;
  }
  el.innerHTML = _anlzHL(d) + _anlzTopFail(d) + _anlzPeriod(d) + _anlzCmp(d);
  document.getElementById('an-apply').addEventListener('click', function() {
    document.getElementById('an-chart-wrap').innerHTML = _anlzChart(_anlzFilter(d.daily));
  });
  document.getElementById('an-cmp-btn').addEventListener('click', function() {
    document.getElementById('an-cmp-result').innerHTML = _anlzCmpResult(d.daily);
  });
}
function _anlzFilter(daily) {
  var f = document.getElementById('an-from').value;
  var t = document.getElementById('an-to').value;
  return (daily||[]).filter(function(d){ return (!f||d.date>=f)&&(!t||d.date<=t); });
}
function _anlzHL(d) {
  var hl = d.highlights || {};
  var ok  = (hl.always_ok||[]).map(function(n){ return '<div class="an-hl-item">✓ '+_ae(n)+'</div>'; }).join('')
            || '<div class="an-hl-item" style="color:#9ca3af">Sem dados suficientes</div>';
  var att = (hl.attention||[]).map(function(n){ return '<div class="an-hl-item">⚠ '+_ae(n)+'</div>'; }).join('')
            || '<div class="an-hl-item" style="color:#9ca3af">Nenhuma m\\u00e9trica cr\\u00edtica</div>';
  return '<div class="an-section"><div class="an-title">Vis\\u00e3o geral — \\u00faltimos 30 dias</div>'
       + '<div class="an-body"><div class="an-hl-grid">'
       + '<div class="an-hl-card an-hl-ok"><div class="an-hl-head">✓ Funcionando bem</div>'+ok+'</div>'
       + '<div class="an-hl-card an-hl-att"><div class="an-hl-head">⚠ Precisa de aten\\u00e7\\u00e3o</div>'+att+'</div>'
       + '</div></div></div>';
}
function _anlzTopFail(d) {
  var rows = (d.top_failures||[]).map(function(f,i){
    return '<tr><td>'+(i+1)+'</td><td>'+_ae(f.check_name)+'</td>'
         + '<td style="color:var(--fail);font-weight:700">'+(f.fail_count||0)+'</td>'
         + '<td>'+(f.last_seen||'—')+'</td></tr>';
  }).join('');
  var body = rows
    ? '<table><thead><tr><th>#</th><th>Checagem</th><th>Ocorr\\u00eancias</th><th>\\u00daltimo registro</th></tr></thead><tbody>'+rows+'</tbody></table>'
    : '<div style="text-align:center;padding:24px;color:#9ca3af">Nenhum erro registrado.</div>';
  return '<div class="an-section"><div class="an-title">Erros mais recorrentes — \\u00faltimos 60 dias</div>'+body+'</div>';
}
function _anlzPeriod(d) {
  var today = new Date(), from30 = new Date();
  from30.setDate(from30.getDate()-30);
  var toS = today.toISOString().slice(0,10), frS = from30.toISOString().slice(0,10);
  var filtered = (d.daily||[]).filter(function(x){ return x.date>=frS; });
  return '<div class="an-section"><div class="an-title">Evolu\\u00e7\\u00e3o por per\\u00edodo</div>'
       + '<div class="an-body">'
       + '<div class="an-filter"><label>De</label><input type="date" id="an-from" value="'+frS+'">'
       + '<label>at\\u00e9</label><input type="date" id="an-to" value="'+toS+'">'
       + '<button id="an-apply">Aplicar</button></div>'
       + '<div id="an-chart-wrap">'+_anlzChart(filtered)+'</div>'
       + '</div></div>';
}
function _anlzChart(days) {
  if (!days||!days.length) return '<div style="text-align:center;padding:24px;color:#9ca3af">Sem dados para o per\\u00edodo.</div>';
  return '<div class="an-chart">'
    + days.map(function(d){
        var h=Math.max(4,d.pass_rate||0), c=d.pass_rate>=90?'#10b981':d.pass_rate>=70?'#f59e0b':'#ef4444';
        return '<div class="an-bar-col"><div class="an-bar" style="height:'+h+'%;background:'+c
             + '" title="'+d.pass_rate+'% — '+d.date+' | '+(d.total_falhou||0)+' falha(s)"></div>'
             + '<div class="an-bar-lbl">'+d.date.slice(5)+'</div></div>';
      }).join('')
    + '</div><div style="display:flex;gap:16px;margin-top:8px;font-size:12px;color:var(--muted)">'
    + '<span style="color:#10b981">■ ≥90%</span>'
    + '<span style="color:#f59e0b">■ 70–89%</span>'
    + '<span style="color:#ef4444">■ &lt;70%</span></div>';
}
function _anlzCmp(d) {
  var t=new Date(), d14=new Date(), d28=new Date();
  d14.setDate(d14.getDate()-14); d28.setDate(d28.getDate()-28);
  var fmt=function(dt){ return dt.toISOString().slice(0,10); };
  return '<div class="an-section"><div class="an-title">Comparar per\\u00edodos</div>'
       + '<div class="an-body">'
       + '<div class="an-compare-grid" style="margin-bottom:14px">'
       + '<div><div class="an-compare-head">Per\\u00edodo A</div><div class="an-filter" style="margin-bottom:0">'
       + '<label>De</label><input type="date" id="an-a-from" value="'+fmt(d28)+'">'
       + '<label>at\\u00e9</label><input type="date" id="an-a-to" value="'+fmt(d14)+'">'
       + '</div></div>'
       + '<div><div class="an-compare-head">Per\\u00edodo B</div><div class="an-filter" style="margin-bottom:0">'
       + '<label>De</label><input type="date" id="an-b-from" value="'+fmt(d14)+'">'
       + '<label>at\\u00e9</label><input type="date" id="an-b-to" value="'+fmt(t)+'">'
       + '</div></div></div>'
       + '<div style="text-align:center;margin-bottom:14px"><button id="an-cmp-btn">Comparar</button></div>'
       + '<div id="an-cmp-result"></div></div></div>';
}
function _anlzCmpResult(daily) {
  var fa=document.getElementById('an-a-from').value, ta=document.getElementById('an-a-to').value;
  var fb=document.getElementById('an-b-from').value, tb=document.getElementById('an-b-to').value;
  function agg(f,t){
    var rows=(daily||[]).filter(function(d){ return d.date>=f&&d.date<=t; });
    if (!rows.length) return null;
    var tc=rows.reduce(function(s,d){ return s+(d.total_checks||0); },0);
    var tp=rows.reduce(function(s,d){ return s+(d.total_passou||0); },0);
    var tf=rows.reduce(function(s,d){ return s+(d.total_falhou||0); },0);
    return { runs:rows.length, tc:tc, tp:tp, tf:tf, rate:tc?Math.round(tp/tc*100):0 };
  }
  var a=agg(fa,ta), b=agg(fb,tb);
  if (!a||!b) return '<div style="text-align:center;padding:16px;color:#9ca3af">Sem dados para os per\\u00edodos selecionados.</div>';
  var diff=b.rate-a.rate, ds=(diff>=0?'+':'')+diff+' p.p.';
  var dc=diff>0?'var(--ok)':diff<0?'var(--fail)':'var(--muted)';
  function card(lbl,period,s){
    var c=s.rate>=90?'var(--ok)':s.rate>=70?'var(--err)':'var(--fail)';
    return '<div class="an-compare-card"><div class="an-compare-head">'+lbl+' <span style="font-weight:400">('+period+')</span></div>'
         + '<div class="an-stat-big" style="color:'+c+'">'+s.rate+'%</div>'
         + '<div class="an-stat-sub">'+s.tc+' checagens · '+s.tf+' falha(s) · '+s.runs+' run(s)</div></div>';
  }
  return '<div class="an-compare-grid">'+card('Per\\u00edodo A',fa+' a '+ta,a)+card('Per\\u00edodo B',fb+' a '+tb,b)+'</div>'
       + '<div style="text-align:center;padding:16px;font-size:15px">Varia\\u00e7\\u00e3o: <strong style="color:'+dc+';font-size:20px">'+ds+'</strong></div>';
}
function _ae(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
"""


def _analytics_js(data: dict) -> str:
    return "var _ANALYTICS = " + json.dumps(data, ensure_ascii=False) + ";\n" + _ANALYTICS_JS_FUNCS


# ── Gerar index.html ──────────────────────────────────────────────────────────

from zoneinfo import ZoneInfo as _ZoneInfo
generated_at = datetime.now(_ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")

HTML = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Auditor — Minimal Club</title>
  {_gsi_script_tag()}
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --pri:#4f46e5; --ok:#10b981; --fail:#ef4444; --err:#f59e0b;
      --bg:#f5f6fa; --card:#fff; --border:#e5e7eb;
      --text:#111827; --muted:#6b7280; --radius:10px;
    }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
            font-size:14px; background:var(--bg); color:var(--text); min-height:100vh; }}

    /* Header */
    .header {{ background:#fff; border-bottom:1px solid var(--border);
               padding:0 32px; height:54px; display:flex; align-items:center;
               justify-content:space-between; position:sticky; top:0; z-index:10; }}
    .logo {{ font-weight:700; font-size:15px; color:var(--pri); }}
    .header-meta {{ font-size:12px; color:var(--muted); }}

    /* Tabs */
    .tab-nav {{ background:#fff; border-bottom:1px solid var(--border);
                display:flex; padding:0 32px; gap:4px; }}
    .tab-btn {{ padding:12px 18px; border:none; background:none; cursor:pointer;
                font-size:13px; font-weight:600; color:var(--muted);
                border-bottom:2px solid transparent; transition:all .15s; }}
    .tab-btn:hover {{ color:var(--text); }}
    .tab-btn.active {{ color:var(--pri); border-bottom-color:var(--pri); }}
    .tab-pane {{ display:none; }}
    .tab-pane.active {{ display:block; }}

    .main {{ max-width:1000px; margin:0 auto; padding:28px 24px; }}

    /* Hero */
    .hero-card {{ display:flex; align-items:center; gap:20px; padding:22px 24px;
                  border-radius:var(--radius); border:1px solid var(--border);
                  margin-bottom:20px; background:var(--card); border-left:5px solid; }}
    .hero-card.ok   {{ border-left-color:var(--ok); }}
    .hero-card.fail {{ border-left-color:var(--fail); }}
    .hero-card.err  {{ border-left-color:var(--err); }}
    .hero-card.gray {{ border-left-color:var(--border); }}
    .hero-icon {{ font-size:36px; flex-shrink:0; width:48px; text-align:center; }}
    .hero-card.ok   .hero-icon {{ color:var(--ok); }}
    .hero-card.fail .hero-icon {{ color:var(--fail); }}
    .hero-card.err  .hero-icon {{ color:var(--err); }}
    .hero-info {{ flex:1; }}
    .hero-title {{ font-size:18px; font-weight:700; margin-bottom:4px; }}
    .hero-date  {{ font-size:12px; color:var(--muted); margin-bottom:10px; }}
    .hero-stats {{ display:flex; gap:8px; flex-wrap:wrap; }}
    .stat-pill  {{ padding:3px 10px; border-radius:999px; font-size:12px; font-weight:600; }}
    .stat-pill.ok   {{ background:#d1fae5; color:#065f46; }}
    .stat-pill.fail {{ background:#fee2e2; color:#991b1b; }}
    .stat-pill.err  {{ background:#fef3c7; color:#92400e; }}
    .stat-pill.gray {{ background:#f3f4f6; color:var(--muted); }}

    /* Buttons */
    .btn {{ display:inline-flex; align-items:center; gap:6px; padding:9px 18px;
            border-radius:8px; border:none; cursor:pointer; font-size:14px;
            font-weight:600; text-decoration:none; transition:opacity .15s; }}
    .btn:hover {{ opacity:.85; }}
    .btn-primary {{ background:var(--pri); color:#fff; }}
    .btn-outline {{ background:#fff; color:var(--pri); border:1.5px solid var(--pri); }}
    .btn-sm-outline {{ padding:6px 12px; font-size:12px; background:#fff;
                       color:var(--pri); border:1.5px solid var(--pri);
                       border-radius:6px; text-decoration:none; font-weight:600; white-space:nowrap; }}
    .btn-sm-outline:hover {{ opacity:.8; }}
    .btn-green {{ color:#15803d; border-color:#15803d; }}
    .btn-red   {{ color:#b91c1c; border-color:#b91c1c; }}

    .actions-row {{ display:flex; align-items:center; gap:12px; margin-bottom:24px; flex-wrap:wrap; }}
    .actions-hint {{ font-size:12px; color:var(--muted); }}

    /* Cards / Table */
    .card {{ background:var(--card); border:1px solid var(--border);
             border-radius:var(--radius); overflow:hidden; margin-bottom:16px; }}
    .card-header {{ padding:14px 18px; border-bottom:1px solid var(--border);
                    font-weight:600; font-size:14px; display:flex; align-items:center; gap:8px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th {{ text-align:left; padding:9px 14px; background:#f9fafb;
          border-bottom:1px solid var(--border); font-size:11px; font-weight:600;
          color:var(--muted); text-transform:uppercase; letter-spacing:.4px; white-space:nowrap; }}
    td {{ padding:10px 14px; border-bottom:1px solid #f3f4f6; vertical-align:middle; }}
    tr:last-child td {{ border-bottom:none; }}
    tr:hover td {{ background:#fafafa; }}
    .num {{ font-family:monospace; text-align:right; font-size:13px; }}
    .num.ok   {{ color:var(--ok); font-weight:600; }}
    .num.fail {{ color:var(--fail); font-weight:600; }}
    .num.err  {{ color:var(--err); font-weight:600; }}

    .badge {{ display:inline-block; padding:3px 9px; border-radius:5px; font-size:11px; font-weight:700; }}
    .b-ok   {{ background:#d1fae5; color:#065f46; }}
    .b-fail {{ background:#fee2e2; color:#991b1b; }}
    .b-err  {{ background:#fef3c7; color:#92400e; }}
    .b-run  {{ background:#ede9fe; color:#4f46e5; }}
    .b-gray {{ background:#f3f4f6; color:var(--muted); }}

    .vp-badge {{ background:#ede9fe; color:#4f46e5; border-radius:4px; padding:1px 6px; font-size:11px; font-weight:600; }}
    .mo-badge {{ background:#f3f4f6; color:var(--muted); border-radius:4px; padding:1px 6px; font-size:11px; }}

    .report-link {{ color:var(--pri); text-decoration:none; font-weight:500; }}
    .report-link:hover {{ text-decoration:underline; }}
    .muted {{ color:var(--muted); }}
    .empty {{ text-align:center; padding:28px; color:var(--muted); }}

    /* Cobertura */
    .cob-summary {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap;
                    background:#fff; border:1px solid var(--border); border-radius:var(--radius);
                    padding:16px 20px; margin-bottom:20px; }}
    .cob-pill {{ display:flex; flex-direction:column; align-items:center; min-width:72px; }}
    .cob-num  {{ font-size:28px; font-weight:700; color:var(--pri); line-height:1; }}
    .cob-lbl  {{ font-size:11px; color:var(--muted); margin-top:2px; text-align:center; }}
    .cob-sep  {{ width:1px; height:40px; background:var(--border); margin:0 4px; }}

    .cob-pages-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(210px,1fr)); gap:12px; }}
    .cob-page-card {{ border:1.5px solid var(--ok); border-radius:8px; padding:14px;
                      display:flex; flex-direction:column; gap:4px; }}
    .cob-page-card.cob-inactive {{ border-color:var(--border); opacity:.6; }}
    .cob-page-status {{ font-size:11px; font-weight:700; color:var(--ok); }}
    .cob-page-card.cob-inactive .cob-page-status {{ color:var(--muted); }}
    .cob-page-name {{ font-size:13px; font-weight:600; }}
    .cob-page-url  {{ font-size:11px; font-family:monospace; color:var(--pri);
                      text-decoration:none; word-break:break-all; }}
    .cob-page-url:hover {{ text-decoration:underline; }}
    .cob-page-meta {{ display:flex; gap:4px; flex-wrap:wrap; margin-top:4px; }}

    .item-list {{ display:flex; flex-direction:column; gap:10px; }}
    .item-row  {{ display:flex; align-items:flex-start; gap:10px; }}
    .item-name {{ font-size:13px; font-weight:600; }}
    .item-sub  {{ display:flex; gap:5px; flex-wrap:wrap; align-items:center; margin-top:3px; font-size:12px; color:var(--muted); }}
    .cob-row-inactive {{ opacity:.55; }}
    .cob-flow-dot {{ width:10px; height:10px; border-radius:50%; flex-shrink:0; margin-top:3px; }}
    .dot-on  {{ background:var(--ok); }}
    .dot-off {{ background:var(--border); }}

    .cob-popup-card {{ border:1px solid var(--border); border-radius:8px; padding:14px; margin-bottom:10px; }}
    .cob-popup-card.cob-inactive {{ opacity:.55; }}
    .cob-popup-head {{ display:flex; align-items:flex-start; gap:10px; margin-bottom:10px; }}
    .cob-checks {{ display:flex; flex-wrap:wrap; gap:6px; }}
    .cob-check {{ background:#f0fdf4; color:#166534; border:1px solid #bbf7d0;
                  border-radius:5px; padding:3px 9px; font-size:11px; font-weight:500; }}

    /* Como funciona */
    .how-section {{ display:flex; flex-direction:column; gap:12px; }}
    .how-title {{ font-size:15px; font-weight:700; }}
    .how-desc  {{ font-size:13px; color:var(--muted); line-height:1.6; }}
    .how-checks {{ display:flex; flex-direction:column; gap:10px; }}
    .how-check {{ display:flex; gap:12px; align-items:flex-start;
                  background:#f9fafb; border-radius:8px; padding:12px 14px; }}
    .how-icon {{ font-size:20px; flex-shrink:0; width:28px; text-align:center; }}
    .how-check div {{ font-size:13px; line-height:1.6; }}
    .how-check strong {{ display:block; margin-bottom:2px; }}

    /* Footer / banner */
    .footer {{ margin-top:40px; text-align:center; font-size:11px; color:#9ca3af; }}
    #running-banner {{ display:none; background:#ede9fe; color:#4f46e5; padding:10px 24px;
                       font-size:13px; font-weight:500; text-align:center; }}
    .spinner {{ display:inline-block; width:12px; height:12px; border:2px solid rgba(79,70,229,.3);
                border-top-color:var(--pri); border-radius:50%;
                animation:spin .7s linear infinite; vertical-align:middle; margin-right:6px; }}
    @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
    /* Analytics tab */
    .an-section {{ background:var(--card); border:1px solid var(--border);
                   border-radius:var(--radius); margin-bottom:16px; overflow:hidden; }}
    .an-title   {{ padding:14px 18px; border-bottom:1px solid var(--border);
                   font-weight:700; font-size:14px; }}
    .an-body    {{ padding:18px; }}
    .an-hl-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
    @media (max-width:640px) {{ .an-hl-grid {{ grid-template-columns:1fr; }} }}
    .an-hl-card  {{ border-radius:8px; padding:14px; }}
    .an-hl-ok    {{ background:#f0fdf4; border:1px solid #bbf7d0; }}
    .an-hl-att   {{ background:#fef2f2; border:1px solid #fecaca; }}
    .an-hl-head  {{ font-size:12px; font-weight:700; margin-bottom:10px; }}
    .an-hl-ok .an-hl-head {{ color:#15803d; }}
    .an-hl-att .an-hl-head {{ color:#dc2626; }}
    .an-hl-item  {{ font-size:13px; padding:4px 0; border-bottom:1px solid rgba(0,0,0,.05); }}
    .an-hl-item:last-child {{ border-bottom:none; }}
    .an-chart    {{ display:flex; align-items:flex-end; gap:3px; height:110px; overflow-x:auto; padding-bottom:2px; }}
    .an-bar-col  {{ display:flex; flex-direction:column; align-items:center; flex-shrink:0; }}
    .an-bar      {{ width:20px; border-radius:3px 3px 0 0; min-height:4px; transition:opacity .15s; }}
    .an-bar:hover {{ opacity:.7; cursor:default; }}
    .an-bar-lbl  {{ font-size:9px; color:var(--muted); margin-top:3px; }}
    .an-filter   {{ display:flex; gap:8px; align-items:center; margin-bottom:14px; flex-wrap:wrap; }}
    .an-filter label {{ font-size:12px; color:var(--muted); }}
    .an-filter input[type=date] {{ border:1px solid var(--border); border-radius:6px;
                                    padding:5px 9px; font-size:12px; font-family:inherit; }}
    .an-filter button, #an-cmp-btn {{ padding:6px 16px; background:var(--pri); color:#fff;
                     border:none; border-radius:6px; cursor:pointer; font-size:12px; font-weight:600; }}
    .an-compare-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
    @media (max-width:640px) {{ .an-compare-grid {{ grid-template-columns:1fr; }} }}
    .an-compare-card {{ border:1px solid var(--border); border-radius:8px; padding:14px; }}
    .an-compare-head {{ font-size:12px; font-weight:700; color:var(--muted); margin-bottom:10px; }}
    .an-stat-big {{ font-size:36px; font-weight:800; }}
    .an-stat-sub {{ font-size:12px; color:var(--muted); margin-top:4px; }}
    /* Agenda tab */
    .day-pills-row {{ display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 6px; }}
    .day-pill {{ padding:7px 14px; border-radius:8px; font-size:13px; font-weight:700; }}
    .day-on  {{ background:#ede9fe; color:#4f46e5; }}
    .day-off {{ background:#f3f4f6; color:#9ca3af; }}
    .sched-label {{ font-size:11px; font-weight:700; color:var(--muted);
                    text-transform:uppercase; letter-spacing:.4px; margin-bottom:2px; }}
    .sched-status {{ padding:12px 16px; border-radius:8px; font-size:13px; font-weight:600; }}
    .sched-status-on  {{ background:#d1fae5; color:#065f46; }}
    .sched-status-off {{ background:#fee2e2; color:#991b1b; }}
    .sched-hora {{ font-size:30px; font-weight:800; color:var(--text); margin:6px 0 2px; }}
    .sched-tz {{ font-size:14px; font-weight:600; color:var(--muted); }}
    .sched-dias-desc {{ font-size:13px; color:var(--muted); }}
    .sched-cron-hint {{ font-size:11px; color:var(--muted); margin-top:4px; }}
    .sched-action-row {{ display:flex; align-items:center; gap:16px; flex-wrap:wrap; }}
    .sched-step-num {{ width:24px; height:24px; border-radius:50%; background:var(--pri);
                       color:#fff; font-size:12px; font-weight:700; display:flex;
                       align-items:center; justify-content:center; flex-shrink:0; margin-top:2px; }}
    {_auth_css()}
  </style>
</head>
<body>
  {_auth_overlay_html()}
  <div id="running-banner">
    <span class="spinner"></span> Auditoria em andamento no GitHub Actions — página atualiza ao concluir
  </div>

  <header class="header">
    <span class="logo">⚡ Auditor Minimal Club</span>
    <div style="display:flex;align-items:center;gap:16px">
      <span class="header-meta">Atualizado em {generated_at}</span>
      {_user_info_html()}
    </div>
  </header>

  <nav class="tab-nav">
    <button class="tab-btn active" onclick="switchTab('historico', this)">📋 Histórico</button>
    <button class="tab-btn"        onclick="switchTab('cobertura', this)">🔍 Cobertura</button>
    <button class="tab-btn"        onclick="switchTab('analise',   this)">📊 Análise</button>
    <button class="tab-btn"        onclick="switchTab('agenda',    this)">📅 Agenda</button>
  </nav>

  <!-- ── Aba: Histórico ───────────────────────────────────────────── -->
  <div id="tab-historico" class="tab-pane active">
    <div class="main">
      {_last_run_card()}

      <div class="actions-row">
        <a class="btn btn-primary" href="{ACTIONS_WORKFLOW_URL}" target="_blank">▶ Rodar Auditoria Agora</a>
        <div style="display:flex;flex-direction:column;gap:4px">
          <span class="actions-hint">
            Abre o GitHub Actions → clique em <strong>Run workflow</strong>.
          </span>
          <span class="actions-hint">
            {_duration_hint()}
          </span>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          Histórico de auditorias
          <span style="font-weight:400;color:var(--muted);font-size:12px;margin-left:auto">{len(runs)} execuções</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Data</th><th>Resultado</th>
              <th style="text-align:right">Total</th><th style="text-align:right">OK</th>
              <th style="text-align:right">Falhas</th><th style="text-align:right">Erros</th>
              <th style="text-align:right">Taxa</th><th>Relatório</th>
            </tr>
          </thead>
          <tbody>{_rows_html()}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ── Aba: Cobertura ──────────────────────────────────────────── -->
  <div id="tab-cobertura" class="tab-pane">
    <div class="main">
      {_cobertura_html()}
    </div>
  </div>

  <!-- ── Aba: Análise ───────────────────────────────────────────── -->
  <div id="tab-analise" class="tab-pane">
    <div class="main">
      <div id="analise-content"></div>
    </div>
  </div>

  <!-- ── Aba: Agenda ────────────────────────────────────────────── -->
  <div id="tab-agenda" class="tab-pane">
    <div class="main">
      {_agenda_html()}
    </div>
  </div>

  <div class="footer">
    Auditor Técnico Minimal Club &nbsp;·&nbsp;
    <a href="{ACTIONS_WORKFLOW_URL}" target="_blank" style="color:inherit">GitHub Actions</a>
  </div>

  <script>
    {_auth_js()}
    {_analytics_js(analytics)}
    function switchTab(name, btn) {{
      document.querySelectorAll('.tab-pane').forEach(function(p) {{ p.classList.remove('active'); }});
      document.querySelectorAll('.tab-btn').forEach(function(b) {{ b.classList.remove('active'); }});
      document.getElementById('tab-' + name).classList.add('active');
      btn.classList.add('active');
      if (name === 'analise') loadAnalise();
    }}

    // Detecta workflow em andamento
    (function() {{
      var repo = "{GITHUB_REPO}";
      if (!repo) return;
      fetch("https://api.github.com/repos/" + repo + "/actions/workflows/audit.yml/runs?per_page=1&status=in_progress",
            {{ headers: {{ Accept: "application/vnd.github+json" }} }})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          if (d.total_count && d.total_count > 0) {{
            document.getElementById("running-banner").style.display = "block";
            setTimeout(function() {{ location.reload(); }}, 60000);
          }}
        }})
        .catch(function() {{}});
    }})();
  </script>
</body>
</html>"""

(OUTPUT_DIR / "index.html").write_text(HTML, encoding="utf-8")

print(f"GitHub Pages gerado:")
print(f"  {len(runs)} runs · {len(cfg_pages)} páginas · {len(cfg_flows)} fluxos · {len(cfg_popups)} popups")
print(f"  {copied} relatório(s) HTML copiado(s)")
print(f"  Output: {OUTPUT_DIR}")
if PAGES_BASE:
    print(f"  URL: {PAGES_BASE}")
