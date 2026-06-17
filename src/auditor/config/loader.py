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


class ConfigError(Exception):
    """Erro de leitura ou validação do audit-config.yaml."""


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> tuple[AuditConfig, str]:
    """
    Carrega o YAML e valida com Pydantic.
    Retorna (AuditConfig, config_version).
    config_version é o MD5 do conteúdo — usado como chave de reprodutibilidade no histórico.
    Lança ConfigError com mensagem legível se o arquivo não existir ou for inválido.
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

    try:
        config = AuditConfig.model_validate(data)
    except ValidationError as e:
        erros = _formatar_erros_pydantic(e)
        raise ConfigError(
            f"Erros de validação no config ({path}):\n{erros}"
        ) from e

    return config, config_version


def _formatar_erros_pydantic(e: ValidationError) -> str:
    linhas = []
    for erro in e.errors():
        campo = " → ".join(str(loc) for loc in erro["loc"])
        mensagem = erro["msg"]
        linhas.append(f"  • {campo}: {mensagem}")
    return "\n".join(linhas)
