"""
Captura de screenshot de falha — utilitário interno dos layers.
Salva PNG em disco e retorna o caminho relativo e o base64 para embedding no HTML.
"""

from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


async def dismiss_known_popups(page, close_selectors: list[str]) -> None:
    """Fecha popups conhecidos (ex: popup de captura) antes de uma ação real (clique, fill)
    ou de uma screenshot de evidência. Best-effort — um popup ausente ou já fechado não deve
    impedir a ação seguinte.

    Espera ativamente o popup aparecer (até 1s) em vez de checar visibilidade uma vez só —
    cobre o caso de pegar o popup no meio da própria animação de entrada. NÃO cobre o caso
    de o popup ainda não ter disparado (medido em produção: até 6-8s após o load, bem mais
    que os 4.5s do "popup_delay" do config) — resolver isso aqui, com um timeout maior,
    multiplicaria o tempo de execução em CADA clique do fluxo depois que o popup já foi
    fechado (o locator não teria como saber que não vale mais a pena esperar). Isso precisa
    de uma espera dedicada, uma vez só, logo na entrada do fluxo — ver ADR/decisão pendente.

    Usa page.mouse.click nas coordenadas do botão em vez de locator.click: o próprio wrapper
    interno do formulário Klaviyo se sobrepõe geometricamente ao botão de fechar, e a
    checagem de actionability do Playwright (inclusive com force=True) recusa o clique como
    "subtree intercepts pointer events" — falso positivo confirmado manualmente (um clique
    físico nas mesmas coordenadas fecha o popup normalmente). Um único clique já é
    suficiente; a animação de saída do Klaviyo só demora mais de 1s para completar, por
    isso a espera por state=hidden é generosa. NÃO clicar de novo se o primeiro clique já
    disparou — uma segunda tentativa em cima do popup em transição faz o bounding_box()
    ficar preso esperando o elemento estabilizar (visto em produção: 30s de timeout).
    Não usar antes de screenshots do próprio popup_checker: lá o popup visível É a evidência."""
    for selector in close_selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=1000)
        except Exception:
            continue
        try:
            box = await locator.bounding_box(timeout=2000)
            if box is None:
                continue
            await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            await locator.wait_for(state="hidden", timeout=4000)
        except Exception:
            continue


async def capture_failure_screenshot(
    page,                       # playwright.async_api.Page
    screenshots_dir: Path,
    stem: str,
    dismiss_selectors: Optional[list[str]] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Tira screenshot da página atual e salva em screenshots_dir/{stem}.png.

    Se 'dismiss_selectors' for informado, tenta fechar popups conhecidos antes de
    capturar — evita que a evidência mostre só um popup por cima da página real.

    Retorna:
        (screenshot_path, screenshot_b64)
        screenshot_path: caminho relativo ao reports_dir (ex: "screenshots/run_id/lcp_desktop.png")
        screenshot_b64:  PNG codificado em base64 para embedding no HTML
    """
    try:
        if dismiss_selectors:
            await dismiss_known_popups(page, dismiss_selectors)
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        safe_stem = re.sub(r"[^a-z0-9_\-]", "_", stem.lower())[:80]
        filename = f"{safe_stem}.png"
        full_path = screenshots_dir / filename
        await page.screenshot(path=str(full_path), full_page=False)
        b64 = base64.b64encode(full_path.read_bytes()).decode("ascii")
        # Caminho relativo: "screenshots/{run_id}/{filename}"
        rel_path = f"screenshots/{screenshots_dir.name}/{filename}"
        return rel_path, b64
    except Exception as exc:
        log.debug("Screenshot falhou (%s): %s", stem, exc)
        return None, None


def enrich_failure(
    result,              # CheckResult
    screenshot_path: Optional[str],
    screenshot_b64: Optional[str],
    explanation: Optional[str],
) -> None:
    """Anexa evidências a um CheckResult com falha ou erro (in-place)."""
    from ..types import CheckStatus
    if result.status == CheckStatus.PASSOU:
        return
    if screenshot_path and not result.screenshot_path:
        result.screenshot_path = screenshot_path
    if screenshot_b64 and not result.screenshot_b64:
        result.screenshot_b64 = screenshot_b64
    if explanation and not result.explanation:
        result.explanation = explanation
