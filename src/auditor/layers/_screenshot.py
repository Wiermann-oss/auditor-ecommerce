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


async def capture_failure_screenshot(
    page,                       # playwright.async_api.Page
    screenshots_dir: Path,
    stem: str,
) -> tuple[Optional[str], Optional[str]]:
    """
    Tira screenshot da página atual e salva em screenshots_dir/{stem}.png.

    Retorna:
        (screenshot_path, screenshot_b64)
        screenshot_path: caminho relativo ao reports_dir (ex: "screenshots/run_id/lcp_desktop.png")
        screenshot_b64:  PNG codificado em base64 para embedding no HTML
    """
    try:
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
