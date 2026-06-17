"""
Modelos Pydantic do audit-config.yaml.
Cada campo mapeia diretamente para uma chave do YAML.
'extra=forbid' garante que typos no config viram erro imediato, não silêncio.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ViewportConfig(str, Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"


class RunMode(str, Enum):
    ALWAYS = "always"
    MANUAL_ONLY = "manual_only"


class ActionType(str, Enum):
    GOTO = "goto"
    CLICK = "click"
    FILL = "fill"
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_NOT_VISIBLE = "assert_not_visible"
    WAIT = "wait"


class ExpectType(str, Enum):
    URL_CONTAINS = "url_contains"
    ELEMENT_VISIBLE = "element_visible"
    ELEMENT_CLICKABLE = "element_clickable"


class StepExpect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ExpectType
    value: Optional[str] = None     # para url_contains
    selector: Optional[str] = None  # para element_visible / element_clickable

    @field_validator("value", "selector", mode="after")
    @classmethod
    def check_has_target(cls, v: Optional[str], info: object) -> Optional[str]:
        return v


class FlowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    action: ActionType
    value: Optional[str] = None     # para goto e fill
    selector: Optional[str] = None  # para click, assert_visible, assert_not_visible
    expect: Optional[StepExpect] = None
    wait_ms: Optional[int] = None   # espera explícita em ms (ex: verificar que popup NÃO aparece)

    @field_validator("selector", mode="after")
    @classmethod
    def selector_required_for_click(cls, v: Optional[str], info: object) -> Optional[str]:
        return v


class Flow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    viewports: list[ViewportConfig]
    steps: list[FlowStep]
    abort_on_failure: bool = True
    active: bool = True
    run_mode: RunMode = RunMode.ALWAYS

    @field_validator("steps", mode="after")
    @classmethod
    def steps_nao_vazios(cls, v: list[FlowStep]) -> list[FlowStep]:
        if not v:
            raise ValueError("Fluxo deve ter ao menos um step")
        return v


class CriticalPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    url: str    # relativo ao base_url
    viewports: list[ViewportConfig] = [ViewportConfig.DESKTOP, ViewportConfig.MOBILE]
    active: bool = True
    lighthouse_skip: bool = False   # true para checkout.shopify.com (limitação Lighthouse)


class PopupChecks(BaseModel):
    """Flags de quais aspectos do popup verificar."""
    model_config = ConfigDict(extra="allow")

    dispara_apos_delay: bool = True
    botao_fechar_visivel: bool = True
    fechar_funciona: bool = True
    nao_bloqueia_scroll: bool = True
    nao_bloqueia_clique: bool = True
    nao_dispara_no_checkout: bool = True
    nao_dispara_loop: bool = True


class PopupConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    trigger: str                         # "page_load"
    trigger_page: str                    # "/" — URL onde o popup dispara
    container_selector: str
    close_selector: str
    email_field_selector: Optional[str] = None
    phone_field_selector: Optional[str] = None
    cta_selector: Optional[str] = None
    viewports: list[ViewportConfig] = [ViewportConfig.DESKTOP, ViewportConfig.MOBILE]
    active: bool = True
    checks: Optional[list[dict[str, bool]]] = None  # lista de flags do playbook


class Timeouts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    navigation: Annotated[int, Field(gt=0)] = 30000
    element: Annotated[int, Field(gt=0)] = 5000
    popup_delay: Annotated[int, Field(gt=0)] = 4500


class Thresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    load_time_ms: Annotated[float, Field(gt=0)] = 5000.0
    lcp_ms: Annotated[float, Field(gt=0)] = 4000.0
    fid_ms: Annotated[float, Field(gt=0)] = 300.0
    cls: Annotated[float, Field(gt=0)] = 0.25


class StoreConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str
    name: str

    @field_validator("base_url", mode="after")
    @classmethod
    def remove_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


class AuditConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store: StoreConfig
    timeouts: Timeouts = Field(default_factory=Timeouts)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    critical_pages: list[CriticalPage]
    popups: list[PopupConfig] = Field(default_factory=list)
    flows: list[Flow] = Field(default_factory=list)

    def active_pages(self) -> list[CriticalPage]:
        return [p for p in self.critical_pages if p.active]

    def active_flows(self, include_manual_only: bool = False) -> list[Flow]:
        flows = [f for f in self.flows if f.active]
        if not include_manual_only:
            flows = [f for f in flows if f.run_mode != RunMode.MANUAL_ONLY]
        return flows

    def active_popups(self) -> list[PopupConfig]:
        return [p for p in self.popups if p.active]

    def absolute_url(self, relative_url: str) -> str:
        """Constrói URL absoluta a partir de URL relativa do config."""
        return self.store.base_url + relative_url
