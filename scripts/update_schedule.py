#!/usr/bin/env python3
"""
Atualiza a agenda de auditorias em .github/workflows/audit.yml
e registra o estado legível em config/schedule.yaml.

Variáveis de ambiente:
  INPUT_DIAS : opção de dias (veja DIAS_TO_CRON_PART abaixo)
  INPUT_HORA : horário BRT no formato "HH:MM" (ex: "09:00")
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
AUDIT_YML  = ROOT / ".github" / "workflows" / "audit.yml"
SCHED_YAML = ROOT / "config" / "schedule.yaml"

DIAS_TO_CRON_PART: dict[str, str | None] = {
    "Dias úteis (seg–sex)":     "1-5",
    "Dias úteis + sábado":      "1-6",
    "Todos os dias":            "*",
    "Apenas fins de semana":    "0,6",
    "Desativado (não agendar)": None,
}


def hora_brt_to_utc_hour(hora_brt: str) -> int:
    """Converte 'HH:MM' BRT (UTC-3) para hora UTC."""
    h = int(hora_brt.split(":")[0])
    return (h + 3) % 24


def update_audit_yml(cron: str | None, dias: str, hora: str, utc_h: int) -> None:
    content = AUDIT_YML.read_text(encoding="utf-8")

    if cron is None:
        # Remove o bloco 'schedule' inteiro; 'workflow_dispatch' permanece
        content = re.sub(
            r"  schedule:\n    - cron: \"[^\"\n]*\"[^\n]*\n",
            "",
            content,
        )
    else:
        new_line = f'    - cron: "{cron}"   # {hora} BRT (UTC {utc_h:02d}h), {dias}'
        if "schedule:" in content:
            content = re.sub(
                r"    - cron: \"[^\"\n]*\"[^\n]*",
                new_line,
                content,
            )
        else:
            # Reinsere bloco schedule antes de workflow_dispatch
            content = content.replace(
                "  workflow_dispatch:",
                f"  schedule:\n{new_line}\n  workflow_dispatch:",
            )

    AUDIT_YML.write_text(content, encoding="utf-8")


def update_schedule_yaml(dias: str, hora: str, cron: str | None) -> None:
    cron_str = f'"{cron}"' if cron else "null"
    SCHED_YAML.write_text(
        f'dias: "{dias}"\nhora: "{hora}"\ncron: {cron_str}\n',
        encoding="utf-8",
    )


def main() -> None:
    dias = os.environ.get("INPUT_DIAS", "Dias úteis (seg–sex)")
    hora = os.environ.get("INPUT_HORA", "09:00")

    if dias not in DIAS_TO_CRON_PART:
        print(f"Erro: opção de dias inválida: '{dias}'", file=sys.stderr)
        sys.exit(1)

    days_part = DIAS_TO_CRON_PART[dias]
    if days_part is not None:
        utc_h = hora_brt_to_utc_hour(hora)
        cron: str | None = f"0 {utc_h} * * {days_part}"
    else:
        utc_h = 0
        cron = None

    update_audit_yml(cron, dias, hora, utc_h)
    update_schedule_yaml(dias, hora, cron)

    if cron:
        print(f"Agenda atualizada: {dias} as {hora} BRT -> cron: {cron}")
    else:
        print("Agendamento automático desativado.")


if __name__ == "__main__":
    main()
