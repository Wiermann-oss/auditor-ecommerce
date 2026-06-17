"""
Persistência do histórico de auditorias em SQLite.
O banco é append-only: AuditRun e CheckResult são imutáveis após criação.
Nunca fazer DELETE ou UPDATE em registros passados — ver CLAUDE.md R8.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator, Optional

from ..types import (
    AuditResultado,
    AuditRun,
    AuditStatus,
    Categoria,
    CheckResult,
    CheckStatus,
    TriggerMode,
    Viewport,
)

DEFAULT_DB_PATH = Path("auditor-history.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_runs (
    run_id          TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL,
    resultado       TEXT,
    trigger         TEXT NOT NULL,
    config_version  TEXT NOT NULL,
    execution_error TEXT,
    total_checks    INTEGER,
    total_passou    INTEGER,
    total_falhou    INTEGER,
    total_erro      INTEGER
);

CREATE TABLE IF NOT EXISTS check_results (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL REFERENCES audit_runs(run_id),
    check_id    TEXT NOT NULL,
    check_name  TEXT NOT NULL,
    categoria   TEXT NOT NULL,
    page_url    TEXT,
    flow_name   TEXT,
    viewport    TEXT NOT NULL,
    status      TEXT NOT NULL,
    detail      TEXT,
    value       REAL,
    unit        TEXT,
    threshold   REAL,
    duration_ms INTEGER,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cr_run_id       ON check_results(run_id);
CREATE INDEX IF NOT EXISTS idx_cr_check_status ON check_results(check_id, status);
CREATE INDEX IF NOT EXISTS idx_cr_page_check   ON check_results(page_url, check_id);
CREATE INDEX IF NOT EXISTS idx_runs_started    ON audit_runs(started_at);
"""


