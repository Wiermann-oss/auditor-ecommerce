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

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from auditor.storage.history import DEFAULT_DB_PATH, get_recent_runs  # noqa: E402

REPORTS_DIR = ROOT / "reports"
OUTPUT_DIR = ROOT / "gh-pages-output"
OUTPUT_REPORTS = OUTPUT_DIR / "reports"

OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_REPORTS.mkdir(exist_ok=True)

GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "")
ACTIONS_WORKFLOW_URL = os.environ.get(
    "ACTIONS_WORKFLOW_URL",
    f"https://github.com/{GITHUB_REPO}/actions/workflows/audit.yml" if GITHUB_REPO else "#",
)
PAGES_BASE = f"https://{GITHUB_REPO.split('/')[0]}.github.io/{GITHUB_REPO.split('/')[-1]}" if GITHUB_REPO else ""


# ── Copiar relatórios HTML gerados neste run ──────────────────────────────────

copied = 0
for html_file in REPORTS_DIR.glob("*.html"):
    dest = OUTPUT_REPORTS / html_file.name
    shutil.copy2(html_file, dest)
    copied += 1

# Copiar screenshots (caso existam e não estejam embeddados)
screenshots_src = REPORTS_DIR / "screenshots"
if screenshots_src.exists():
    screenshots_dst = OUTPUT_REPORTS / "screenshots"
    shutil.copytree(screenshots_src, screenshots_dst, dirs_exist_ok=True)


# ── Carregar histórico completo do SQLite ─────────────────────────────────────

db_path = ROOT / "auditor-history.db"
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
        "run_id": r.get("run_id", ""),
        "started_at": r.get("started_at", ""),
        "status": r.get("status", ""),
        "resultado": r.get("resultado") or "",
        "total_checks": r.get("total_checks") or 0,
        "total_passou": r.get("total_passou") or 0,
        "total_falhou": r.get("total_falhou") or 0,
        "total_erro": r.get("total_erro") or 0,
        "report_url": _report_url(r.get("started_at")),
    }
    for r in runs_raw
]

(OUTPUT_DIR / "reports.json").write_text(
    json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8"
)


# ── Gerar index.html ──────────────────────────────────────────────────────────

last = runs[0] if runs else None

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


def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso).astimezone()
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso[:16].replace("T", " ")


def _rows_html() -> str:
    if not runs:
        return '<tr><td colspan="6" class="empty">Nenhuma auditoria registrada ainda.</td></tr>'
    rows = []
    for r in runs:
        date = _fmt_date(r["started_at"]) if r["started_at"] else "—"
        badge = _status_badge(r["status"], r["resultado"])
        tc = r["total_checks"] or "—"
        tp = r["total_passou"]
        tf = r["total_falhou"]
        te = r["total_erro"]
        rate = f"{round(tp / r['total_checks'] * 100)}%" if r["total_checks"] else "—"

        if r["report_url"]:
            link = f'<a class="report-link" href="{r["report_url"]}" target="_blank">Ver relatório →</a>'
        else:
            link = '<span class="muted">relatório não disponível</span>'

        rows.append(f"""
        <tr>
          <td>{date}</td>
          <td>{badge}</td>
          <td class="num">{tc}</td>
          <td class="num ok">{tp}</td>
          <td class="num fail">{tf}</td>
          <td class="num err">{te}</td>
          <td class="num">{rate}</td>
          <td>{link}</td>
        </tr>""")
    return "\n".join(rows)


