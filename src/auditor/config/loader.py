"""
Carrega e valida o audit-config.yaml.
Produz config_version (MD5 do conteúdo) para rastreabilidade do histórico.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import AuditConfig

DEFAULT_CONFIG_PATH = Path("config/audit-config.yaml")
DEFAULT_PAGES_PATH = Path("config/pages.yaml")


class ConfigError(Exception):
    """Erro de leitura ou validação do audit-config.yaml."""


def load_config(
    path: Path = DEFAULT_CONFIG_PATH,
    pages_path: Path = DEFAULT_PAGES_PATH,
) -> tuple[AuditConfig, str]:
    """
    Carrega o YAML e valida com Pydantic.
    Se config/pages.yaml existir, substitui critical_pages do audit-config.yaml.
    Retorna (AuditConfig, config_version).
    """
    if not path.exists():
        raise ConfigError(
            f"Arquivo de config não encontrado: {path}\n"
            "Certifique-se de rodar o auditor a partir da raiz do projeto."
        )

    raw_content = path.read_text(encoding="utf-8")
    config_version = hashlib.md5(raw_content.encode()).hexdigest()[:8]

    try:
        data = yaml.safe_load(raw_content)
    except yaml.YAMLError as e:
        raise ConfigError(f"Erro de sintaxe no YAML ({path}): {e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"Config inválido: esperado um mapa YAML, recebido {type(data).__name__}")

    if pages_path.exists():
        data = _merge_pages(data, pages_path)

    try:
        config = AuditConfig.model_validate(data)
    except ValidationError as e:
        erros = _formatar_erros_pydantic(e)
        raise ConfigError(
            f"Erros de validação no config ({path}):\n{erros}"
        ) from e

    return config, config_version


def _merge_pages(data: dict, pages_path: Path) -> dict:
    """Substitui critical_pages com o conteúdo de pages.yaml."""
    try:
        pages_raw = pages_path.read_text(encoding="utf-8")
        pages_data = yaml.safe_load(pages_raw)
    except yaml.YAMLError as e:
        raise ConfigError(f"Erro de sintaxe em {pages_path}: {e}") from e

    if not isinstance(pages_data, dict) or "pages" not in pages_data:
        return data

    data = dict(data)
    data["critical_pages"] = pages_data["pages"]
    return data


def _formatar_erros_pydantic(e: ValidationError) -> str:
    linhas = []
    for erro in e.errors():
        campo = " → ".join(str(loc) for loc in erro["loc"])
        mensagem = erro["msg"]
        linhas.append(f"  • {campo}: {mensagem}")
    return "\n".join(linhas)
