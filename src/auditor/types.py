"""
Contratos de dados do Auditor.
Estas dataclasses são a fonte de verdade do que trafega entre os módulos.
Alterar campos aqui quebra storage e reporters — ver ARCHITECTURE.md seção 7.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


class Viewport(str, Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"


class CheckStatus(str, Enum):
    PASSOU = "passou"   # checagem executou; loja OK neste ponto
    FALHOU = "falhou"   # checagem executou; loja tem problema — investigar a loja
    ERRO = "erro"       # checagem não conseguiu executar — investigar o auditor/config


class AuditStatus(str, Enum):
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    FALHOU = "falhou"     # auditor crashou; resultado da loja desconhecido
    CANCELADA = "cancelada"


class AuditResultado(str, Enum):
    TUDO_OK = "tudo_ok"
    COM_FALHAS = "com_falhas"


class TriggerMode(str, Enum):
    MANUAL = "manual"
    AGENDADO = "agendado"


class Categoria(str, Enum):
    FLUXO = "fluxo"
    SAUDE_TECNICA = "saude_tecnica"


@dataclass
class CheckResult:
    check_id: str           # identificador estável para comparação histórica (ex: 'http_status')
    check_name: str         # nome legível (ex: 'Status HTTP — Home')
    categoria: Categoria
    viewport: Viewport
    status: CheckStatus
    page_url: Optional[str] = None    # URL absoluta se categoria = saude_tecnica
    flow_name: Optional[str] = None   # nome do fluxo se categoria = fluxo
    detail: Optional[str] = None      # detalhe técnico; obrigatório quando status != passou
    value: Optional[float] = None     # valor numérico da métrica (ex: 2340)
    unit: Optional[str] = None        # unidade: 'ms', 'count', 'score'
    threshold: Optional[float] = None # limiar usado (preservado para comparação futura)
    duration_ms: Optional[int] = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Campos de evidência — preenchidos durante a execução; screenshot_b64 não vai pro SQLite
    screenshot_path: Optional[str] = None  # caminho relativo a reports_dir (ex: screenshots/run_id/lcp_desktop.png)
    screenshot_b64: Optional[str] = None   # PNG em base64; embutido no relatório HTML; NÃO persistido
    explanation: Optional[str] = None      # explicação em linguagem de negócio da falha

    def __post_init__(self) -> None:
        if self.page_url is None and self.flow_name is None:
            raise ValueError(
                f"CheckResult '{self.check_id}': page_url ou flow_name deve ser informado"
            )
        if self.status != CheckStatus.PASSOU and self.detail is None:
            raise ValueError(
                f"CheckResult '{self.check_id}' com status '{self.status}' "
                "deve ter 'detail' preenchido"
            )


@dataclass
class AuditRun:
    """
    Eixo 1 (status): saúde do job do auditor.
    Eixo 2 (resultado): saúde da loja. Só preenchido quando status = CONCLUIDA.
    Ver CLAUDE.md R9 — nunca colapsar os dois em um campo único.
    """
    trigger: TriggerMode
    config_version: str       # MD5 do audit-config.yaml — garante reprodutibilidade
    run_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: AuditStatus = AuditStatus.EM_ANDAMENTO
    resultado: Optional[AuditResultado] = None
    finished_at: Optional[datetime] = None
    execution_error: Optional[str] = None   # detalhe técnico se status = FALHOU
    check_results: list[CheckResult] = field(default_factory=list)

    @property
    def total_checks(self) -> int:
        return len(self.check_results)

    @property
    def total_passou(self) -> int:
        return sum(1 for r in self.check_results if r.status == CheckStatus.PASSOU)

    @property
    def total_falhou(self) -> int:
        return sum(1 for r in self.check_results if r.status == CheckStatus.FALHOU)

    @property
    def total_erro(self) -> int:
        return sum(1 for r in self.check_results if r.status == CheckStatus.ERRO)

    def finalizar(self) -> None:
        """Marca a execução como concluída e deriva o resultado da loja."""
        self.finished_at = datetime.now(timezone.utc)
        self.status = AuditStatus.CONCLUIDA
        self.resultado = (
            AuditResultado.TUDO_OK
            if self.total_falhou == 0
            else AuditResultado.COM_FALHAS
        )

    def marcar_falha(self, error: str) -> None:
        """Marca o auditor como falho (job quebrou — nada se sabe da loja)."""
        self.finished_at = datetime.now(timezone.utc)
        self.status = AuditStatus.FALHOU
        self.resultado = None
        self.execution_error = error
