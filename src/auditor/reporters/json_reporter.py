"""
Serializa um AuditRun completo para JSON.
Formato estável — breaking changes exigem bumpar a versão do schema.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..types import AuditRun


def generate_json_report(run: AuditRun, reports_dir: Path) -> Path:
    """Grava report JSON em reports_dir e retorna o caminho do arquivo."""
    import json

    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / (_run_filename(run.started_at) + ".json")
    path.write_text(
        json.dumps(_serialize_run(run), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _run_filename(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H-%M-%S")


def _serialize_run(run: AuditRun) -> dict:
    return {
        "run_id": run.run_id,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "status": run.status.value,
        "resultado": run.resultado.value if run.resultado else None,
        "trigger": run.trigger.value,
        "config_version": run.config_version,
        "execution_error": run.execution_error,
        "total_checks": run.total_checks,
        "total_passou": run.total_passou,
        "total_falhou": run.total_falhou,
        "total_erro": run.total_erro,
        "check_results": [
            {
                "id": r.id,
                "check_id": r.check_id,
                "check_name": r.check_name,
                "categoria": r.categoria.value,
                "page_url": r.page_url,
                "flow_name": r.flow_name,
                "viewport": r.viewport.value,
                "status": r.status.value,
                "detail": r.detail,
                "value": r.value,
                "unit": r.unit,
                "threshold": r.threshold,
                "duration_ms": r.duration_ms,
                "created_at": r.created_at.isoformat(),
            }
            for r in run.check_results
        ],
    }
