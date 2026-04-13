import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import app.core.logger  # noqa: F401 — initialisiert Logging beim Import
from app.core.logger import get_logger
from app.api.routes_backtesting import router as backtesting_router
from app.api.routes_forecasts import router as forecasts_router
from app.api.routes_questions import router as questions_router

log = get_logger("api")

app = FastAPI(title="Prognostic API")

# --- Prometheus-Metriken ---
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, include_in_schema=False)
except ImportError:
    log.warning("prometheus-fastapi-instrumentator nicht installiert — /metrics deaktiviert")


@app.middleware("http")
async def _request_log(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        log.error(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    ms = round((time.perf_counter() - start) * 1000)
    level = logging.WARNING if response.status_code >= 400 else logging.INFO
    log.log(
        level,
        "%s %s → %s (%dms)",
        request.method,
        request.url.path,
        response.status_code,
        ms,
    )
    return response


app.include_router(questions_router)
app.include_router(forecasts_router)
app.include_router(backtesting_router)


@app.get("/health")
def health():
    return {"status": "ok"}
