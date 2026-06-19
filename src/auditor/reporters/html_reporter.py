"""
Gera relatório HTML self-contained via Jinja2.
Zero dependências externas — CSS inline, sem CDN, sem JS.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment

from ..reporters.explanations import explain_expected
from ..types import AuditRun, AuditStatus, CheckResult, CheckStatus


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Auditoria — {{ store_name }}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           font-size: 14px; color: #1a1a1a; background: #f0f0f0; padding: 24px; }
    h2 { font-size: 15px; font-weight: 600; margin: 32px 0 12px; }
    .header { margin-bottom: 20px; }
    .header h1 { font-size: 20px; font-weight: 700; }
    .meta { color: #666; font-size: 12px; margin-top: 4px; }

    .banner { padding: 14px 18px; border-radius: 8px; margin-bottom: 20px;
              font-size: 15px; font-weight: 600; border-left: 4px solid; }
    .banner-ok   { background: #d1fae5; color: #065f46; border-color: #10b981; }
    .banner-fail { background: #fee2e2; color: #991b1b; border-color: #ef4444; }
    .banner-err  { background: #fef3c7; color: #92400e; border-color: #f59e0b; }

    .stats { display: flex; gap: 12px; margin-bottom: 28px; flex-wrap: wrap; }
    .stat { background: #fff; border-radius: 8px; padding: 14px 20px; text-align: center;
            min-width: 90px; }
    .stat .num { font-size: 28px; font-weight: 700; }
    .stat .lbl { font-size: 11px; color: #777; text-transform: uppercase; margin-top: 2px; }
    .num-ok   { color: #10b981; }
    .num-fail { color: #ef4444; }
    .num-err  { color: #f59e0b; }

    table { width: 100%; border-collapse: collapse; background: #fff;
            border-radius: 8px; overflow: hidden; font-size: 13px; margin-bottom: 8px; }
    th { background: #f4f4f4; padding: 9px 12px; text-align: left;
         font-weight: 600; border-bottom: 1px solid #e5e5e5; white-space: nowrap; }
    td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #fafafa; }

    .badge { display: inline-block; padding: 2px 7px; border-radius: 4px;
             font-size: 11px; font-weight: 600; white-space: nowrap; }
    .badge-passou { background: #d1fae5; color: #065f46; }
    .badge-falhou { background: #fee2e2; color: #991b1b; }
    .badge-erro   { background: #fef3c7; color: #92400e; }

    .vp { display: inline-block; font-size: 10px; background: #e5e7eb; color: #555;
          padding: 2px 6px; border-radius: 3px; white-space: nowrap; }
    .detail-fail { color: #b91c1c; font-size: 12px; }
    .detail-err  { color: #b45309; font-size: 12px; }
    .val { font-family: monospace; font-size: 12px; }
    .scope { max-width: 260px; overflow: hidden; text-overflow: ellipsis;
             white-space: nowrap; color: #444; }
    .footer { margin-top: 32px; color: #aaa; font-size: 11px; }

    /* ── Failure cards ── */
    .failure-card {
      background: #fff; border-radius: 10px; border: 1px solid #e5e7eb;
      border-left: 4px solid #ef4444; margin-bottom: 20px; overflow: hidden;
    }
    .failure-card.is-erro { border-left-color: #f59e0b; }
    .failure-card-head {
      display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
      padding: 14px 18px; border-bottom: 1px solid #f3f4f6;
    }
    .failure-card-head strong { font-size: 14px; flex: 1; }
    .failure-card-body { padding: 18px; display: flex; flex-direction: column; gap: 16px; }
    .scope-line { font-size: 12px; color: #6b7280; font-family: monospace; }

    .info-blocks { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
    @media (max-width: 700px) { .info-blocks { grid-template-columns: 1fr; } }

    .info-block { border-radius: 8px; padding: 12px 14px; }
    .info-block label { display: block; font-size: 10px; text-transform: uppercase;
                        letter-spacing: .5px; font-weight: 700; margin-bottom: 6px; }
    .info-block p { font-size: 13px; line-height: 1.6; }

    .block-detail { background: #fef2f2; border: 1px solid #fecaca; }
    .block-detail label { color: #dc2626; }
    .block-detail p { color: #7f1d1d; font-family: monospace; font-size: 12px; word-break: break-word; }
    .block-detail.is-erro { background: #fffbeb; border-color: #fde68a; }
    .block-detail.is-erro label { color: #d97706; }
    .block-detail.is-erro p { color: #78350f; }

    .block-expected { background: #f0fdf4; border: 1px solid #bbf7d0; }
    .block-expected label { color: #15803d; }
    .block-expected p { color: #14532d; }

    .block-impact { background: #f8fafc; border: 1px solid #e2e8f0; }
    .block-impact label { color: #475569; }
    .block-impact p { color: #334155; }

    .failure-screenshot {
      border-top: 1px solid #f3f4f6; padding-top: 16px;
    }
    .failure-screenshot-label {
      font-size: 10px; text-transform: uppercase; letter-spacing: .5px;
      font-weight: 700; color: #9ca3af; margin-bottom: 8px;
    }
    .screenshot-wrap {
      position: relative; cursor: zoom-in; border-radius: 8px; overflow: hidden;
      border: 1px solid #e5e7eb; box-shadow: 0 2px 12px rgba(0,0,0,.08);
      max-width: 720px;
    }
    .screenshot-wrap img {
      display: block; width: 100%; height: 260px;
      object-fit: cover; object-position: top;
      transition: height .25s ease;
    }
    .screenshot-wrap.expanded img { height: auto; cursor: zoom-out; }
    .screenshot-overlay {
      position: absolute; bottom: 0; left: 0; right: 0; height: 56px;
      background: linear-gradient(transparent, rgba(0,0,0,.45));
      display: flex; align-items: flex-end; padding: 10px 14px;
      pointer-events: none; transition: opacity .2s;
    }
    .screenshot-wrap.expanded .screenshot-overlay { display: none; }
    .screenshot-hint {
      font-size: 11px; color: rgba(255,255,255,.9); font-weight: 600;
      letter-spacing: .3px;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>Auditoria Técnica — {{ store_name }}</h1>
    <div class="meta">
      {{ started_at }} &nbsp;·&nbsp; trigger: {{ trigger }}
      &nbsp;·&nbsp; config: {{ config_version }}
      {% if duration %}&nbsp;·&nbsp; duração: {{ duration }}{% endif %}
    </div>
  </div>

  <div class="banner {{ banner_class }}">{{ banner_text }}</div>

  <div class="stats">
    <div class="stat">
      <div class="num">{{ total_checks }}</div>
      <div class="lbl">checagens</div>
    </div>
    <div class="stat">
      <div class="num num-ok">{{ total_passou }}</div>
      <div class="lbl">passaram</div>
    </div>
    <div class="stat">
      <div class="num num-fail">{{ total_falhou }}</div>
      <div class="lbl">falharam</div>
    </div>
    <div class="stat">
      <div class="num num-err">{{ total_erro }}</div>
      <div class="lbl">com erro</div>
    </div>
  </div>

  {% if failures %}
  <h2>Falhas e erros detectados</h2>
  {% for r in failures %}
  <div class="failure-card{% if r.status == 'erro' %} is-erro{% endif %}">
    <div class="failure-card-head">
      <span class="badge badge-{{ r.status }}">{{ r.status }}</span>
      <strong>{{ r.check_name }}</strong>
      <span class="vp">{{ r.viewport }}</span>
      {% if r.value_display %}<span class="val">{{ r.value_display }}</span>{% endif %}
    </div>
    <div class="failure-card-body">
      <div class="scope-line">{{ r.full_scope }}</div>

      <div class="info-blocks">
        {% if r.detail %}
        <div class="info-block block-detail{% if r.status == 'erro' %} is-erro{% endif %}">
          <label>O que aconteceu</label>
          <p>{{ r.detail }}</p>
        </div>
        {% endif %}

        {% if r.expected %}
        <div class="info-block block-expected">
          <label>O que era esperado</label>
          <p>{{ r.expected }}</p>
        </div>
        {% endif %}

        {% if r.explanation %}
        <div class="info-block block-impact">
          <label>Impacto no negócio</label>
          <p>{{ r.explanation }}</p>
        </div>
        {% endif %}
      </div>

      {% if r.screenshot_b64 %}
      <div class="failure-screenshot">
        <div class="failure-screenshot-label">Estado da página no momento da falha</div>
        <div class="screenshot-wrap" onclick="this.classList.toggle('expanded')">
          <img src="data:image/png;base64,{{ r.screenshot_b64 }}"
               alt="Screenshot da página no momento da falha — {{ r.check_name }}">
          <div class="screenshot-overlay">
            <span class="screenshot-hint">🔍 Clique para ampliar</span>
          </div>
        </div>
      </div>
      {% endif %}
    </div>
  </div>
  {% endfor %}
  {% endif %}

  <h2>Todos os resultados</h2>
  <table>
    <thead>
      <tr>
        <th>Página / Fluxo</th>
        <th>Checagem</th>
        <th>Viewport</th>
        <th>Status</th>
        <th>Valor → Limiar</th>
        <th>Detalhe</th>
      </tr>
    </thead>
    <tbody>
      {% for r in all_results %}
      <tr>
        <td class="scope" title="{{ r.full_scope }}">{{ r.scope }}</td>
        <td>{{ r.check_name }}</td>
        <td><span class="vp">{{ r.viewport }}</span></td>
        <td><span class="badge badge-{{ r.status }}">{{ r.status }}</span></td>
        <td class="val">{{ r.value_display }}</td>
        <td>{{ r.detail or "" }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <div class="footer">
    run_id: {{ run_id }} &nbsp;·&nbsp; gerado em {{ generated_at }}
  </div>
</body>
</html>
"""