@contextmanager
def _connect(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Cria as tabelas se não existirem. Seguro de chamar múltiplas vezes."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def save_run(run: AuditRun, db_path: Path = DEFAULT_DB_PATH) -> None:
    """
    Insere ou atualiza um AuditRun no banco.
    Upsert por run_id — permite salvar o run no início (em_andamento)
    e atualizá-lo ao final (concluida/falhou).
    """
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO audit_runs
                (run_id, started_at, finished_at, status, resultado, trigger,
                 config_version, execution_error,
                 total_checks, total_passou, total_falhou, total_erro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                finished_at     = excluded.finished_at,
                status          = excluded.status,
                resultado       = excluded.resultado,
                execution_error = excluded.execution_error,
                total_checks    = excluded.total_checks,
                total_passou    = excluded.total_passou,
                total_falhou    = excluded.total_falhou,
                total_erro      = excluded.total_erro
            """,
            (
                run.run_id,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at else None,
                run.status.value,
                run.resultado.value if run.resultado else None,
                run.trigger.value,
                run.config_version,
                run.execution_error,
                run.total_checks if run.status == AuditStatus.CONCLUIDA else None,
                run.total_passou if run.status == AuditStatus.CONCLUIDA else None,
                run.total_falhou if run.status == AuditStatus.CONCLUIDA else None,
                run.total_erro if run.status == AuditStatus.CONCLUIDA else None,
            ),
        )
        _upsert_check_results(conn, run.run_id, run.check_results)


def _upsert_check_results(
    conn: sqlite3.Connection, run_id: str, results: list[CheckResult]
) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO check_results
            (id, run_id, check_id, check_name, categoria,
             page_url, flow_name, viewport, status, detail,
             value, unit, threshold, duration_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r.id,
                run_id,
                r.check_id,
                r.check_name,
                r.categoria.value,
                r.page_url,
                r.flow_name,
                r.viewport.value,
                r.status.value,
                r.detail,
                r.value,
                r.unit,
                r.threshold,
                r.duration_ms,
                r.created_at.isoformat(),
            )
            for r in results
        ],
    )


def get_recent_runs(
    limit: int = 10,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict]:
    """
    Retorna os N runs mais recentes como dicts simples (sem check_results).
    Usado para listagem rápida no CLI.
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT run_id, started_at, finished_at, status, resultado,
                   trigger, config_version, total_checks, total_passou, total_falhou, total_erro
            FROM audit_runs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_run_by_id(run_id: str, db_path: Path = DEFAULT_DB_PATH) -> Optional[AuditRun]:
    """Carrega um AuditRun completo com todos os CheckResult."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM audit_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None

        cr_rows = conn.execute(
            "SELECT * FROM check_results WHERE run_id = ? ORDER BY created_at",
            (run_id,),
        ).fetchall()

    run = _row_to_audit_run(dict(row))
    run.check_results = [_row_to_check_result(dict(r)) for r in cr_rows]
    return run


def get_diff(
    since_days: int = 7,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    """
    Compara o último run concluído com todos os runs anteriores no período.
    Retorna regressões (passou→falhou), recuperações (falhou→passou) e run ids.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()

    with _connect(db_path) as conn:
        run_ids = [
            r["run_id"]
            for r in conn.execute(
                """
                SELECT run_id FROM audit_runs
                WHERE status = 'concluida' AND started_at >= ?
                ORDER BY started_at ASC
                """,
                (cutoff,),
            ).fetchall()
        ]

    if len(run_ids) < 2:
        return {
            "error": f"Menos de 2 execuções concluídas nos últimos {since_days} dias. "
                     "Não há histórico suficiente para comparar."
        }

    latest_id = run_ids[-1]
    previous_ids = run_ids[:-1]

    with _connect(db_path) as conn:
        latest = {
            (r["check_id"], r["page_url"], r["flow_name"], r["viewport"]): r["status"]
            for r in conn.execute(
                "SELECT check_id, page_url, flow_name, viewport, status "
                "FROM check_results WHERE run_id = ?",
                (latest_id,),
            ).fetchall()
        }

        previous_statuses: dict[tuple, set[str]] = {}
        for prev_id in previous_ids:
            for r in conn.execute(
                "SELECT check_id, page_url, flow_name, viewport, status "
                "FROM check_results WHERE run_id = ?",
                (prev_id,),
            ).fetchall():
                key = (r["check_id"], r["page_url"], r["flow_name"], r["viewport"])
                previous_statuses.setdefault(key, set()).add(r["status"])

    regressoes = []
    recuperacoes = []
    novidades = []

    for key, status_atual in latest.items():
        check_id, page_url, flow_name, viewport = key
        base = {
            "check_id": check_id,
            "page_url": page_url,
            "flow_name": flow_name,
            "viewport": viewport,
        }
        if key not in previous_statuses:
            novidades.append(base)
            continue
        prev = previous_statuses[key]
        if status_atual == "falhou" and "passou" in prev:
            regressoes.append(base)
        elif status_atual == "passou" and "falhou" in prev:
            recuperacoes.append(base)

    return {
        "periodo_dias": since_days,
        "runs_analisados": len(run_ids),
        "run_atual": latest_id,
        "regressoes": regressoes,
        "recuperacoes": recuperacoes,
        "novidades": novidades,
    }


def _row_to_audit_run(row: dict) -> AuditRun:
    run = AuditRun(
        trigger=TriggerMode(row["trigger"]),
        config_version=row["config_version"],
    )
    run.run_id = row["run_id"]
    run.started_at = datetime.fromisoformat(row["started_at"])
    run.status = AuditStatus(row["status"])
    run.resultado = AuditResultado(row["resultado"]) if row["resultado"] else None
    run.finished_at = (
        datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None
    )
    run.execution_error = row["execution_error"]
    return run


def _row_to_check_result(row: dict) -> CheckResult:
    return CheckResult(
        check_id=row["check_id"],
        check_name=row["check_name"],
        categoria=Categoria(row["categoria"]),
        viewport=Viewport(row["viewport"]),
        status=CheckStatus(row["status"]),
        page_url=row["page_url"],
        flow_name=row["flow_name"],
        detail=row["detail"],
        value=row["value"],
        unit=row["unit"],
        threshold=row["threshold"],
        duration_ms=row["duration_ms"],
        id=row["id"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
