from typing import List
from datetime import datetime
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.question import Question
from app.models.evidence import EvidenceItem
from app.models.forecast import Forecast, ForecastRead


router = APIRouter(prefix="/questions", tags=["forecasts"])


# -----------------------------
# Simple MVP Bayesian Log-Odds
# -----------------------------

BASE_RATES = {
    "politics": 0.30,
    "economy": 0.40,
    "technology": 0.50,
    "security": 0.35,
}


def logit(p: float) -> float:
    import math
    return math.log(p / (1 - p))


def inv_logit(x: float) -> float:
    import math
    return 1 / (1 + math.exp(-x))


# -----------------------------
# Create Forecast
# -----------------------------

@router.post("/{question_id}/forecast", response_model=ForecastRead)
def create_forecast(
    question_id: str,
    method_version: str = "v0.1.0",
    session: Session = Depends(get_session),
):
    question = session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    evidences = session.exec(
        select(EvidenceItem).where(EvidenceItem.question_id == question_id)
    ).all()

    base_rate = BASE_RATES.get(question.category, 0.5)
    log_odds = logit(base_rate)

    explanation_lines = []
    explanation_lines.append("### Methodik: bayes_logodds_v1\n")
    explanation_lines.append(f"- Base-Rate (Kategorie): **{base_rate*100:.1f}%**")

    total_weight = 0.0

    for ev in evidences:
        contribution = ev.direction * ev.weight
        log_odds += contribution
        total_weight += abs(ev.weight)

        explanation_lines.append(
            f"- `{ev.indicator_type}` (id={ev.id}): "
            f"dir={ev.direction}, weight={ev.weight} "
            f"→ contribution={contribution:+.3f}"
        )

    posterior = inv_logit(log_odds)
    probability = round(posterior * 100, 2)

    confidence = min(100.0, round(total_weight * 80, 2))

    explanation_lines.insert(
        2, f"- Ergebnis (Posterior): **{probability:.2f}%**"
    )
    explanation_lines.insert(
        3, f"- Confidence (MVP-Heuristik): **{confidence:.2f}%**\n"
    )

    explanation_lines.append(
        "\n### Hinweis\n"
        "- Später: Kalibrierung (Brier Score), "
        "Source-Credibility, Time-Decay, Crowd-Module."
    )

    explanation_md = "\n".join(explanation_lines)

    inputs_hash = hashlib.sha256(
        (str(base_rate) + str([(e.id, e.direction, e.weight) for e in evidences])).encode()
    ).hexdigest()

    forecast = Forecast(
        question_id=question_id,
        probability=probability,
        confidence=confidence,
        method="bayes_logodds_v1",
        method_version=method_version,
        explanation_md=explanation_md,
        inputs_hash=inputs_hash,
        created_at=datetime.utcnow(),
    )

    session.add(forecast)
    session.commit()
    session.refresh(forecast)

    return forecast


# -----------------------------
# Forecast History
# -----------------------------

@router.get("/{question_id}/forecasts", response_model=List[ForecastRead])
def get_forecasts(question_id: str, session: Session = Depends(get_session)):
    forecasts = session.exec(
        select(Forecast)
        .where(Forecast.question_id == question_id)
        .order_by(Forecast.created_at.desc())
    ).all()

    return forecasts
