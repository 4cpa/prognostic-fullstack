from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.calibration_service import (
    load_backtest_summary,
    load_calibration_report,
    load_runtime_calibration,
)
from app.core.db import get_session


router = APIRouter(prefix="/backtesting", tags=["backtesting"])


@router.get("/summary")
def get_backtesting_summary(
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Returns aggregated backtesting metrics and the underlying records.
    """
    return load_backtest_summary(session)


@router.get("/calibration")
def get_calibration_report(
    num_bins: int = Query(default=10, ge=2, le=20),
    min_bin_count: int = Query(default=3, ge=1, le=100),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Returns global and category-specific calibration tables
    derived from historical resolved-question forecasts.
    """
    return load_calibration_report(
        session,
        num_bins=num_bins,
        min_bin_count=min_bin_count,
    )


@router.get("/runtime")
def get_runtime_calibration(
    num_bins: int = Query(default=10, ge=2, le=20),
    min_bin_count: int = Query(default=3, ge=1, le=100),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Returns the runtime calibration payload used by the forecast engine.
    """
    return load_runtime_calibration(
        session,
        num_bins=num_bins,
        min_bin_count=min_bin_count,
    )
