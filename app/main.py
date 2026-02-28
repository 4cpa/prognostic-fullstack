from fastapi import FastAPI
from app.api.routes_questions import router as questions_router
from app.api.routes_forecasts import router as forecasts_router

app = FastAPI(title="4CPA Prognostic API", version="0.1.0")

app.include_router(questions_router)
app.include_router(forecasts_router)

@app.get("/health")
def health():
    return {"status": "ok"}
