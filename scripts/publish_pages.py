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

from auditor.storage.history import DEFAULT_DB_PATH, get_recent_runs  # noqa: E402

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
PAGES_BASE = (
    f"https://{GITHUB_REPO.split('/')[0]}.github.io/{GITHUB_REPO.split('/')[-1]}"
    if GITHUB_REPO else ""
)


# ── Copiar relatórios e screenshots ───────────────────────────────────────────

copied = 0
for html_file in REPORTS_DIR.glob("*.html"):
    shutil.copy2(html_file, OUTPUT_REPORTS / html_file.name)
    copied += 1

screenshots_src = REPORTS_DIR / "screenshots"
if screenshots_src.exists():
    shutil.copytree(screenshots_src, OUTPUT_REPORTS / "screenshots", dirs_exist_ok=True)


# ── Histórico do SQLite ───────────────────────────────────────────────────────

db_path  = ROOT / "auditor-history.db"
runs_raw = get_recent_runs(limit=200, db_path=db_path) if db_path.exists() else []


def _report_url(started_at: str | None) -> str | None:
    if not started_at:
        return None
    try:
        dt = datetime.fromisoformat(started_at)
        filename = dt.strftime("%Y-%m-%dT%H-%M-%S") + ".html"
        if (OUTPUT_REPORTS / filename).exists():
            return f"reports/{filename}"
    except Exception:
        pass
    return None


runs = [
    {
        "run_id":       r.get("run_id", ""),
        "started_at":   r.get("started_at", ""),
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

(OUTPUT_DIR / "reports.json").write_text(
    json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8"
)


# ── Carregar config (páginas, fluxos, popups) ─────────────────────────────────

def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


_pages_yaml  = _load_yaml(ROOT / "config" / "pages.yaml")
_audit_yaml  = _load_yaml(ROOT / "config" / "audit-config.yaml")

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
        return datetime.fromisoformat(iso).astimezone().strftime("%d/%m/%Y %H:%M")
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
      <a class="btn btn-sm-outline" href="{MANAGE_WORKFLOW_URL}" target="_blank" style="margin-left:auto">
        + Gerenciar páginas
      </a>
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
    </div>"""


# ── Gerar index.html ──────────────────────────────────────────────────────────

generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

HTML = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Auditor — Minimal Club</title>
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

    /* Footer / banner */
    .footer {{ margin-top:40px; text-align:center; font-size:11px; color:#9ca3af; }}
    #running-banner {{ display:none; background:#ede9fe; color:#4f46e5; padding:10px 24px;
                       font-size:13px; font-weight:500; text-align:center; }}
    .spinner {{ display:inline-block; width:12px; height:12px; border:2px solid rgba(79,70,229,.3);
                border-top-color:var(--pri); border-radius:50%;
                animation:spin .7s linear infinite; vertical-align:middle; margin-right:6px; }}
    @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
  </style>
</head>
<body>
  <div id="running-banner">
    <span class="spinner"></span> Auditoria em andamento no GitHub Actions — página atualiza ao concluir
  </div>

  <header class="header">
    <span class="logo">⚡ Auditor Minimal Club</span>
    <span class="header-meta">Atualizado em {generated_at}</span>
  </header>

  <nav class="tab-nav">
    <button class="tab-btn active" onclick="switchTab('historico', this)">📋 Histórico</button>
    <button class="tab-btn"        onclick="switchTab('cobertura', this)">🔍 Cobertura</button>
  </nav>

  <!-- ── Aba: Histórico ───────────────────────────────────────────── -->
  <div id="tab-historico" class="tab-pane active">
    <div class="main">
      {_last_run_card()}

      <div class="actions-row">
        <a class="btn btn-primary" href="{ACTIONS_WORKFLOW_URL}" target="_blank">▶ Rodar Auditoria Agora</a>
        <span class="actions-hint">
          Abre o GitHub Actions → clique em <strong>Run workflow</strong>.
        </span>
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

  <div class="footer">
    Auditor Técnico Minimal Club &nbsp;·&nbsp;
    <a href="{ACTIONS_WORKFLOW_URL}" target="_blank" style="color:inherit">GitHub Actions</a>
  </div>

  <script>
    function switchTab(name, btn) {{
      document.querySelectorAll('.tab-pane').forEach(function(p) {{ p.classList.remove('active'); }});
      document.querySelectorAll('.tab-btn').forEach(function(b) {{ b.classList.remove('active'); }});
      document.getElementById('tab-' + name).classList.add('active');
      btn.classList.add('active');
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
