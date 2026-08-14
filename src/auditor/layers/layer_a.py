"""
Camada de verificação funcional dos fluxos (ex-Camada A).
Executa os fluxos definidos no audit-config.yaml navegando com Playwright.
Cada step produz um CheckResult. Abort_on_failure interrompe o fluxo no primeiro FALHOU.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeoutError

from ..config.models import ActionType, AuditConfig, ExpectType, Flow, FlowStep, RunMode
from ..reporters.explanations import explain_failure
from ..types import Categoria, CheckResult, CheckStatus, Viewport
from ._screenshot import capture_failure_screenshot, dismiss_known_popups

_VIEWPORT_DIMS = {
    Viewport.DESKTOP: {"width": 1280, "height": 800},
    Viewport.MOBILE: {"width": 390, "height": 844},
}


def _visible(selector: str) -> str:
    """Filtra o seletor para considerar só elementos visíveis. Temas Shopify costumam
    renderizar um elemento por variante (ex: um bloco de preço por tamanho, só um
    visível por vez) — sem esse filtro, '.first' pode pegar uma cópia oculta e a
    checagem falha mesmo com o elemento certo visível na tela (visto em produção:
    F1 'PDP exibe preço', 2026-08-13)."""
    return f"{selector} >> visible=true"

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


async def run_flow(
    browser: Browser,
    flow: Flow,
    config: AuditConfig,
    viewport: Viewport,
    screenshots_dir: Optional[Path] = None,
) -> list[CheckResult]:
    """
    Executa um fluxo completo em contexto isolado (fresh browser context).
    Cada contexto começa sem cookies nem sessão — idêntico a um visitante novo.
    """
    results: list[CheckResult] = []
    abort_triggered = False
    abort_step_name = ""

    context = await browser.new_context(
        viewport=_VIEWPORT_DIMS[viewport],
        user_agent=_USER_AGENTS[viewport],
    )
    page = await context.new_page()
    page.set_default_timeout(config.timeouts.element)

    try:
        for i, step in enumerate(flow.steps):
            if abort_triggered:
                results.append(
                    CheckResult(
                        check_id=f"{flow.id}_step_{i}",
                        check_name=f"{flow.name} → {step.name}",
                        categoria=Categoria.FLUXO,
                        viewport=viewport,
                        status=CheckStatus.ERRO,
                        flow_name=flow.name,
                        detail=f"Passo ignorado — fluxo abortado em '{abort_step_name}' (abort_on_failure=true)",
                    )
                )
                continue

            result = await _execute_step(page, step, flow, config, viewport, i, screenshots_dir)
            results.append(result)

            if result.status == CheckStatus.FALHOU and flow.abort_on_failure:
                abort_triggered = True
                abort_step_name = step.name

    except Exception as exc:
        results.append(
            CheckResult(
                check_id=f"{flow.id}_runtime_error",
                check_name=f"{flow.name} — erro de runtime",
                categoria=Categoria.FLUXO,
                viewport=viewport,
                status=CheckStatus.ERRO,
                flow_name=flow.name,
                detail=f"Exceção inesperada no fluxo: {type(exc).__name__}: {exc}",
            )
        )
    finally:
        await context.close()

    return results


async def _execute_step(
    page: Page,
    step: FlowStep,
    flow: Flow,
    config: AuditConfig,
    viewport: Viewport,
    step_index: int,
    screenshots_dir: Optional[Path] = None,
) -> CheckResult:
    check_id = f"{flow.id}_step_{step_index}"
    check_name = f"{flow.name} → {step.name}"
    start = time.monotonic()

    try:
        try:
            await _perform_action(page, step, config)
            if step.expect is not None:
                await _verify_expect(page, step.expect, config)
        except _StepFailure as first_failure:
            await _retry_click_after_popup(page, step, config, first_failure)

        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.PASSOU,
            flow_name=flow.name,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    except _StepFailure as exc:
        screenshot_path, screenshot_b64 = await _screenshot_on_fail(page, config, screenshots_dir, check_id, viewport)
        detail = str(exc)
        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.FALHOU,
            flow_name=flow.name,
            detail=detail,
            duration_ms=int((time.monotonic() - start) * 1000),
            screenshot_path=screenshot_path,
            screenshot_b64=screenshot_b64,
            explanation=explain_failure(check_id, check_name, detail),
        )

    except Exception as exc:
        screenshot_path, screenshot_b64 = await _screenshot_on_fail(page, config, screenshots_dir, check_id, viewport)
        detail = f"{type(exc).__name__}: {exc}"
        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.ERRO,
            flow_name=flow.name,
            detail=detail,
            duration_ms=int((time.monotonic() - start) * 1000),
            screenshot_path=screenshot_path,
            screenshot_b64=screenshot_b64,
            explanation=explain_failure(check_id, check_name, detail),
        )


_MAX_CLICK_RETRIES = 2  # tentativas extras além da original (3 no total)


async def _retry_click_after_popup(
    page: Page, step: FlowStep, config: AuditConfig, original: Exception
) -> None:
    """Reexecuta uma ação de clique que falhou, fechando popups conhecidos antes de cada
    nova tentativa. Popups (ex: Klaviyo) às vezes engolem o clique via preventDefault sem
    gerar erro de interceptação — o Playwright reporta sucesso, mas a navegação não
    acontece, e só o 'expect' seguinte acusa o problema; outras vezes a própria animação
    de fechamento do popup (~1s+) ainda intercepta pointer events na primeira retentativa.
    Uma tentativa extra às vezes não bastava (visto em produção: F9, 2026-08-14, interceptado
    2x seguidas) — até _MAX_CLICK_RETRIES tentativas antes de desistir de vez.
    Ações que não são clique não se beneficiam disso — repropaga o erro original."""
    if step.action != ActionType.CLICK:
        raise original
    last_error: Exception = original
    for _attempt in range(_MAX_CLICK_RETRIES):
        await dismiss_known_popups(page, [p.close_selector for p in config.active_popups()])
        try:
            await _perform_action(page, step, config)
            if step.expect is not None:
                await _verify_expect(page, step.expect, config)
            return
        except _StepFailure as exc:
            last_error = exc
    raise last_error


async def _perform_action(page: Page, step: FlowStep, config: AuditConfig) -> None:
    """Executa a ação do step. Lança _StepFailure se o elemento não responde."""
    match step.action:
        case ActionType.GOTO:
            url = _resolve_url(step.value, config)
            # "load" espera TODOS os recursos terminarem — scripts de terceiros (Klaviyo,
            # VWO, GA4, chat, widgets) ocasionalmente atrasam ou travam esse evento sem
            # sinalizar erro real de rede (visto em produção: timeout de 30s numa tentativa,
            # carregamento normal na seguinte — 2026-08-14). Uma retentativa cobre a maioria
            # dos casos sem mascarar uma página genuinamente fora do ar (a 2ª tentativa
            # também falha nesse caso, e o erro é reportado normalmente).
            try:
                await page.goto(url, timeout=config.timeouts.navigation, wait_until="load")
            except PlaywrightTimeoutError:
                try:
                    await page.goto(url, timeout=config.timeouts.navigation, wait_until="load")
                except PlaywrightTimeoutError as exc:
                    raise _StepFailure(
                        f"Timeout ao navegar para {url} (2 tentativas): {exc}"
                    ) from exc

        case ActionType.CLICK:
            if not step.selector:
                raise ValueError(f"'click' requer 'selector' (step: {step.name})")
            # Popups conhecidos (ex: captura Klaviyo) interceptam cliques reais quando
            # visíveis por cima do elemento alvo — fecha antes de tentar, best-effort.
            await dismiss_known_popups(page, [p.close_selector for p in config.active_popups()])
            try:
                await page.locator(_visible(step.selector)).first.click(
                    timeout=config.timeouts.element
                )
            except PlaywrightTimeoutError:
                raise _StepFailure(
                    f"Elemento não encontrado ou não clicável após {config.timeouts.element}ms: "
                    f"'{step.selector}'"
                )

        case ActionType.FILL:
            if not step.selector or step.value is None:
                raise ValueError(f"'fill' requer 'selector' e 'value' (step: {step.name})")
            await dismiss_known_popups(page, [p.close_selector for p in config.active_popups()])
            try:
                await page.locator(_visible(step.selector)).first.fill(
                    step.value, timeout=config.timeouts.element
                )
            except PlaywrightTimeoutError:
                raise _StepFailure(
                    f"Campo não encontrado após {config.timeouts.element}ms: '{step.selector}'"
                )

        case ActionType.ASSERT_VISIBLE:
            if not step.selector:
                raise ValueError(f"'assert_visible' requer 'selector' (step: {step.name})")
            try:
                await page.locator(_visible(step.selector)).first.wait_for(
                    state="visible", timeout=config.timeouts.element
                )
            except PlaywrightTimeoutError:
                raise _StepFailure(
                    f"Elemento não visível após {config.timeouts.element}ms: '{step.selector}'"
                )

        case ActionType.ASSERT_NOT_VISIBLE:
            if not step.selector:
                raise ValueError(f"'assert_not_visible' requer 'selector' (step: {step.name})")
            if step.wait_ms:
                await page.wait_for_timeout(step.wait_ms)
            locator = page.locator(step.selector)
            count = await locator.count()
            if count > 0 and await locator.first.is_visible():
                raise _StepFailure(
                    f"Elemento está visível quando não deveria: '{step.selector}'"
                )

        case ActionType.WAIT:
            ms = step.wait_ms or 1000
            await page.wait_for_timeout(ms)

        case ActionType.DISMISS_POPUP:
            # Espera ATIVA pelo popup, não um sleep cego: retorna assim que ele aparecer
            # e for fechado, sem desperdiçar tempo se vier rápido. Timeout generoso porque
            # o runner do GitHub Actions (CPU compartilhada) pode ser mais lento que uma
            # máquina local para disparar o popup — um sleep fixo curto (8-10s, calibrado
            # localmente) falhou em produção mesmo com folga aparente.
            ms = step.wait_ms or 15000
            await dismiss_known_popups(
                page,
                [p.close_selector for p in config.active_popups()],
                visible_timeout_ms=ms,
            )


async def _verify_expect(page: Page, expect: object, config: AuditConfig) -> None:
    """Verifica a asserção após a ação. Lança _StepFailure se falhar."""
    from ..config.models import StepExpect  # import local para evitar circular

    assert isinstance(expect, StepExpect)

    match expect.type:
        case ExpectType.URL_CONTAINS:
            current = page.url
            if expect.value not in current:
                raise _StepFailure(
                    f"URL esperada conter '{expect.value}', mas URL atual é '{current}'"
                )

        case ExpectType.ELEMENT_VISIBLE:
            if not expect.selector:
                raise ValueError("expect 'element_visible' requer 'selector'")
            try:
                await page.locator(_visible(expect.selector)).first.wait_for(
                    state="visible", timeout=config.timeouts.element
                )
            except PlaywrightTimeoutError:
                raise _StepFailure(
                    f"Elemento esperado não visível após ação: '{expect.selector}'"
                )

        case ExpectType.ELEMENT_CLICKABLE:
            if not expect.selector:
                raise ValueError("expect 'element_clickable' requer 'selector'")
            try:
                locator = page.locator(_visible(expect.selector)).first
                await locator.wait_for(state="visible", timeout=config.timeouts.element)
                is_enabled = await locator.is_enabled()
                if not is_enabled:
                    raise _StepFailure(
                        f"Elemento visível mas desabilitado: '{expect.selector}'"
                    )
            except PlaywrightTimeoutError:
                raise _StepFailure(
                    f"Elemento esperado não encontrado após ação: '{expect.selector}'"
                )


def _resolve_url(value: Optional[str], config: AuditConfig) -> str:
    if not value:
        raise ValueError("'goto' requer 'value' com a URL")
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return config.absolute_url(value)


async def _screenshot_on_fail(
    page: Page,
    config: AuditConfig,
    screenshots_dir: Optional[Path],
    check_id: str,
    viewport: Viewport,
) -> tuple[Optional[str], Optional[str]]:
    if not screenshots_dir:
        return None, None
    stem = f"{check_id}_{viewport.value}"
    return await capture_failure_screenshot(
        page, screenshots_dir, stem,
        dismiss_selectors=[p.close_selector for p in config.active_popups()],
    )


class _StepFailure(Exception):
    """Sinaliza que um step falhou porque a LOJA não respondeu como esperado."""
