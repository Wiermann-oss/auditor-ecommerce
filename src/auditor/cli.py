"""
Interface de linha de comando — zero lógica de negócio.
Apenas parse de argumentos, chamada ao engine, e formatação de saída.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import typer

from .config.loader import DEFAULT_CONFIG_PATH, ConfigError, load_config
from .engine import DEFAULT_REPORTS_DIR, run_audit
from .storage.history import DEFAULT_DB_PATH, get_diff, get_recent_runs
from .types import AuditRun, AuditStatus, TriggerMode

app = typer.Typer(
    name="auditor",
    help="Auditor técnico automatizado da loja Minimal Club",
    add_completion=False,
)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


@app.command()
def run(
    config_path: Path = typer.Option(
        DEFAULT_CONFIG_PATH, "--config", "-c", help="Caminho do audit-config.yaml"
    ),
    db_path: Path = typer.Option(
        DEFAULT_DB_PATH, "--db", help="Banco SQLite de histórico"
    ),
    reports_dir: Path = typer.Option(
        DEFAULT_REPORTS_DIR, "--reports-dir", help="Diretório de relatórios"
    ),
    manual_only: bool = typer.Option(
        False, "--manual-only", help="Incluir fluxos marcados como manual_only"
    ),
    scheduled: bool = typer.Option(
        False, "--scheduled", help="Marcar execução como agendada (cron/CI)"
    ),
    url_filter: str = typer.Option(
        "", "--url-filter", "-f",
        help="Auditar apenas páginas cuja URL contenha este texto (ex: colecoes)"
    ),
) -> None:
    """Executa uma auditoria completa da loja."""
    _setup_logging()

    try:
        config, config_version = load_config(config_path)
    except ConfigError as exc:
        typer.echo(f"Erro no config: {exc}", err=True)
        raise typer.Exit(1)

    if url_filter:
        for page in config.critical_pages:
            if url_filter not in page.url:
                page.active = False
        typer.echo(f"Filtro aplicado: auditando apenas páginas com '{url_filter}' na URL")

    trigger = TriggerMode.AGENDADO if scheduled else TriggerMode.MANUAL

    audit_run = asyncio.run(
        run_audit(
            config=config,
            config_version=config_version,
            trigger=trigger,
            include_manual_only=manual_only,
            db_path=db_path,
            reports_dir=reports_dir,
        )
    )

    typer.echo("")
    _print_summary(audit_run, reports_dir)

    exit_code = 1 if audit_run.total_falhou > 0 or audit_run.status.value == "falhou" else 0
    raise typer.Exit(exit_code)


@app.command()
def diff(
    since: int = typer.Option(7, "--since", "-s", help="Comparar com últimos N dias"),
    db_path: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Banco SQLite de histórico"),
) -> None:
    """Compara a última auditoria com execuções anteriores no período."""
    result = get_diff(since_days=since, db_path=db_path)

    if "error" in result:
        typer.echo(f"⚠  {result['error']}", err=True)
        raise typer.Exit(1)

    regressoes = result["regressoes"]
    recuperacoes = result["recuperacoes"]
    novidades = result["novidades"]

    typer.echo(
        f"\nDiff — últimos {since} dia(s)  "
        f"({result['runs_analisados']} execuções analisadas)"
    )
    typer.echo(f"Run atual: {result['run_atual']}\n")

    if not regressoes and not recuperacoes and not novidades:
        typer.echo("✓  Nenhuma mudança de estado nas checagens.")
        return

    if regressoes:
        typer.echo(f"✗  {len(regressoes)} REGRESSÃO(ÕES)  (passou → falhou):")
        for r in regressoes:
            typer.echo(f"   • {r['check_id']:30s}  {r['page_url'] or r['flow_name'] or '—':40s}  {r['viewport']}")

    if recuperacoes:
        typer.echo(f"\n✓  {len(recuperacoes)} RECUPERAÇÃO(ÕES)  (falhou → passou):")
        for r in recuperacoes:
            typer.echo(f"   • {r['check_id']:30s}  {r['page_url'] or r['flow_name'] or '—':40s}  {r['viewport']}")

    if novidades:
        typer.echo(f"\n+  {len(novidades)} checagem(ns) nova(s):")
        for r in novidades:
            typer.echo(f"   • {r['check_id']:30s}  {r['page_url'] or r['flow_name'] or '—':40s}  {r['viewport']}")

    if regressoes:
        raise typer.Exit(1)


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Número de execuções a listar"),
    db_path: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="Banco SQLite de histórico"),
) -> None:
    """Lista as últimas execuções de auditoria."""
    runs = get_recent_runs(limit=limit, db_path=db_path)

    if not runs:
        typer.echo("Nenhuma execução encontrada no histórico.")
        return

    header = f"{'Data':<20}  {'Status':<14}  {'Resultado':<14}  {'Ok':>4}  {'Fail':>4}  {'Erro':>4}  run_id"
    typer.echo("\n" + header)
    typer.echo("-" * len(header))
    for r in runs:
        date = (r.get("started_at") or "")[:19].replace("T", " ")
        run_id_short = (r.get("run_id") or "")[:8] + "…"
        typer.echo(
            f"{date:<20}  {r.get('status') or '':<14}  {r.get('resultado') or '':<14}  "
            f"{r.get('total_passou') or 0:>4}  {r.get('total_falhou') or 0:>4}  "
            f"{r.get('total_erro') or 0:>4}  {run_id_short}"
        )


@app.command()
def server(
    host: str = typer.Option("127.0.0.1", "--host", help="Host do servidor"),
    port: int = typer.Option(8000, "--port", "-p", help="Porta"),
    no_open: bool = typer.Option(False, "--no-open", help="Não abrir o navegador automaticamente"),
) -> None:
    """Inicia o servidor web do dashboard de auditoria."""
    import threading
    import webbrowser

    import uvicorn

    url = f"http://{host}:{port}"

    if not no_open:
        def _open() -> None:
            import time
            time.sleep(1.8)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    typer.echo(f"Dashboard: {url}  (Ctrl+C para parar)")
    uvicorn.run(
        "auditor.server:app",
        host=host,
        port=port,
        log_level="warning",
    )


def _print_summary(run: AuditRun, reports_dir: Path) -> None:
    if run.status == AuditStatus.FALHOU:
        typer.echo("✗  AUDITOR FALHOU — ver log acima")
    elif run.total_falhou > 0:
        typer.echo(f"✗  {run.total_falhou} FALHA(S) DETECTADA(S) NA LOJA")
    else:
        typer.echo("✓  TUDO OK")

    typer.echo(
        f"   {run.total_passou} passaram  ·  "
        f"{run.total_falhou} falharam  ·  "
        f"{run.total_erro} com erro  ·  "
        f"{run.total_checks} total"
    )

    html_files = sorted(reports_dir.glob("*.html")) if reports_dir.exists() else []
    if html_files:
        typer.echo(f"   Relatório: {html_files[-1]}")
