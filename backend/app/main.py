from fastapi import FastAPI
from pydantic import BaseModel
import math
import random

app = FastAPI()


class ForecastResponse(BaseModel):
    slug: str
    probability: float
    confidence: float
    factors: dict


# -----------------------------
# Media Sentiment
# -----------------------------
def calculate_media_sentiment(slug: str) -> float:
    slug = slug.lower()

    positive_keywords = ["growth", "boom", "innovation", "success", "breakthrough"]
    negative_keywords = ["crash", "crisis", "risk", "decline", "war"]

    base_score = 0.6

    for word in positive_keywords:
        if word in slug:
            base_score += 0.1

    for word in negative_keywords:
        if word in slug:
            base_score -= 0.15

    noise = random.uniform(-0.05, 0.05)

    return max(0.1, min(0.95, base_score + noise))


# -----------------------------
# Quellengewichtung
# -----------------------------
def calculate_source_weight(slug: str) -> float:
    slug = slug.lower()

    if "study" in slug or "research" in slug:
        return 0.9
    if "news" in slug or "report" in slug:
        return 0.75
    if "blog" in slug or "opinion" in slug:
        return 0.5

    return 0.7


# -----------------------------
# Momentum Simulation
# -----------------------------
def simulate_previous_probability() -> float:
    return random.uniform(0.3, 0.8)


# -----------------------------
# Forecast Endpoint
# -----------------------------
@app.get("/forecast/{slug}", response_model=ForecastResponse)
def get_forecast(slug: str):

    # Basisfaktoren
    trend_score = random.uniform(0.4, 0.9)
    volatility = random.uniform(0.1, 0.5)
    ai_signal = random.uniform(0.3, 0.95)

    # Media
    media_raw = calculate_media_sentiment(slug)
    source_weight = calculate_source_weight(slug)
    media_weighted = media_raw * source_weight

    # Momentum
    previous_probability = simulate_previous_probability()

    # Basisscore
    base_score = (
        trend_score * 0.30 +
        ai_signal * 0.25 +
        (1 - volatility) * 0.15 +
        media_weighted * 0.30
    )

    # Momentum-Einfluss (20%)
    momentum_score = (base_score * 0.8) + (previous_probability * 0.2)

    # Sigmoid Normalisierung
    probability = 1 / (1 + math.exp(-5 * (momentum_score - 0.5)))

    probability_percent = round(probability * 100, 2)
    confidence = round((1 - volatility) * 100, 2)

    return {
        "slug": slug,
        "probability": probability_percent,
        "confidence": confidence,
        "factors": {
            "trend_score": round(trend_score, 2),
            "ai_signal": round(ai_signal, 2),
            "volatility": round(volatility, 2),
            "media_sentiment_raw": round(media_raw, 2),
            "source_weight": round(source_weight, 2),
            "media_sentiment_weighted": round(media_weighted, 2),
            "previous_probability": round(previous_probability * 100, 2)
        }
    }
