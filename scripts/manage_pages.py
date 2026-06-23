#!/usr/bin/env python3
"""
Adiciona, desativa ou remove páginas em config/pages.yaml.
Chamado pelo workflow manage-pages.yml.

Variáveis de ambiente:
  ADD_URLS        : URLs para adicionar, separadas por vírgula
  DEACTIVATE_URLS : URLs para desativar, separadas por vírgula
  REMOVE_URLS     : URLs para remover definitivamente, separadas por vírgula
  PAGE_VIEWPORTS  : "desktop e mobile" | "só desktop" | "só mobile"
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

PAGES_PATH = Path("config/pages.yaml")

VIEWPORT_MAP = {
    "desktop e mobile": "[desktop, mobile]",
    "só desktop":       "[desktop]",
    "só mobile":        "[mobile]",
}


# ── Leitura preservando comentários ───────────────────────────────────────────

def _load_raw() -> str:
    if not PAGES_PATH.exists():
        raise SystemExit(f"Arquivo não encontrado: {PAGES_PATH}")
    return PAGES_PATH.read_text(encoding="utf-8")


def _parse_pages(raw: str) -> list[dict]:
    pages: list[dict] = []
    current: dict | None = None
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("- name:"):
            if current is not None:
                pages.append(current)
            current = {"name": _val(s, "name")}
        elif current is not None:
            for f in ("url", "active", "viewports", "lighthouse_skip"):
                if s.startswith(f"{f}:"):
                    current[f] = _val(s, f)
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


def _is_active(raw: str, url: str) -> bool:
    for p in _parse_pages(raw):
        if _url_eq(p.get("url", ""), url):
            return p.get("active", "true") != "false"
    return False


# ── Auto-nome ─────────────────────────────────────────────────────────────────

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
    in_target = replaced = False
    for line in lines:
        s = line.strip()
        if s.startswith("- name:"):
            in_target = replaced = False
        if f'url: "{url}"' in line or f"url: {url}" in line or f"url: '{url}'" in line:
            in_target = True
        if in_target and s.startswith("active:") and not replaced:
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
        if line.strip().startswith("- name:"):
            block = "".join(lines[i: i + 8])
            skip = (
                f'url: "{url}"' in block
                or f"url: {url}" in block
                or f"url: '{url}'" in block
            )
        if not skip:
            result.append(line)
    return "".join(result)


def _set_all_active(raw: str, active: bool) -> tuple[str, int]:
    val = "true" if active else "false"
    lines = raw.splitlines(keepends=True)
    result: list[str] = []
    changed = 0
    for line in lines:
        s = line.strip()
        if s.startswith("active:"):
            current = _val(s, "active")
            if current != val:
                indent = len(line) - len(line.lstrip())
                line = " " * indent + f"active: {val}\n"
                changed += 1
        result.append(line)
    return "".join(result), changed


def _add_page(raw: str, name: str, url: str, viewports_label: str) -> str:
    viewports = VIEWPORT_MAP.get(viewports_label, "[desktop, mobile]")
    block = (
        f'\n  - name: "{name}"\n'
        f'    url: "{url}"\n'
        f"    active: true\n"
        f"    viewports: {viewports}\n"
    )
    marker = "  # ── Páginas de campanha"
    return raw.replace(marker, block + marker, 1) if marker in raw else raw.rstrip() + "\n" + block


# ── Parse de múltiplas URLs (vírgula ou espaço como separador) ────────────────

def _parse_urls(raw: str) -> list[str]:
    urls: list[str] = []
    for part in re.split(r"[,\s]+", raw):
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
    add_raw        = os.environ.get("ADD_URLS",        "").strip()
    deactivate_raw = os.environ.get("DEACTIVATE_URLS", "").strip()
    remove_raw     = os.environ.get("REMOVE_URLS",     "").strip()
    viewports      = os.environ.get("PAGE_VIEWPORTS",  "desktop e mobile").strip()
    activate_all   = os.environ.get("ACTIVATE_ALL",   "").lower() in ("1", "true", "yes")
    deactivate_all = os.environ.get("DEACTIVATE_ALL", "").lower() in ("1", "true", "yes")

    add_urls        = _parse_urls(add_raw)
    deactivate_urls = _parse_urls(deactivate_raw)
    remove_urls     = _parse_urls(remove_raw)

    if not any([add_urls, deactivate_urls, remove_urls, activate_all, deactivate_all]):
        print("Erro: nenhuma URL informada. Preencha ao menos um dos campos.")
        sys.exit(1)

    raw = _load_raw()
    ok: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    if activate_all:
        raw, n = _set_all_active(raw, True)
        ok.append(f"  ✓ Todas as páginas ativadas ({n} alteração(ões)).")

    if deactivate_all:
        raw, n = _set_all_active(raw, False)
        ok.append(f"  ○ Todas as páginas desativadas ({n} alteração(ões)).")

    for url in add_urls:
        if _url_exists(raw, url):
            if not _is_active(raw, url):
                raw = _set_active(raw, url, True) or raw
                ok.append(f"  ↑ {url}  (reativada)")
            else:
                skipped.append(f"  ~ {url}  (já existe e está ativa, ignorada)")
        else:
            name = _auto_name(url)
            raw = _add_page(raw, name, url, viewports)
            ok.append(f"  + {url}  →  \"{name}\"")

    for url in deactivate_urls:
        result = _set_active(raw, url, active=False)
        if result is None:
            errors.append(f"  ✗ {url}  (não encontrada)")
        else:
            raw = result
            ok.append(f"  ○ {url}  (desativada)")

    for url in remove_urls:
        result = _remove_page(raw, url)
        if result is None:
            errors.append(f"  ✗ {url}  (não encontrada)")
        else:
            raw = result
            ok.append(f"  − {url}  (removida)")

    PAGES_PATH.write_text(raw, encoding="utf-8")

    print(f"\n{'═' * 52}")
    total = len(add_urls) + len(deactivate_urls) + len(remove_urls)
    print(f"  {total} URL(s) processada(s) | {len(ok)} ok | {len(errors)} erro(s)")
    print(f"{'═' * 52}")
    if ok:
        print("\nExecutado:")
        print("\n".join(ok))
    if skipped:
        print("\nIgnorado:")
        print("\n".join(skipped))
    if errors:
        print("\nErros:")
        print("\n".join(errors))
    print(f"\nSalvo: {PAGES_PATH}")

    if errors and not ok and not skipped:
        sys.exit(1)


if __name__ == "__main__":
    main()