def generate_html_report(run: AuditRun, reports_dir: Path) -> Path:
    """Grava report HTML em reports_dir e retorna o caminho do arquivo."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = run.started_at.strftime("%Y-%m-%dT%H-%M-%S") + ".html"
    path = reports_dir / filename

    env = Environment(autoescape=True)
    template = env.from_string(_HTML_TEMPLATE)

    failures = [r for r in run.check_results if r.status != CheckStatus.PASSOU]

    html = template.render(
        store_name="Minimal Club",
        run_id=run.run_id,
        started_at=run.started_at.strftime("%d/%m/%Y %H:%M:%S"),
        trigger=run.trigger.value,
        config_version=run.config_version,
        duration=_format_duration(run),
        banner_class=_banner_class(run),
        banner_text=_banner_text(run),
        total_checks=run.total_checks,
        total_passou=run.total_passou,
        total_falhou=run.total_falhou,
        total_erro=run.total_erro,
        failures=[_format_result(r) for r in failures],
        all_results=[_format_result(r) for r in run.check_results],
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    path.write_text(html, encoding="utf-8")
    return path


def _banner_class(run: AuditRun) -> str:
    if run.status == AuditStatus.FALHOU:
        return "banner-err"
    if run.resultado is None or run.total_falhou > 0 or run.total_erro > 0:
        return "banner-fail"
    return "banner-ok"


def _banner_text(run: AuditRun) -> str:
    if run.status == AuditStatus.FALHOU:
        return f"Auditor falhou — {run.execution_error or 'ver logs'}"
    if run.total_falhou > 0:
        n = run.total_falhou
        return f"{'1 falha detectada' if n == 1 else f'{n} falhas detectadas'} na loja"
    if run.total_erro > 0:
        n = run.total_erro
        return f"{'1 checagem com erro' if n == 1 else f'{n} checagens com erro'} (auditor/config)"
    return "Tudo OK — nenhuma falha técnica detectada"


def _format_duration(run: AuditRun) -> Optional[str]:
    if run.finished_at is None:
        return None
    delta = run.finished_at - run.started_at
    total_s = int(delta.total_seconds())
    if total_s < 60:
        return f"{total_s}s"
    return f"{total_s // 60}m {total_s % 60}s"


def _format_result(r: CheckResult) -> dict:
    full_scope = r.page_url or r.flow_name or ""
    scope = _shorten_scope(full_scope)

    if r.value is not None and r.unit:
        val_str = _format_value(r.value, r.unit)
        if r.threshold is not None:
            val_str += f" → {_format_value(r.threshold, r.unit)}"
    else:
        val_str = ""

    return {
        "scope": scope,
        "full_scope": full_scope,
        "check_name": r.check_name,
        "viewport": r.viewport.value,
        "status": r.status.value,
        "value_display": val_str,
        "detail": r.detail or "",
        "expected": explain_expected(r.check_id, r.check_name, r.value, r.threshold, r.unit),
        "explanation": r.explanation or "",
        "screenshot_b64": r.screenshot_b64 or "",
    }


def _shorten_scope(scope: str) -> str:
    if len(scope) <= 50:
        return scope
    # Para URLs, mostrar só o path
    if "://" in scope:
        try:
            path = scope.split("://", 1)[1].split("/", 1)[1] if "/" in scope.split("://", 1)[1] else "/"
            short = "/" + path
            return short if len(short) <= 50 else short[:47] + "..."
        except Exception:
            pass
    return scope[:47] + "..."


def _format_value(value: float, unit: str) -> str:
    if unit == "ms":
        return f"{value:.0f}ms"
    if unit == "score":
        return f"{value:.3f}"
    if unit == "count":
        return f"{value:.0f}"
    if unit == "status_code":
        return f"{value:.0f}"
    return f"{value:.2f} {unit}"
