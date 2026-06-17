"""
Orquestrador principal da auditoria.
Coordena config → layers → storage → reporters.
Sem lógica de checagem — só sequenciamento e tratamento de erros fatais.
"""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.async_api import Browser, async_playwright

from .config.models import AuditConfig
from .layers.layer_a import run_flow
from .layers.layer_b import run_page_health_checks
from .layers.popup_checker import check_popup
from .reporters.html_reporter import generate_html_report
from .reporters.json_reporter import generate_json_report
from .storage.history import DEFAULT_DB_PATH, init_db, save_run
from .types import AuditRun, TriggerMode, Viewport

log = logging.getLogger(__name__)

DEFAULT_REPORTS_DIR = Path("reports")


async def run_audit(
    config: AuditConfig,
    config_version: str,
    trigger: TriggerMode = TriggerMode.MANUAL,
    include_manual_only: bool = False,
    db_path: Path = DEFAULT_DB_PATH,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
) -> AuditRun:
    """
    Executa uma auditoria completa e persiste os resultados.
    Retorna o AuditRun finalizado (status = concluida ou falhou).
    """
    run = AuditRun(trigger=trigger, config_version=config_version)

    init_db(db_path)
    save_run(run, db_path)
    log.info("Auditoria iniciada — run_id: %s", run.run_id)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            await _run_page_health(browser, config, run)
            await _run_popup_checks(browser, config, run)
            await _run_flows(browser, config, run, include_manual_only)
            run.finalizar()
            log.info(
                "Auditoria concluída — %d passaram, %d falharam, %d com erro",
                run.total_passou, run.total_falhou, run.total_erro,
            )
        except Exception as exc:
            run.marcar_falha(f"{type(exc).__name__}: {exc}")
            log.error("Auditor falhou fatalmente: %s", exc)
        finally:
            await browser.close()

    save_run(run, db_path)

    if run.check_results:
        json_path = generate_json_report(run, reports_dir)
        html_path = generate_html_report(run, reports_dir)
        log.info("Relatórios gerados: %s | %s", json_path, html_path)

    return run


async def _run_page_health(browser: Browser, config: AuditConfig, run: AuditRun) -> None:
    pages = config.active_pages()
    if not pages:
        return
    log.info("Verificando saúde técnica das páginas (%d)...", len(pages))
    for page_cfg in pages:
        for viewport_cfg in page_cfg.viewports:
            viewport = Viewport(viewport_cfg.value)
            log.info("  → %s (%s)", page_cfg.name, viewport.value)
            results = await run_page_health_checks(browser, page_cfg, config, viewport)
            run.check_results.extend(results)
            _log_results_summary(results)


async def _run_popup_checks(browser: Browser, config: AuditConfig, run: AuditRun) -> None:
    popups = config.active_popups()
    if not popups:
        return
    log.info("Verificando popups (%d)...", len(popups))
    for popup in popups:
        for viewport_cfg in popup.viewports:
            viewport = Viewport(viewport_cfg.value)
            log.info("  → %s (%s)", popup.name, viewport.value)
            results = await check_popup(browser, popup, config, viewport)
            run.check_results.extend(results)
            _log_results_summary(results)


async def _run_flows(
    browser: Browser,
    config: AuditConfig,
    run: AuditRun,
    include_manual_only: bool,
) -> None:
    flows = config.active_flows(include_manual_only)
    if not flows:
        return
    log.info("Verificando fluxos funcionais (%d)...", len(flows))
    for flow in flows:
        for viewport_cfg in flow.viewports:
            viewport = Viewport(viewport_cfg.value)
            log.info("  → %s (%s)", flow.name, viewport.value)
            results = await run_flow(browser, flow, config, viewport)
            run.check_results.extend(results)
            _log_results_summary(results)


def _log_results_summary(results: list) -> None:
    total = len(results)
    falhas = sum(1 for r in results if r.status.value == "falhou")
    erros = sum(1 for r in results if r.status.value == "erro")
    mark = "✗" if falhas or erros else "✓"
    log.info("    %s %d checks — %d falha(s), %d erro(s)", mark, total, falhas, erros)
