"""
Verificação dos popups da loja (Klaviyo e outros).
Sempre roda em contexto fresh (sem cookies) — simula visitante novo, que vê o Lead popup.
Modo agendado: verifica mecânica até ANTES do submit (não cria lead no Klaviyo).
Modo manual com contato designado: submit real — pendente alinhamento com Daniel/CRM.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeoutError

from ..config.models import AuditConfig, PopupConfig
from ..reporters.explanations import explain_failure
from ..types import Categoria, CheckResult, CheckStatus, Viewport
from ._screenshot import capture_failure_screenshot

_VIEWPORT_DIMS = {
    Viewport.DESKTOP: {"width": 1280, "height": 800},
    Viewport.MOBILE: {"width": 390, "height": 844},
}

_USER_AGENTS = {
    Viewport.DESKTOP: (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    Viewport.MOBILE: (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
}


async def check_popup(
    browser: Browser,
    popup: PopupConfig,
    config: AuditConfig,
    viewport: Viewport,
    screenshots_dir: Optional[Path] = None,
) -> list[CheckResult]:
    """
    Executa todas as checagens definidas para um popup num viewport.
    Contexto fresh (sem cookies) garante que o Lead popup aparece.
    """
    trigger_url = config.absolute_url(popup.trigger_page)
    results: list[CheckResult] = []

    context = await browser.new_context(
        viewport=_VIEWPORT_DIMS[viewport],
        user_agent=_USER_AGENTS[viewport],
    )
    page = await context.new_page()

    try:
        await page.goto(trigger_url, timeout=config.timeouts.navigation, wait_until="load")

        # Aguardar o delay do popup (Klaviyo dispara ~3s após load; popup_delay = 4.5s)
        await page.wait_for_timeout(config.timeouts.popup_delay)

        # 1. Popup dispara após o delay
        appeared = await _check_appears(page, popup, trigger_url, viewport)
        await _maybe_enrich(appeared, page, screenshots_dir, "popup_dispara", viewport)
        results.append(appeared)

        if appeared.status != CheckStatus.PASSOU:
            results.extend(
                _skip_remaining(
                    popup, trigger_url, viewport,
                    reason=f"Popup não apareceu após {config.timeouts.popup_delay}ms — "
                           "verificar gatilho e selector no config"
                )
            )
            return results

        # 2. Botão de fechar sempre visível
        close_vis = await _check_close_visible(page, popup, trigger_url, viewport)
        await _maybe_enrich(close_vis, page, screenshots_dir, "popup_botao_fechar", viewport)
        results.append(close_vis)

        # 3. Fechar funciona
        close_result = await _check_close_works(page, popup, trigger_url, viewport)
        await _maybe_enrich(close_result, page, screenshots_dir, "popup_fechar_funciona", viewport)
        results.append(close_result)

        if close_result.status != CheckStatus.PASSOU:
            results.extend(
                _skip_remaining(
                    popup, trigger_url, viewport,
                    reason="Botão de fechar não funcionou — checagens de bloqueio ignoradas",
                    skip_ids={"popup_scroll_block", "popup_click_block", "popup_loop"},
                )
            )
            return results

        # 4. Não bloqueia scroll após fechar
        scroll_result = await _check_no_scroll_block(page, trigger_url, viewport, popup.name)
        await _maybe_enrich(scroll_result, page, screenshots_dir, "popup_scroll_block", viewport)
        results.append(scroll_result)

        # 5. Não bloqueia clique após fechar
        click_result = await _check_no_click_block(page, trigger_url, viewport, popup.name)
        await _maybe_enrich(click_result, page, screenshots_dir, "popup_click_block", viewport)
        results.append(click_result)

        # 6. Não dispara em loop
        loop_result = await _check_no_loop(page, popup, trigger_url, viewport, config)
        await _maybe_enrich(loop_result, page, screenshots_dir, "popup_loop", viewport)
        results.append(loop_result)

    except Exception as exc:
        results.append(
            CheckResult(
                check_id=f"popup_{popup.name.lower().replace(' ', '_')}_error",
                check_name=f"Popup '{popup.name}' — erro de runtime",
                categoria=Categoria.FLUXO,
                viewport=viewport,
                status=CheckStatus.ERRO,
                page_url=trigger_url,
                detail=f"Exceção inesperada ao verificar popup: {type(exc).__name__}: {exc}",
            )
        )
    finally:
        await context.close()

    return results


# — Checagens individuais —

async def _check_appears(
    page: Page,
    popup: PopupConfig,
    url: str,
    viewport: Viewport,
) -> CheckResult:
    start = time.monotonic()
    try:
        await page.locator(popup.container_selector).first.wait_for(
            state="visible", timeout=3000
        )
        return CheckResult(
            check_id="popup_dispara",
            check_name=f"Popup '{popup.name}' — dispara após delay",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.PASSOU,
            page_url=url,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except PlaywrightTimeoutError:
        return CheckResult(
            check_id="popup_dispara",
            check_name=f"Popup '{popup.name}' — dispara após delay",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.FALHOU,
            page_url=url,
            detail=f"Popup não visível após delay — seletor: '{popup.container_selector}'",
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _check_close_visible(
    page: Page,
    popup: PopupConfig,
    url: str,
    viewport: Viewport,
) -> CheckResult:
    start = time.monotonic()
    try:
        await page.locator(popup.close_selector).first.wait_for(
            state="visible", timeout=3000
        )
        return CheckResult(
            check_id="popup_botao_fechar",
            check_name=f"Popup '{popup.name}' — botão de fechar visível",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.PASSOU,
            page_url=url,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except PlaywrightTimeoutError:
        return CheckResult(
            check_id="popup_botao_fechar",
            check_name=f"Popup '{popup.name}' — botão de fechar visível",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.FALHOU,
            page_url=url,
            detail=(
                f"Botão de fechar não visível — seletor: '{popup.close_selector}'. "
                "CRÍTICO: esconder o close derruba a conversão (regra do playbook v2.4)"
            ),
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _check_close_works(
    page: Page,
    popup: PopupConfig,
    url: str,
    viewport: Viewport,
) -> CheckResult:
    start = time.monotonic()
    try:
        await page.locator(popup.close_selector).first.click(timeout=3000)
        # Aguardar o popup desaparecer
        await page.locator(popup.container_selector).first.wait_for(
            state="hidden", timeout=3000
        )
        return CheckResult(
            check_id="popup_fechar_funciona",
            check_name=f"Popup '{popup.name}' — fechar funciona",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.PASSOU,
            page_url=url,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except PlaywrightTimeoutError:
        return CheckResult(
            check_id="popup_fechar_funciona",
            check_name=f"Popup '{popup.name}' — fechar funciona",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.FALHOU,
            page_url=url,
            detail=(
                f"Popup não fechou após clicar em '{popup.close_selector}'. "
                "Usuário fica preso — bloqueio de compra crítico"
            ),
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _check_no_scroll_block(
    page: Page, url: str, viewport: Viewport, popup_name: str
) -> CheckResult:
    start = time.monotonic()
    try:
        before_y = await page.evaluate("window.scrollY")
        await page.evaluate("window.scrollTo(0, 400)")
        after_y = await page.evaluate("window.scrollY")

        # Em algumas páginas com conteúdo curto, o scroll pode não atingir 400px
        passed = after_y > before_y or after_y >= 300
        return CheckResult(
            check_id="popup_scroll_block",
            check_name=f"Popup '{popup_name}' — scroll não bloqueado após fechar",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.PASSOU if passed else CheckStatus.FALHOU,
            page_url=url,
            detail=(
                None if passed
                else f"Scroll bloqueado: scrollY={after_y}px após tentativa de scroll para 400px"
            ),
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:
        return CheckResult(
            check_id="popup_scroll_block",
            check_name=f"Popup '{popup_name}' — scroll não bloqueado após fechar",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.ERRO,
            page_url=url,
            detail=f"Erro ao verificar scroll: {exc}",
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _check_no_click_block(
    page: Page, url: str, viewport: Viewport, popup_name: str
) -> CheckResult:
    """
    Verifica que não há overlay invisível bloqueando cliques.
    Estratégia: tentar clicar no primeiro <a> da área principal da página.
    Usa no_wait_after=True para não aguardar navegação — apenas testa a interação.
    """
    start = time.monotonic()
    try:
        link = page.locator("main a, article a, section a, .product-item a").first
        count = await link.count()

        if count == 0:
            # Fallback: qualquer link que não seja popup
            link = page.locator(f"a:not([class*='klaviyo']):not([class*='popup'])").first
            count = await link.count()

        if count == 0:
            return CheckResult(
                check_id="popup_click_block",
                check_name=f"Popup '{popup_name}' — clique não bloqueado após fechar",
                categoria=Categoria.FLUXO,
                viewport=viewport,
                status=CheckStatus.ERRO,
                page_url=url,
                detail="Nenhum elemento de link encontrado para testar desbloqueio de clique",
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        await link.click(timeout=3000, no_wait_after=True)
        return CheckResult(
            check_id="popup_click_block",
            check_name=f"Popup '{popup_name}' — clique não bloqueado após fechar",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.PASSOU,
            page_url=url,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    except PlaywrightTimeoutError:
        return CheckResult(
            check_id="popup_click_block",
            check_name=f"Popup '{popup_name}' — clique não bloqueado após fechar",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.FALHOU,
            page_url=url,
            detail="Clique bloqueado após fechar o popup — possível overlay invisível na página",
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _check_no_loop(
    page: Page,
    popup: PopupConfig,
    url: str,
    viewport: Viewport,
    config: AuditConfig,
) -> CheckResult:
    """Popup não deve reaparecer na mesma sessão após fechar (regra: max 1x por 24h)."""
    start = time.monotonic()
    try:
        # Aguardar novamente o delay do popup
        await page.wait_for_timeout(config.timeouts.popup_delay)

        locator = page.locator(popup.container_selector)
        count = await locator.count()
        reappeared = count > 0 and await locator.first.is_visible()

        return CheckResult(
            check_id="popup_loop",
            check_name=f"Popup '{popup.name}' — não dispara em loop",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.FALHOU if reappeared else CheckStatus.PASSOU,
            page_url=url,
            detail=(
                f"Popup reapareceu na mesma sessão após fechar — viola regra de max 1x/24h"
                if reappeared else None
            ),
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:
        return CheckResult(
            check_id="popup_loop",
            check_name=f"Popup '{popup.name}' — não dispara em loop",
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.ERRO,
            page_url=url,
            detail=f"Erro ao verificar loop: {exc}",
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _maybe_enrich(
    result: CheckResult,
    page: Page,
    screenshots_dir: Optional[Path],
    check_id: str,
    viewport: Viewport,
) -> None:
    """Captura screenshot e adiciona explicação se o resultado for falha/erro."""
    if result.status == CheckStatus.PASSOU or not screenshots_dir:
        return
    path, b64 = await capture_failure_screenshot(page, screenshots_dir, f"{check_id}_{viewport.value}")
    if path:
        result.screenshot_path = path
    if b64:
        result.screenshot_b64 = b64
    if not result.explanation:
        result.explanation = explain_failure(check_id, result.check_name, result.detail)


def _skip_remaining(
    popup: PopupConfig,
    url: str,
    viewport: Viewport,
    reason: str,
    skip_ids: set[str] | None = None,
) -> list[CheckResult]:
    all_ids = {
        "popup_botao_fechar": f"Popup '{popup.name}' — botão de fechar visível",
        "popup_fechar_funciona": f"Popup '{popup.name}' — fechar funciona",
        "popup_scroll_block": f"Popup '{popup.name}' — scroll não bloqueado após fechar",
        "popup_click_block": f"Popup '{popup.name}' — clique não bloqueado após fechar",
        "popup_loop": f"Popup '{popup.name}' — não dispara em loop",
    }
    ids_to_skip = skip_ids or set(all_ids.keys())
    return [
        CheckResult(
            check_id=check_id,
            check_name=name,
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.ERRO,
            page_url=url,
            detail=f"Ignorado: {reason}",
        )
        for check_id, name in all_ids.items()
        if check_id in ids_to_skip
    ]
