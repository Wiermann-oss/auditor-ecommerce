#!/usr/bin/env python3
"""
Adiciona, ativa, desativa ou remove páginas em config/pages.yaml.
Chamado pelo workflow manage-pages.yml via GitHub Actions.

Variáveis de ambiente esperadas:
  ACTION       : add | activate | deactivate | remove
  PAGE_NAME    : nome da página (obrigatório para 'add')
  PAGE_URL     : URL da página, ex: /collections/verao-2026
  PAGE_VIEWPORTS: "desktop e mobile" | "só desktop" | "só mobile"
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

PAGES_PATH = Path("config/pages.yaml")

VIEWPORT_MAP = {
    "desktop e mobile": "[desktop, mobile]",
    "só desktop": "[desktop]",
    "só mobile": "[mobile]",
}


# ── Leitura e escrita preservando comentários ─────────────────────────────────

def _load_raw() -> str:
    if not PAGES_PATH.exists():
        raise SystemExit(f"Arquivo não encontrado: {PAGES_PATH}")
    return PAGES_PATH.read_text(encoding="utf-8")


def _parse_pages(raw: str) -> list[dict]:
    """Extrai blocos de página do YAML sem depender de lib externa."""
    pages = []
    current: dict | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("- name:"):
            if current is not None:
                pages.append(current)
            current = {"name": _extract_value(stripped, "name"), "_line": line}
        elif current is not None:
            for field in ("url", "active", "viewports", "lighthouse_skip"):
                if stripped.startswith(f"{field}:"):
                    current[field] = _extract_value(stripped, field)
    if current is not None:
        pages.append(current)
    return pages


def _extract_value(line: str, field: str) -> str:
    m = re.match(rf"^\s*-?\s*{field}:\s*(.+)$", line)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def _url_matches(page_url: str, target: str) -> bool:
    return page_url.rstrip("/") == target.rstrip("/")


# ── Operações ─────────────────────────────────────────────────────────────────

def _set_active(raw: str, url: str, active: bool) -> str:
    """Altera o campo active da página com a URL dada."""
    pages = _parse_pages(raw)
    found = any(_url_matches(p.get("url", ""), url) for p in pages)
    if not found:
        print(f"Página com URL '{url}' não encontrada em {PAGES_PATH}.")
        sys.exit(1)

    lines = raw.splitlines(keepends=True)
    result = []
    in_target = False
    active_replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- name:"):
            in_target = False
            active_replaced = False
        if f"url: \"{url}\"" in line or f"url: {url}" in line or f"url: '{url}'" in line:
            in_target = True
        if in_target and stripped.startswith("active:") and not active_replaced:
            indent = len(line) - len(line.lstrip())
            line = " " * indent + f"active: {'true' if active else 'false'}\n"
            active_replaced = True
            in_target = False
        result.append(line)
    return "".join(result)


def _remove_page(raw: str, url: str) -> str:
    """Remove o bloco inteiro da página com a URL dada."""
    pages = _parse_pages(raw)
    found = any(_url_matches(p.get("url", ""), url) for p in pages)
    if not found:
        print(f"Página com URL '{url}' não encontrada em {PAGES_PATH}.")
        sys.exit(1)

    lines = raw.splitlines(keepends=True)
    result = []
    skip = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("- name:"):
            # Verifica se alguma linha próxima tem a URL alvo
            block = "".join(lines[i: i + 8])
            if f'url: "{url}"' in block or f"url: {url}" in block or f"url: '{url}'" in block:
                skip = True
            else:
                skip = False
        elif skip and stripped.startswith("- name:"):
            skip = False
        if not skip:
            result.append(line)
    return "".join(result)


def _add_page(raw: str, name: str, url: str, viewports_label: str) -> str:
    """Adiciona nova página antes da seção de comentários de campanha."""
    viewports = VIEWPORT_MAP.get(viewports_label, "[desktop, mobile]")
    block = (
        f'\n  - name: "{name}"\n'
        f"    url: \"{url}\"\n"
        f"    active: true\n"
        f"    viewports: {viewports}\n"
    )
    # Inserir antes do bloco de comentários de campanha, se existir
    marker = "  # ── Páginas de campanha"
    if marker in raw:
        return raw.replace(marker, block + marker, 1)
    # Ou no final
    return raw.rstrip() + "\n" + block


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    action = os.environ.get("ACTION", "").strip().lower()
    name = os.environ.get("PAGE_NAME", "").strip()
    url = os.environ.get("PAGE_URL", "").strip()
    viewports = os.environ.get("PAGE_VIEWPORTS", "desktop e mobile").strip()

    if not url:
        print("Erro: PAGE_URL não definida.")
        sys.exit(1)

    raw = _load_raw()

    if action == "add":
        if not name:
            print("Erro: PAGE_NAME é obrigatório para adicionar uma página.")
            sys.exit(1)
        raw = _add_page(raw, name, url, viewports)
        print(f"Página '{name}' ({url}) adicionada com active: true.")

    elif action == "activate":
        raw = _set_active(raw, url, active=True)
        print(f"Página '{url}' ativada.")

    elif action == "deactivate":
        raw = _set_active(raw, url, active=False)
        print(f"Página '{url}' desativada.")

    elif action == "remove":
        raw = _remove_page(raw, url)
        print(f"Página '{url}' removida.")

    else:
        print(f"Ação desconhecida: '{action}'. Use: add | activate | deactivate | remove")
        sys.exit(1)

    PAGES_PATH.write_text(raw, encoding="utf-8")
    print(f"Arquivo salvo: {PAGES_PATH}")


if __name__ == "__main__":
    main()
