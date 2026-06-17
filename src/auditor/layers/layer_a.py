"""
Camada de verificação funcional dos fluxos (ex-Camada A).
Executa os fluxos definidos no audit-config.yaml navegando com Playwright.
Cada step produz um CheckResult. Abort_on_failure interrompe o fluxo no primeiro FALHOU.
"""

from __future__ import annotations

import time
from typing import Optional

from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeoutError

from ..config.models import ActionType, AuditConfig, ExpectType, Flow, FlowStep, RunMode
from ..types import Categoria, CheckResult, CheckStatus, Viewport

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


async def run_flow(
    browser: Browser,
    flow: Flow,
    config: AuditConfig,
    viewport: Viewport,
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

            result = await _execute_step(page, step, flow, config, viewport, i)
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
) -> CheckResult:
    check_id = f"{flow.id}_step_{step_index}"
    check_name = f"{flow.name} → {step.name}"
    start = time.monotonic()

    try:
        await _perform_action(page, step, config)

        if step.expect is not None:
            await _verify_expect(page, step.expect, config)

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
        # Falha de loja: elemento não encontrado, asserção falhou, clique bloqueado
        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.FALHOU,
            flow_name=flow.name,
            detail=str(exc),
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    except Exception as exc:
        # Erro do auditor: timeout de config, seletor malformado, etc.
        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            categoria=Categoria.FLUXO,
            viewport=viewport,
            status=CheckStatus.ERRO,
            flow_name=flow.name,
            detail=f"{type(exc).__name__}: {exc}",
            duration_ms=int((time.monotonic() - start) * 1000),
        )


async def _perform_action(page: Page, step: FlowStep, config: AuditConfig) -> None:
    """Executa a ação do step. Lança _StepFailure se o elemento não responde."""
    match step.action:
        case ActionType.GOTO:
            url = _resolve_url(step.value, config)
            try:
                await page.goto(url, timeout=config.timeouts.navigation, wait_until="load")
            except PlaywrightTimeoutError as exc:
                raise _StepFailure(f"Timeout ao navegar para {url}: {exc}") from exc

        case ActionType.CLICK:
            if not step.selector:
                raise ValueError(f"'click' requer 'selector' (step: {step.name})")
            try:
                await page.locator(step.selector).first.click(
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
            try:
                await page.locator(step.selector).first.fill(
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
                await page.locator(step.selector).first.wait_for(
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
                await page.locator(expect.selector).first.wait_for(
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
                locator = page.locator(expect.selector).first
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


class _StepFailure(Exception):
    """Sinaliza que um step falhou porque a LOJA não respondeu como esperado."""