def _last_run_card() -> str:
    if not last:
        return '<div class="hero-card gray"><p>Nenhuma auditoria registrada ainda.</p></div>'

    date = _fmt_date(last["started_at"]) if last["started_at"] else "—"
    s = last["status"]
    r = last["resultado"]

    if s == "concluida" and r == "tudo_ok":
        cls, icon, title = "ok", "✓", "Tudo OK"
    elif s == "concluida" and r == "com_falhas":
        cls, icon, title = "fail", "✗", f'{last["total_falhou"]} falha(s) detectada(s)'
    elif s == "falhou":
        cls, icon, title = "err", "⚠", "Auditor com erro"
    else:
        cls, icon, title = "gray", "·", s

    tc = last["total_checks"] or 0
    tp = last["total_passou"]
    tf = last["total_falhou"]
    te = last["total_erro"]
    rate = f"{round(tp / tc * 100)}%" if tc else "—"

    report_btn = ""
    if last["report_url"]:
        report_btn = f'<a class="btn btn-outline" href="{last["report_url"]}" target="_blank">Ver relatório completo</a>'

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
      --pri: #4f46e5; --ok: #10b981; --fail: #ef4444; --err: #f59e0b;
      --bg: #f5f6fa; --card: #fff; --border: #e5e7eb;
      --text: #111827; --muted: #6b7280; --radius: 10px;
    }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 14px; background: var(--bg); color: var(--text); min-height: 100vh; }}

    .header {{ background: #fff; border-bottom: 1px solid var(--border);
               padding: 0 32px; height: 54px; display: flex; align-items: center;
               justify-content: space-between; position: sticky; top: 0; z-index: 10; }}
    .logo {{ font-weight: 700; font-size: 15px; color: var(--pri); }}
    .header-meta {{ font-size: 12px; color: var(--muted); }}

    .main {{ max-width: 1000px; margin: 0 auto; padding: 28px 24px; }}

    /* Hero card */
    .hero-card {{ display: flex; align-items: center; gap: 20px; padding: 22px 24px;
                  border-radius: var(--radius); border: 1px solid var(--border);
                  margin-bottom: 20px; background: var(--card); border-left: 5px solid; }}
    .hero-card.ok   {{ border-left-color: var(--ok); }}
    .hero-card.fail {{ border-left-color: var(--fail); }}
    .hero-card.err  {{ border-left-color: var(--err); }}
    .hero-card.gray {{ border-left-color: var(--border); }}
    .hero-icon {{ font-size: 36px; flex-shrink: 0; width: 48px; text-align: center; }}
    .hero-card.ok   .hero-icon {{ color: var(--ok); }}
    .hero-card.fail .hero-icon {{ color: var(--fail); }}
    .hero-card.err  .hero-icon {{ color: var(--err); }}
    .hero-info {{ flex: 1; }}
    .hero-title {{ font-size: 18px; font-weight: 700; margin-bottom: 4px; }}
    .hero-date  {{ font-size: 12px; color: var(--muted); margin-bottom: 10px; }}
    .hero-stats {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .stat-pill  {{ padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
    .stat-pill.ok   {{ background: #d1fae5; color: #065f46; }}
    .stat-pill.fail {{ background: #fee2e2; color: #991b1b; }}
    .stat-pill.err  {{ background: #fef3c7; color: #92400e; }}
    .stat-pill.gray {{ background: #f3f4f6; color: var(--muted); }}

    /* Buttons */
    .btn {{ display: inline-flex; align-items: center; gap: 6px; padding: 9px 18px;
            border-radius: 8px; border: none; cursor: pointer; font-size: 14px;
            font-weight: 600; text-decoration: none; transition: opacity .15s; }}
    .btn:hover {{ opacity: .85; }}
    .btn-primary {{ background: var(--pri); color: #fff; }}
    .btn-outline {{ background: #fff; color: var(--pri); border: 1.5px solid var(--pri); }}

    .actions-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }}
    .actions-hint {{ font-size: 12px; color: var(--muted); }}

    /* Table */
    .card {{ background: var(--card); border: 1px solid var(--border);
             border-radius: var(--radius); overflow: hidden; margin-bottom: 16px; }}
    .card-header {{ padding: 14px 18px; border-bottom: 1px solid var(--border);
                    font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ text-align: left; padding: 9px 14px; background: #f9fafb;
          border-bottom: 1px solid var(--border); font-size: 11px; font-weight: 600;
          color: var(--muted); text-transform: uppercase; letter-spacing: .4px; white-space: nowrap; }}
    td {{ padding: 10px 14px; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: #fafafa; }}
    .num {{ font-family: monospace; text-align: right; font-size: 13px; }}
    .num.ok   {{ color: var(--ok); font-weight: 600; }}
    .num.fail {{ color: var(--fail); font-weight: 600; }}
    .num.err  {{ color: var(--err); font-weight: 600; }}

    .badge {{ display: inline-block; padding: 3px 9px; border-radius: 5px; font-size: 11px; font-weight: 700; }}
    .b-ok   {{ background: #d1fae5; color: #065f46; }}
    .b-fail {{ background: #fee2e2; color: #991b1b; }}
    .b-err  {{ background: #fef3c7; color: #92400e; }}
    .b-run  {{ background: #ede9fe; color: #4f46e5; }}
    .b-gray {{ background: #f3f4f6; color: var(--muted); }}

    .report-link {{ color: var(--pri); text-decoration: none; font-weight: 500; }}
    .report-link:hover {{ text-decoration: underline; }}
    .muted {{ color: var(--muted); }}
    .empty {{ text-align: center; padding: 28px; color: var(--muted); }}

    .footer {{ margin-top: 40px; text-align: center; font-size: 11px; color: #9ca3af; }}

    /* Running indicator */
    #running-banner {{ display: none; background: #ede9fe; color: #4f46e5; padding: 10px 24px;
                       font-size: 13px; font-weight: 500; text-align: center; }}
    .spinner {{ display: inline-block; width: 12px; height: 12px; border: 2px solid rgba(79,70,229,.3);
                border-top-color: var(--pri); border-radius: 50%;
                animation: spin .7s linear infinite; vertical-align: middle; margin-right: 6px; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  </style>
</head>
<body>
  <div id="running-banner">
    <span class="spinner"></span> Auditoria em andamento no GitHub Actions — a página atualiza ao concluir
  </div>

  <header class="header">
    <span class="logo">⚡ Auditor Minimal Club</span>
    <span class="header-meta">Atualizado em {generated_at}</span>
  </header>

  <div class="main">

    {_last_run_card()}

    <div class="actions-row">
      <a class="btn btn-primary" href="{ACTIONS_WORKFLOW_URL}" target="_blank">
        ▶ Rodar Auditoria Agora
      </a>
      <span class="actions-hint">
        Abre o GitHub Actions → clique em <strong>Run workflow</strong>.
        Você pode filtrar por URL ou incluir fluxos manuais antes de rodar.
      </span>
    </div>

    <div class="card">
      <div class="card-header">
        Histórico de auditorias
        <span style="font-weight:400;color:var(--muted);font-size:12px;margin-left:auto">
          {len(runs)} execuções registradas
        </span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Data</th>
            <th>Resultado</th>
            <th style="text-align:right">Total</th>
            <th style="text-align:right">OK</th>
            <th style="text-align:right">Falhas</th>
            <th style="text-align:right">Erros</th>
            <th style="text-align:right">Taxa</th>
            <th>Relatório</th>
          </tr>
        </thead>
        <tbody>
          {_rows_html()}
        </tbody>
      </table>
    </div>

  </div>

  <div class="footer">
    Auditor Técnico Minimal Club &nbsp;·&nbsp;
    <a href="{ACTIONS_WORKFLOW_URL}" target="_blank" style="color:inherit">GitHub Actions</a>
  </div>

  <script>
    // Detecta se há workflow rodando consultando a API pública do GitHub
    (function() {{
      var repo = "{GITHUB_REPO}";
      if (!repo) return;
      var api = "https://api.github.com/repos/" + repo + "/actions/workflows/audit.yml/runs?per_page=1&status=in_progress";
      fetch(api, {{ headers: {{ Accept: "application/vnd.github+json" }} }})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          if (d.total_count && d.total_count > 0) {{
            document.getElementById("running-banner").style.display = "block";
            // Recarregar a página a cada 60s enquanto o workflow estiver rodando
            setTimeout(function() {{ location.reload(); }}, 60000);
          }}
        }})
        .catch(function() {{ /* API indisponível ou repo privado — ignorar */ }});
    }})();
  </script>
</body>
</html>"""

(OUTPUT_DIR / "index.html").write_text(HTML, encoding="utf-8")

print(f"GitHub Pages gerado:")
print(f"  {len(runs)} runs no índice")
print(f"  {copied} relatório(s) HTML copiado(s)")
print(f"  Output: {OUTPUT_DIR}")
if PAGES_BASE:
    print(f"  URL: {PAGES_BASE}")
