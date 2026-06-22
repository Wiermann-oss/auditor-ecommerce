#!/usr/bin/env python3
"""
Adiciona, ativa, desativa ou remove MÚLTIPLAS páginas em config/pages.yaml.
Chamado pelo workflow manage-pages.yml via GitHub Actions.

Variáveis de ambiente:
  ACTION        : add | activate | deactivate | remove
  PAGE_URLS     : uma URL por linha (ou separadas por vírgula)
  PAGE_VIEWPORTS: "desktop e mobile" | "só desktop" | "só mobile"  (só para 'add')
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
    pages: list[dict] = []
    current: dict | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("- name:"):
            if current is not None:
                pages.append(current)
            current = {"name": _val(stripped, "name")}
        elif current is not None:
            for field in ("url", "active", "viewports", "lighthouse_skip"):
                if stripped.startswith(f"{field}:"):
                    current[field] = _val(stripped, field)
    if current is not None:
        pages.append(current)
    return pages


def _val(line: str, field: str) -> str:
    m = re.match(rf"^\s*-?\s*{field}:\s*(.+)$", line)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def _url_eq(a: str, b: str) -> bool:
    return a.rstrip("/") == b.rstrip("/")


def _url_exists(raw: str, url: str) -> bool:
    return any(_url_eq(p.get("url", ""), url) for p in _parse_pages(raw))


# ── Auto-nome a partir da URL ─────────────────────────────────────────────────

def _auto_name(url: str) -> str:
    path = url.strip("/")
    if not path:
        return "Home"
    parts = path.split("/")
    slug = parts[-1].replace("-", " ").replace("_", " ").title()
    prefixes = {
        "collections": "Coleção",
        "products":    "Produto",
        "pages":       "Página",
        "blogs":       "Blog",
        "cart":        "Carrinho",
        "search":      "Busca",
        "account":     "Conta",
    }
    if len(parts) > 1 and parts[0] in prefixes:
        return f"{prefixes[parts[0]]} — {slug}"
    return slug


# ── Operações ─────────────────────────────────────────────────────────────────

def _set_active(raw: str, url: str, active: bool) -> str | None:
    if not _url_exists(raw, url):
        return None
    lines = raw.splitlines(keepends=True)
    result: list[str] = []
    in_target = False
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- name:"):
            in_target = False
            replaced = False
        if f'url: "{url}"' in line or f"url: {url}" in line or f"url: '{url}'" in line:
            in_target = True
        if in_target and stripped.startswith("active:") and not replaced:
            indent = len(line) - len(line.lstrip())
            line = " " * indent + f"active: {'true' if active else 'false'}\n"
            replaced = True
            in_target = False
        result.append(line)
    return "".join(result)


def _remove_page(raw: str, url: str) -> str | None:
    if not _url_exists(raw, url):
        return None
    lines = raw.splitlines(keepends=True)
    result: list[str] = []
    skip = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("- name:"):
            block = "".join(lines[i: i + 8])
            skip = (
                f'url: "{url}"' in block
                or f"url: {url}" in block
                or f"url: '{url}'" in block
            )
        if not skip:
            result.append(line)
    return "".join(result)


def _add_page(raw: str, name: str, url: str, viewports_label: str) -> str:
    viewports = VIEWPORT_MAP.get(viewports_label, "[desktop, mobile]")
    block = (
        f'\n  - name: "{name}"\n'
        f'    url: "{url}"\n'
        f"    active: true\n"
        f"    viewports: {viewports}\n"
    )
    marker = "  # ── Páginas de campanha"
    if marker in raw:
        return raw.replace(marker, block + marker, 1)
    return raw.rstrip() + "\n" + block


# ── Parse de múltiplas URLs ───────────────────────────────────────────────────

def _parse_urls(raw_input: str) -> list[str]:
    """Extrai lista de URLs de um bloco de texto (uma por linha ou vírgula)."""
    urls: list[str] = []
    for part in re.split(r"[\n,]+", raw_input):
        url = part.strip()
        if not url or url.startswith("#"):
            continue
        if not url.startswith("/"):
            url = "/" + url.lstrip("/")
        if url not in urls:
            urls.append(url)
    return urls


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    action    = os.environ.get("ACTION", "").strip().lower()
    urls_raw  = os.environ.get("PAGE_URLS", os.environ.get("PAGE_URL", "")).strip()
    viewports = os.environ.get("PAGE_VIEWPORTS", "desktop e mobile").strip()

    urls = _parse_urls(urls_raw)
    if not urls:
        print("Erro: PAGE_URLS não definida ou vazia. Informe ao menos uma URL.")
        sys.exit(1)

    valid_actions = ("add", "activate", "deactivate", "remove")
    if action not in valid_actions:
        print(f"Ação inválida: '{action}'. Use: {' | '.join(valid_actions)}")
        sys.exit(1)

    raw = _load_raw()
    ok: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for url in urls:
        if action == "add":
            if _url_exists(raw, url):
                skipped.append(f"  ~ {url}  (já existe, ignorado)")
                continue
            name = _auto_name(url)
            raw = _add_page(raw, name, url, viewports)
            ok.append(f"  + {url}  →  \"{name}\"")

        elif action in ("activate", "deactivate"):
            result = _set_active(raw, url, active=(action == "activate"))
            if result is None:
                errors.append(f"  ✗ {url}  (não encontrada)")
            else:
                raw = result
                symbol = "✓" if action == "activate" else "○"
                ok.append(f"  {symbol} {url}")

        elif action == "remove":
            result = _remove_page(raw, url)
            if result is None:
                errors.append(f"  ✗ {url}  (não encontrada)")
            else:
                raw = result
                ok.append(f"  - {url}")

    PAGES_PATH.write_text(raw, encoding="utf-8")

    print(f"\n{'═' * 50}")
    print(f"  Ação: {action.upper()} | {len(urls)} URL(s) processada(s)")
    print(f"{'═' * 50}\n")
    if ok:
        print("Executado com sucesso:")
        print("\n".join(ok))
    if skipped:
        print("\nIgnorado:")
        print("\n".join(skipped))
    if errors:
        print("\nErros:")
        print("\n".join(errors))
    print(f"\nArquivo salvo: {PAGES_PATH}")

    if errors and not ok and not skipped:
        sys.exit(1)


if __name__ == "__main__":
    main()
