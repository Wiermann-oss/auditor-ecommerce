"""
Camada de saúde técnica das páginas (ex-Camada B).
Cada checagem produz um CheckResult — nunca propaga exceção para o engine.
Cobre: HTTP status, erros de JS, requisições com falha, load time, LCP/CLS/FID via Lighthouse.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, ConsoleMessage, Request, Response

from ..config.models import AuditConfig, CriticalPage, Thresholds
from ..reporters.explanations import explain_failure
from ..types import Categoria, CheckResult, CheckStatus, Viewport
from ._screenshot import capture_failure_screenshot, enrich_failure

# Padrões de erros de terceiros decorativos — aparecem no relatório mas não reprovam a checagem.
# Use padrões específicos (endpoint, não domínio inteiro) para não mascarar falhas reais.
_THIRD_PARTY_NOISE: tuple[str, ...] = (
    # Reclame Aqui — widget decorativo com CORS mal configurado no servidor deles
    "reclameaqui.com.br",
    "RA-Reputation",
    # Sizebay — endpoint de perfil pessoal retorna 404 para visitante anônimo (sem histórico)
    # Outros endpoints sizebay.technology continuam sendo monitorados normalmente
    "sizebay.technology/api/me/analysis",
)

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
    screenshots_dir: Optional[Path] = None,
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
        rtype = req.resource_type  # xhr, fetch, script, beacon, etc.
        method = req.method
        failure = req.failure or "unknown failure"
        failed_requests.append(f"{req.url} — {failure} [{method} {rtype}]")

    def on_response(response: Response) -> None:
        if response.status >= 400 and response.request.resource_type != "document":
            failed_requests.append(f"{response.url} — HTTP {response.status}")

    page.on("console", on_console)
    page.on("requestfailed", on_request_failed)
    page.on("response", on_response)

    page_stem = f"{_safe_name(critical_page.name)}_{viewport.value}"
    screenshot_path: Optional[str] = None
    screenshot_b64: Optional[str] = None

    try:
        nav_start = time.monotonic()
        response = await page.goto(
            url,
            timeout=config.timeouts.navigation,
            wait_until="load",
        )
        # Aguarda a rede quietar para dar tempo a beacons e analytics dispararem.
        # networkidle = sem requisições ativas por 500ms consecutivos (máx 5s).
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass  # site com polling contínuo nunca atinge idle — ignora e segue
        nav_duration_ms = int((time.monotonic() - nav_start) * 1000)

        check_results_raw = [
            _check_http_status(url, response, viewport, nav_duration_ms),
            _check_console_errors(url, _enrich_console_errors(console_errors, failed_requests), viewport),
            _check_failed_requests(url, failed_requests, viewport),
        ]

        load_ms = await _get_load_time_ms(page)
        check_results_raw.append(_check_load_time(url, load_ms, config.thresholds.load_time_ms, viewport))

        if not critical_page.lighthouse_skip:
            lh_results = await _run_lighthouse_checks(url, config.thresholds, viewport)
            check_results_raw.extend(lh_results)

        # Capturar screenshot apenas se houver falhas — página ainda está aberta
        has_failures = any(cr.status != CheckStatus.PASSOU for cr in check_results_raw)
        if has_failures and screenshots_dir:
            screenshot_path, screenshot_b64 = await capture_failure_screenshot(
                page, screenshots_dir, page_stem
            )

        for cr in check_results_raw:
            enrich_failure(
                cr, screenshot_path, screenshot_b64,
                explain_failure(cr.check_id, cr.check_name, cr.detail, cr.value, cr.threshold, cr.unit)
            )
        results.extend(check_results_raw)

    except Exception as exc:
        duration_ms = int((time.monotonic() - start_mono) * 1000)
        if screenshots_dir:
            screenshot_path, screenshot_b64 = await capture_failure_screenshot(
                page, screenshots_dir, f"error_{page_stem}"
            )
        err_result = CheckResult(
            check_id="page_load_error",
            check_name="Carregamento da página",
            categoria=Categoria.SAUDE_TECNICA,
            viewport=viewport,
            status=CheckStatus.ERRO,
            page_url=url,
            detail=f"Erro ao carregar {url}: {type(exc).__name__}: {exc}",
            duration_ms=duration_ms,
            screenshot_path=screenshot_path,
            screenshot_b64=screenshot_b64,
            explanation=(
                "A página não carregou corretamente durante a auditoria. "
                "Pode ser instabilidade temporária da loja, timeout de rede ou erro de configuração do auditor."
            ),
        )
        results.append(err_result)
    finally:
        await context.close()

    return results


def _safe_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", name.lower().strip())[:30]


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


def _enrich_console_errors(
    console_errors: list[str],
    failed_requests: list[str],
) -> list[str]:
    """Substitui mensagens genéricas 'Failed to load resource' pela URL real da requisição."""
    # Constrói índice: assinatura_de_falha → fila de URLs
    url_by_sig: dict[str, deque[str]] = defaultdict(deque)
    for entry in failed_requests:
        if " — HTTP " in entry:
            url, _, code = entry.rpartition(" — HTTP ")
            url_by_sig[f"http_{code.strip()}"].append(url)
        elif " — " in entry:
            url, _, failure = entry.rpartition(" — ")
            url_by_sig[failure.strip()].append(url)

    enriched: list[str] = []
    for msg in console_errors:
        # "Failed to load resource: the server responded with a status of 401 ()"
        m = re.search(r"Failed to load resource: the server responded with a status of (\d+)", msg)
        if m:
            sig = f"http_{m.group(1)}"
            if url_by_sig[sig]:
                enriched.append(f"Failed to load resource: HTTP {m.group(1)} — {url_by_sig[sig].popleft()}")
                continue

        # "Failed to load resource: net::ERR_FAILED" e similares
        m = re.search(r"Failed to load resource: (net::ERR_\w+)", msg)
        if m:
            sig = m.group(1)
            if url_by_sig[sig]:
                enriched.append(f"Failed to load resource: {sig} — {url_by_sig[sig].popleft()}")
                continue

        enriched.append(msg)

    return enriched


def _is_bare_err_failed(msg: str) -> bool:
    """net::ERR_FAILED sem URL — gerado pelo Chrome como companheiro de erros CORS.
    Sozinho é inacionável: sem URL não há o que investigar."""
    return bool(re.fullmatch(r"Failed to load resource: net::ERR_FAILED", msg.strip()))


def _check_console_errors(
    url: str,
    errors: list[str],
    viewport: Viewport,
) -> CheckResult:
    def _is_noise(msg: str) -> bool:
        return any(p in msg for p in _THIRD_PARTY_NOISE)

    real_errors = [e for e in errors if not _is_noise(e)]
    noise_warnings = [e for e in errors if _is_noise(e)]

    # net::ERR_FAILED sem URL é companheiro inevitável de bloqueios CORS.
    # Quando há CORS noise na página, esses bare ERR_FAILED são reclassificados
    # como noise — sem URL são inacionáveis e já representados pelo CORS warning.
    has_cors_noise = any("CORS" in w or "Access-Control" in w for w in noise_warnings)
    if has_cors_noise:
        bare_failed = [e for e in real_errors if _is_bare_err_failed(e)]
        real_errors = [e for e in real_errors if not _is_bare_err_failed(e)]
        noise_warnings.extend(bare_failed)

    passed = len(real_errors) == 0
    detail_parts: list[str] = []

    if real_errors:
        sample = real_errors[:5]
        part = f"{len(real_errors)} erro(s) de JS: " + " | ".join(sample)
        if len(real_errors) > 5:
            part += f" ... (+{len(real_errors) - 5} mais)"
        detail_parts.append(part)

    if noise_warnings:
        sample = noise_warnings[:3]
        part = f"⚠ {len(noise_warnings)} aviso(s) de terceiros sem impacto: " + " | ".join(sample)
        if len(noise_warnings) > 3:
            part += f" ... (+{len(noise_warnings) - 3} mais)"
        detail_parts.append(part)

    return CheckResult(
        check_id="console_errors",
        check_name="Erros de JavaScript no console",
        categoria=Categoria.SAUDE_TECNICA,
        viewport=viewport,
        status=CheckStatus.PASSOU if passed else CheckStatus.FALHOU,
        page_url=url,
        detail=" || ".join(detail_parts) if detail_parts else None,
        value=float(len(real_errors)),
        unit="count",
    )


def _check_failed_requests(
    url: str,
    failures: list[str],
    viewport: Viewport,
) -> CheckResult:
    _SKIP = ("chrome-extension://", "favicon.ico")

    def _is_noise(entry: str) -> bool:
        return any(p in entry for p in _THIRD_PARTY_NOISE)

    def _is_aborted(entry: str) -> bool:
        # ERR_ABORTED nunca é falha de servidor — é o browser cancelando a requisição
        # (context fechando, prefetch cancelado, navegação interrompida).
        # No browser real essas requisições completam normalmente.
        return "net::ERR_ABORTED" in entry

    relevant = [f for f in failures if not any(s in f for s in _SKIP)]
    aborted   = [f for f in relevant if _is_aborted(f)]
    relevant  = [f for f in relevant if not _is_aborted(f)]
    real_failures = [f for f in relevant if not _is_noise(f)]
    noise_warnings = [f for f in relevant if _is_noise(f)]

    passed = len(real_failures) == 0
    detail_parts: list[str] = []

    if real_failures:
        sample = real_failures[:5]
        part = f"{len(real_failures)} requisição(ões) com falha: " + " | ".join(sample)
        if len(real_failures) > 5:
            part += f" ... (+{len(real_failures) - 5} mais)"
        detail_parts.append(part)

    if noise_warnings:
        sample = noise_warnings[:3]
        part = f"⚠ {len(noise_warnings)} requisição(ões) de terceiros sem impacto: " + " | ".join(sample)
        if len(noise_warnings) > 3:
            part += f" ... (+{len(noise_warnings) - 3} mais)"
        detail_parts.append(part)

    if aborted:
        sample = aborted[:3]
        part = f"ℹ {len(aborted)} requisição(ões) abortadas pelo browser (falso positivo do ambiente headless): " + " | ".join(sample)
        if len(aborted) > 3:
            part += f" ... (+{len(aborted) - 3} mais)"
        detail_parts.append(part)

    return CheckResult(
        check_id="failed_requests",
        check_name="Requisições de rede com falha",
        categoria=Categoria.SAUDE_TECNICA,
        viewport=viewport,
        status=CheckStatus.PASSOU if passed else CheckStatus.FALHOU,
        page_url=url,
        detail=" || ".join(detail_parts) if detail_parts else None,
        value=float(len(real_failures)),
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
