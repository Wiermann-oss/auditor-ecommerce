"""
Camada de saúde técnica das páginas (ex-Camada B).
Cada checagem produz um CheckResult — nunca propaga exceção para o engine.
Cobre: HTTP status, erros de JS, requisições com falha, load time, LCP/CLS/FID via Lighthouse.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

from playwright.async_api import Browser, ConsoleMessage, Request, Response

from ..config.models import AuditConfig, CriticalPage, Thresholds
from ..types import Categoria, CheckResult, CheckStatus, Viewport

_VIEWPORT_DIMS = {
    Viewport.DESKTOP: {"width": 1280, "height": 800},
    Viewport.MOBILE: {"width": 390, "height": 844},  # iPhone 14 Pro
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


async def run_page_health_checks(
    browser: Browser,
    critical_page: CriticalPage,
    config: AuditConfig,
    viewport: Viewport,
) -> list[CheckResult]:
    """Executa todas as checagens de saúde técnica para uma página num viewport."""
    url = config.absolute_url(critical_page.url)
    results: list[CheckResult] = []
    start_mono = time.monotonic()

    context = await browser.new_context(
        viewport=_VIEWPORT_DIMS[viewport],
        user_agent=_USER_AGENTS[viewport],
        ignore_https_errors=False,
    )
    page = await context.new_page()

    console_errors: list[str] = []
    failed_requests: list[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            console_errors.append(msg.text)

    def on_request_failed(req: Request) -> None:
        failed_requests.append(f"{req.url} — {req.failure or 'unknown failure'}")

    def on_response(response: Response) -> None:
        if response.status >= 400 and response.request.resource_type != "document":
            failed_requests.append(f"{response.url} — HTTP {response.status}")

    page.on("console", on_console)
    page.on("requestfailed", on_request_failed)
    page.on("response", on_response)

    try:
        nav_start = time.monotonic()
        response = await page.goto(
            url,
            timeout=config.timeouts.navigation,
            wait_until="load",
        )
        nav_duration_ms = int((time.monotonic() - nav_start) * 1000)

        results.append(_check_http_status(url, response, viewport, nav_duration_ms))
        results.append(_check_console_errors(url, console_errors, viewport))
        results.append(_check_failed_requests(url, failed_requests, viewport))

        load_ms = await _get_load_time_ms(page)
        results.append(_check_load_time(url, load_ms, config.thresholds.load_time_ms, viewport))

        if not critical_page.lighthouse_skip:
            lh_results = await _run_lighthouse_checks(url, config.thresholds, viewport)
            results.extend(lh_results)

    except Exception as exc:
        duration_ms = int((time.monotonic() - start_mono) * 1000)
        results.append(
            CheckResult(
                check_id="page_load_error",
                check_name="Carregamento da página",
                categoria=Categoria.SAUDE_TECNICA,
                viewport=viewport,
                status=CheckStatus.ERRO,
                page_url=url,
                detail=f"Erro ao carregar {url}: {type(exc).__name__}: {exc}",
                duration_ms=duration_ms,
            )
        )
    finally:
        await context.close()

    return results


# — Checagens individuais —

def _check_http_status(
    url: str,
    response: Optional[Response],
    viewport: Viewport,
    duration_ms: int,
) -> CheckResult:
    if response is None:
        return CheckResult(
            check_id="http_status",
            check_name="Status HTTP",
            categoria=Categoria.SAUDE_TECNICA,
            viewport=viewport,
            status=CheckStatus.ERRO,
            page_url=url,
            detail=f"Nenhuma resposta recebida de {url}",
            duration_ms=duration_ms,
        )

    passed = response.status == 200
    return CheckResult(
        check_id="http_status",
        check_name="Status HTTP",
        categoria=Categoria.SAUDE_TECNICA,
        viewport=viewport,
        status=CheckStatus.PASSOU if passed else CheckStatus.FALHOU,
        page_url=url,
        detail=None if passed else f"Status {response.status} — esperado 200",
        value=float(response.status),
        unit="status_code",
        duration_ms=duration_ms,
    )


def _check_console_errors(
    url: str,
    errors: list[str],
    viewport: Viewport,
) -> CheckResult:
    passed = len(errors) == 0
    detail: Optional[str] = None
    if not passed:
        sample = errors[:5]
        detail = f"{len(errors)} erro(s) de JS no console: " + " | ".join(sample)
        if len(errors) > 5:
            detail += f" ... (+{len(errors) - 5} mais)"
    return CheckResult(
        check_id="console_errors",
        check_name="Erros de JavaScript no console",
        categoria=Categoria.SAUDE_TECNICA,
        viewport=viewport,
        status=CheckStatus.PASSOU if passed else CheckStatus.FALHOU,
        page_url=url,
        detail=detail,
        value=float(len(errors)),
        unit="count",
    )


def _check_failed_requests(
    url: str,
    failures: list[str],
    viewport: Viewport,
) -> CheckResult:
    # Filtrar requisições de extensões de navegador e analytics (ruído esperado)
    filtered = [
        f for f in failures
        if not any(skip in f for skip in ["chrome-extension://", "favicon.ico"])
    ]
    passed = len(filtered) == 0
    detail: Optional[str] = None
    if not passed:
        sample = filtered[:5]
        detail = f"{len(filtered)} requisição(ões) com falha: " + " | ".join(sample)
        if len(filtered) > 5:
            detail += f" ... (+{len(filtered) - 5} mais)"
    return CheckResult(
        check_id="failed_requests",
        check_name="Requisições de rede com falha",
        categoria=Categoria.SAUDE_TECNICA,
        viewport=viewport,
        status=CheckStatus.PASSOU if passed else CheckStatus.FALHOU,
        page_url=url,
        detail=detail,
        value=float(len(filtered)),
        unit="count",
    )


def _check_load_time(
    url: str,
    load_ms: Optional[float],
    threshold_ms: float,
    viewport: Viewport,
) -> CheckResult:
    if load_ms is None:
        return CheckResult(
            check_id="load_time",
            check_name="Tempo de carregamento (load event)",
            categoria=Categoria.SAUDE_TECNICA,
            viewport=viewport,
            status=CheckStatus.ERRO,
            page_url=url,
            detail="Navigation Timing API não retornou valor válido",
            threshold=threshold_ms,
            unit="ms",
        )

    passed = load_ms <= threshold_ms
    return CheckResult(
        check_id="load_time",
        check_name="Tempo de carregamento (load event)",
        categoria=Categoria.SAUDE_TECNICA,
        viewport=viewport,
        status=CheckStatus.PASSOU if passed else CheckStatus.FALHOU,
        page_url=url,
        detail=None if passed else f"Load time={load_ms:.0f}ms excede limiar de {threshold_ms:.0f}ms",
        value=load_ms,
        unit="ms",
        threshold=threshold_ms,
    )


async def _get_load_time_ms(page: object) -> Optional[float]:
    try:
        result = await page.evaluate(  # type: ignore[attr-defined]
            "() => { const t = performance.timing; "
            "return t.loadEventEnd > 0 ? t.loadEventEnd - t.fetchStart : null; }"
        )
        return float(result) if result is not None else None
    except Exception:
        return None


# — Lighthouse —

async def _run_lighthouse_checks(
    url: str,
    thresholds: Thresholds,
    viewport: Viewport,
) -> list[CheckResult]:
    cmd = [
        "lighthouse",
        url,
        "--output=json",
        "--quiet",
        "--chrome-flags=--headless --no-sandbox --disable-gpu",
        "--only-categories=performance",
        "--no-enable-error-reporting",
    ]
    if viewport == Viewport.DESKTOP:
        cmd.append("--preset=desktop")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except FileNotFoundError:
        return [_lighthouse_erro(url, viewport, "Lighthouse CLI não encontrado — instale com: npm install -g lighthouse")]
    except asyncio.TimeoutError:
        return [_lighthouse_erro(url, viewport, "Lighthouse excedeu 120s de timeout")]
    except Exception as exc:
        return [_lighthouse_erro(url, viewport, f"Erro ao executar Lighthouse: {exc}")]

    if proc.returncode not in (0, 1):  # LH retorna 1 quando há avisos mas a saída é válida
        err_sample = stderr.decode(errors="replace")[:300]
        return [_lighthouse_erro(url, viewport, f"Lighthouse falhou (exit {proc.returncode}): {err_sample}")]

    try:
        data = json.loads(stdout.decode(errors="replace"))
    except json.JSONDecodeError as exc:
        return [_lighthouse_erro(url, viewport, f"Saída do Lighthouse não é JSON válido: {exc}")]

    audits = data.get("audits", {})
    return list(filter(None, [
        _parse_lcp(url, audits, thresholds.lcp_ms, viewport),
        _parse_cls(url, audits, thresholds.cls, viewport),
        _parse_fid(url, audits, thresholds.fid_ms, viewport),
    ]))


def _lighthouse_erro(url: str, viewport: Viewport, detail: str) -> CheckResult:
    return CheckResult(
        check_id="lighthouse",
        check_name="Lighthouse (LCP / CLS / FID)",
        categoria=Categoria.SAUDE_TECNICA,
        viewport=viewport,
        status=CheckStatus.ERRO,
        page_url=url,
        detail=detail,
    )


def _parse_lcp(
    url: str,
    audits: dict,
    threshold: float,
    viewport: Viewport,
) -> Optional[CheckResult]:
    audit = audits.get("largest-contentful-paint", {})
    value = audit.get("numericValue")
    if value is None:
        return None
    value = float(value)
    passed = value <= threshold
    return CheckResult(
        check_id="lcp",
        check_name="LCP — Largest Contentful Paint",
        categoria=Categoria.SAUDE_TECNICA,
        viewport=viewport,
        status=CheckStatus.PASSOU if passed else CheckStatus.FALHOU,
        page_url=url,
        detail=None if passed else f"LCP={value:.0f}ms excede limiar de {threshold:.0f}ms",
        value=value,
        unit="ms",
        threshold=threshold,
    )


def _parse_cls(
    url: str,
    audits: dict,
    threshold: float,
    viewport: Viewport,
) -> Optional[CheckResult]:
    audit = audits.get("cumulative-layout-shift", {})
    value = audit.get("numericValue")
    if value is None:
        return None
    value = float(value)
    passed = value <= threshold
    return CheckResult(
        check_id="cls",
        check_name="CLS — Cumulative Layout Shift",
        categoria=Categoria.SAUDE_TECNICA,
        viewport=viewport,
        status=CheckStatus.PASSOU if passed else CheckStatus.FALHOU,
        page_url=url,
        detail=None if passed else f"CLS={value:.3f} excede limiar de {threshold:.2f} (histórico da loja: 1.3–2.5)",
        value=value,
        unit="score",
        threshold=threshold,
    )


def _parse_fid(
    url: str,
    audits: dict,
    threshold: float,
    viewport: Viewport,
) -> Optional[CheckResult]:
    # Tenta max-potential-fid primeiro, depois total-blocking-time como proxy
    audit = audits.get("max-potential-fid") or audits.get("total-blocking-time", {})
    value = audit.get("numericValue")
    if value is None:
        return None
    value = float(value)
    passed = value <= threshold
    return CheckResult(
        check_id="fid",
        check_name="FID — First Input Delay (max potencial)",
        categoria=Categoria.SAUDE_TECNICA,
        viewport=viewport,
        status=CheckStatus.PASSOU if passed else CheckStatus.FALHOU,
        page_url=url,
        detail=None if passed else f"FID={value:.0f}ms excede limiar de {threshold:.0f}ms",
        value=value,
        unit="ms",
        threshold=threshold,
    )
