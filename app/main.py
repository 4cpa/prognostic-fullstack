from fastapi import FastAPI

from app.api.routes_backtesting import router as backtesting_router
from app.api.routes_forecasts import router as forecasts_router
from app.api.routes_questions import router as questions_router


app = FastAPI(title="Prognostic API")

app.include_router(questions_router)
app.include_router(forecasts_router)
app.include_router(backtesting_router)


@app.get("/health")
def health():
    return {"status": "ok"}
