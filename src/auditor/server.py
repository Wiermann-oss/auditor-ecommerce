"""
Servidor web do dashboard de auditoria.
Roda localmente em http://localhost:8000
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .config.loader import ConfigError, load_config
from .config.models import AuditConfig
from .engine import DEFAULT_REPORTS_DIR, run_audit
from .storage.history import DEFAULT_DB_PATH, get_recent_runs, get_run_by_id
from .types import TriggerMode

log = logging.getLogger(__name__)

_DIR = Path(__file__).parent
_TEMPLATES_DIR = _DIR / "web" / "templates"
_STATIC_DIR = _DIR / "web" / "static"
_CONFIG_DIR = Path("config")
_OVERRIDES_PATH = _CONFIG_DIR / "overrides.json"
_SCHEDULE_PATH = _CONFIG_DIR / "schedule.json"
_GA4_CONFIG_PATH = _CONFIG_DIR / "ga4.json"

app = FastAPI(title="Auditor Minimal Club", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


# ── Estado global ─────────────────────────────────────────────────────────────

class _State:
    is_running: bool = False
    current_run_id: Optional[str] = None
    last_run_id: Optional[str] = None
    last_error: Optional[str] = None
    started_at: Optional[str] = None

_state = _State()
_scheduler = None


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def _startup() -> None:
    global _scheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    _scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")
    _scheduler.start()
    _apply_saved_schedule()
    log.info("Dashboard disponível em http://localhost:8000")


@app.on_event("shutdown")
async def _shutdown() -> None:
    if _scheduler:
        _scheduler.shutdown(wait=False)


# ── Páginas ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/reports/{filename}")
async def serve_report(filename: str) -> FileResponse:
    path = DEFAULT_REPORTS_DIR / filename
    if not path.exists() or path.suffix not in (".html", ".json"):
        raise HTTPException(404, "Relatório não encontrado")
    return FileResponse(path)


# ── API: status ───────────────────────────────────────────────────────────────

@app.get("/api/status")
async def api_status() -> dict:
    return {
        "is_running": _state.is_running,
        "current_run_id": _state.current_run_id,
        "last_run_id": _state.last_run_id,
        "last_error": _state.last_error,
        "started_at": _state.started_at,
    }


# ── API: run ──────────────────────────────────────────────────────────────────

@app.post("/api/run")
async def api_run() -> dict:
    if _state.is_running:
        raise HTTPException(409, "Auditoria já em andamento")
    asyncio.create_task(_run_audit_task(TriggerMode.MANUAL))
    return {"started": True}


async def _run_audit_task(trigger: TriggerMode = TriggerMode.AGENDADO) -> None:
    _state.is_running = True
    _state.last_error = None
    _state.started_at = datetime.now(timezone.utc).isoformat()
    _state.current_run_id = None
    try:
        config, config_version = load_config()
        overrides = _load_json(_OVERRIDES_PATH)
        config = _apply_overrides(config, overrides)
        run = await run_audit(config, config_version, trigger=trigger)
        _state.last_run_id = run.run_id
    except Exception as exc:
        _state.last_error = str(exc)
        log.error("Audit task falhou: %s", exc)
    finally:
        _state.is_running = False
        _state.started_at = None
        _state.current_run_id = None


# ── API: config ───────────────────────────────────────────────────────────────

@app.get("/api/config")
async def api_get_config() -> dict:
    try:
        config, _ = load_config()
    except ConfigError as exc:
        raise HTTPException(500, str(exc))

    overrides = _load_json(_OVERRIDES_PATH)
    page_ov = overrides.get("pages", {})
    flow_ov = overrides.get("flows", {})
    url_filter = overrides.get("url_filter", "")

    return {
        "store": {"name": config.store.name, "base_url": config.store.base_url},
        "url_filter": url_filter,
        "pages": [
            {
                "name": p.name,
                "url": p.url,
                "viewports": [v.value for v in p.viewports],
                "active": page_ov.get(p.name, {}).get("active", p.active),
                "lighthouse_skip": p.lighthouse_skip,
            }
            for p in config.critical_pages
        ],
        "flows": [
            {
                "id": f.id,
                "name": f.name,
                "viewports": [v.value for v in f.viewports],
                "active": flow_ov.get(f.id, {}).get("active", f.active),
                "run_mode": f.run_mode.value,
            }
            for f in config.flows
        ],
    }


class _ToggleBody(BaseModel):
    active: bool


@app.post("/api/config/pages/{name}/active")
async def api_toggle_page(name: str, body: _ToggleBody) -> dict:
    overrides = _load_json(_OVERRIDES_PATH)
    overrides.setdefault("pages", {})[name] = {"active": body.active}
    _save_json(_OVERRIDES_PATH, overrides)
    return {"ok": True}


@app.post("/api/config/flows/{flow_id}/active")
async def api_toggle_flow(flow_id: str, body: _ToggleBody) -> dict:
    overrides = _load_json(_OVERRIDES_PATH)
    overrides.setdefault("flows", {})[flow_id] = {"active": body.active}
    _save_json(_OVERRIDES_PATH, overrides)
    return {"ok": True}


class _UrlFilterBody(BaseModel):
    url_filter: str


@app.post("/api/config/url-filter")
async def api_set_url_filter(body: _UrlFilterBody) -> dict:
    overrides = _load_json(_OVERRIDES_PATH)
    overrides["url_filter"] = body.url_filter.strip()
    _save_json(_OVERRIDES_PATH, overrides)
    return {"ok": True}


# ── API: schedule ─────────────────────────────────────────────────────────────

class _ScheduleBody(BaseModel):
    enabled: bool
    time: str        # "HH:MM"
    days: list[int]  # 0=Seg … 6=Dom


@app.get("/api/schedule")
async def api_get_schedule() -> dict:
    return _load_schedule()


@app.post("/api/schedule")
async def api_save_schedule(body: _ScheduleBody) -> dict:
    _save_json(_SCHEDULE_PATH, body.model_dump())
    _apply_saved_schedule()
    return {"ok": True}


# ── API: runs ─────────────────────────────────────────────────────────────────

@app.get("/api/runs")
async def api_list_runs(limit: int = 50) -> list:
    return get_recent_runs(limit=limit)


@app.get("/api/runs/{run_id}/report", response_class=HTMLResponse)
async def api_run_report(run_id: str) -> HTMLResponse:
    run = get_run_by_id(run_id)
    if not run:
        raise HTTPException(404, "Run não encontrado")
    filename = run.started_at.strftime("%Y-%m-%dT%H-%M-%S") + ".html"
    path = DEFAULT_REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Arquivo de relatório não encontrado: {filename}")
    return HTMLResponse(path.read_text(encoding="utf-8"))


# ── API: dashboard ────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
async def api_dashboard() -> dict:
    runs = get_recent_runs(limit=100)
    completed = [r for r in runs if r.get("status") == "concluida"]

    # Tendência: últimas 10 execuções concluídas
    trend = [
        {
            "date": (r.get("started_at") or "")[:10],
            "pass_rate": (
                round(r["total_passou"] / r["total_checks"] * 100)
                if r.get("total_checks") and r["total_checks"] > 0
                else 0
            ),
            "total_falhou": r.get("total_falhou") or 0,
            "run_id": r.get("run_id"),
        }
        for r in list(reversed(completed))[:10]
    ]

    # Top falhas (das últimas 20 execuções concluídas)
    failure_counts: dict[str, int] = defaultdict(int)
    for run_row in completed[:20]:
        run_obj = get_run_by_id(run_row["run_id"])
        if run_obj:
            for cr in run_obj.check_results:
                if cr.status.value == "falhou":
                    failure_counts[cr.check_name] += 1

    top_failures = sorted(
        [{"check_name": k, "count": v} for k, v in failure_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    # Stats gerais
    avg_pass_rate = 0
    if completed:
        rates = [
            r["total_passou"] / r["total_checks"] * 100
            for r in completed
            if r.get("total_checks") and r["total_checks"] > 0
        ]
        avg_pass_rate = round(sum(rates) / len(rates)) if rates else 0

    last = completed[0] if completed else None
    return {
        "total_runs": len(runs),
        "avg_pass_rate": avg_pass_rate,
        "last_run_date": (last.get("started_at") or "")[:16].replace("T", " ") if last else "—",
        "recent_failures": sum(r.get("total_falhou") or 0 for r in completed[:5]),
        "trend": trend,
        "top_failures": top_failures,
    }


# ── API: GA4 ──────────────────────────────────────────────────────────────────

class _GA4ConfigBody(BaseModel):
    property_id: str
    credentials_path: str


@app.get("/api/ga4/config")
async def api_ga4_get_config() -> dict:
    cfg = _load_json(_GA4_CONFIG_PATH)
    return {
        "property_id": cfg.get("property_id", ""),
        "credentials_path": cfg.get("credentials_path", ""),
        "configured": bool(cfg.get("property_id") and cfg.get("credentials_path")),
    }


@app.post("/api/ga4/config")
async def api_ga4_save_config(body: _GA4ConfigBody) -> dict:
    _save_json(_GA4_CONFIG_PATH, body.model_dump())
    return {"ok": True}


@app.get("/api/ga4/pages")
async def api_ga4_pages() -> dict:
    cfg = _load_json(_GA4_CONFIG_PATH)
    if not cfg.get("property_id") or not cfg.get("credentials_path"):
        raise HTTPException(400, "GA4 não configurado")

    try:
        from .ga4_client import get_top_pages
    except ImportError:
        raise HTTPException(
            501,
            "Instale: pip install google-analytics-data",
        )

    try:
        pages = await asyncio.get_event_loop().run_in_executor(
            None, get_top_pages, cfg["property_id"], cfg["credentials_path"]
        )
    except Exception as exc:
        raise HTTPException(500, f"Erro ao consultar GA4: {exc}")

    # Marcar quais já estão no config
    try:
        audit_config, _ = load_config()
        audit_urls = {p.url for p in audit_config.critical_pages}
    except Exception:
        audit_urls = set()

    for p in pages:
        p["in_audit"] = p["path"] in audit_urls

    return {"pages": pages}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_schedule() -> dict:
    saved = _load_json(_SCHEDULE_PATH)
    return {
        "enabled": saved.get("enabled", False),
        "time": saved.get("time", "09:00"),
        "days": saved.get("days", [0, 1, 2, 3, 4]),
    }


def _apply_saved_schedule() -> None:
    if _scheduler is None:
        return
    job_id = "scheduled_audit"
    try:
        _scheduler.remove_job(job_id)
    except Exception:
        pass

    schedule = _load_schedule()
    if not schedule["enabled"]:
        return

    hour, minute = map(int, schedule["time"].split(":"))
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_str = ",".join(day_names[d] for d in schedule["days"] if 0 <= d <= 6)
    if not day_str:
        return

    _scheduler.add_job(
        _run_audit_task,
        "cron",
        id=job_id,
        hour=hour,
        minute=minute,
        day_of_week=day_str,
        replace_existing=True,
    )
    log.info("Agendamento ativo: %s às %s", day_str, schedule["time"])


def _apply_overrides(config: AuditConfig, overrides: dict) -> AuditConfig:
    """Retorna cópia da config com overrides de active aplicados."""
    data = config.model_dump()
    page_ov = overrides.get("pages", {})
    flow_ov = overrides.get("flows", {})
    url_filter = overrides.get("url_filter", "").strip()

    for page in data["critical_pages"]:
        if page["name"] in page_ov:
            page["active"] = page_ov[page["name"]].get("active", page["active"])
        if url_filter and url_filter not in page["url"]:
            page["active"] = False

    for flow in data["flows"]:
        if flow["id"] in flow_ov:
            flow["active"] = flow_ov[flow["id"]].get("active", flow["active"])

    return AuditConfig.model_validate(data)
