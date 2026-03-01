"""
Geopolitical News API Routes
Serves the GeopoliticalAnalysisComponent dashboard.
Per-instrument geo risk is handled separately in geo_risk_analyzer.py.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from .geopolitical_lambda_safe import LambdaSafeSentimentAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geopolitical", tags=["geopolitical"])

# Use the correct class — analyze_geopolitical_sentiment() lives here
_analyzer = LambdaSafeSentimentAnalyzer()


class GeopoliticalResponse(BaseModel):
    timestamp: str
    overall_sentiment: Dict[str, Any]          # Any: contains float + string fields
    critical_events: List[Dict[str, Any]]
    high_impact_events: List[Dict[str, Any]]
    trading_recommendations: Dict[str, Any]    # Any: contains lists + string 'risk_assessment'
    affected_sectors: Dict[str, float]
    risk_assessment: Dict[str, Any]
    market_impact_forecast: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True


def _safe_response() -> GeopoliticalResponse:
    """Always-valid fallback response."""
    return GeopoliticalResponse(
        timestamp=datetime.now().isoformat(),
        overall_sentiment={"overall_score": 0.0, "trend": "stable",
                           "volatility_risk": 0.0, "event_count": 0, "critical_count": 0},
        critical_events=[],
        high_impact_events=[],
        trading_recommendations={
            "energy_markets": [], "commodities": [],
            "equities": [], "currencies": [], "risk_assessment": "MODERATE"
        },
        affected_sectors={"energy": 0.0, "commodities": 0.0,
                          "defense": 0.0, "transportation": 0.0, "finance": 0.0},
        risk_assessment={"overall_risk_level": "MODERATE", "critical_event_count": 0,
                         "high_impact_count": 0, "volatility_expectation": "MEDIUM",
                         "recommended_position_sizing": "NORMAL"},
        market_impact_forecast={"energy_outlook": "NEUTRAL",
                                "commodities_outlook": "NEUTRAL", "overall_volatility": "MEDIUM"},
    )


@router.get("/health")
def geo_health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@router.get("/sentiment", response_model=GeopoliticalResponse)
def get_geopolitical_sentiment():
    """Geopolitical sentiment for the dashboard panel."""
    try:
        result = _analyzer.analyze_geopolitical_sentiment()
        return GeopoliticalResponse(
            timestamp=result.get("timestamp", datetime.now().isoformat()),
            overall_sentiment=result.get("overall_sentiment", {}),
            critical_events=result.get("critical_events", []),
            high_impact_events=result.get("high_impact_events", []),
            trading_recommendations=result.get("trading_recommendations", {}),
            affected_sectors=result.get("affected_sectors", {}),
            risk_assessment=result.get("risk_assessment", {}),
            market_impact_forecast=result.get("market_impact_forecast",
                                              {"energy_outlook": "NEUTRAL",
                                               "commodities_outlook": "NEUTRAL",
                                               "overall_volatility": "MEDIUM"}),
        )
    except Exception as e:
        logger.error(f"Geopolitical sentiment error: {e}")
        return _safe_response()


@router.get("/crisis-alerts")
def get_crisis_alerts():
    try:
        result = _analyzer.analyze_geopolitical_sentiment()
        alerts = []
        for ev in result.get("critical_events", []):
            alerts.append({**ev, "severity": "CRITICAL"})
        for ev in result.get("high_impact_events", []):
            alerts.append({**ev, "severity": "HIGH"})
        return {"timestamp": datetime.now().isoformat(),
                "alert_count": len(alerts), "alerts": alerts,
                "overall_risk_level": result.get("risk_assessment", {}).get("overall_risk_level", "MODERATE")}
    except Exception as e:
        logger.error(f"Crisis alerts error: {e}")
        return {"timestamp": datetime.now().isoformat(), "alert_count": 0, "alerts": [],
                "overall_risk_level": "MODERATE"}


@router.get("/energy-markets")
def get_energy_markets():
    try:
        result = _analyzer.analyze_geopolitical_sentiment()
        return {"timestamp": datetime.now().isoformat(),
                "recommendations": result.get("trading_recommendations", {}).get("energy_markets", []),
                "affected_sectors": result.get("affected_sectors", {})}
    except Exception as e:
        logger.error(f"Energy markets error: {e}")
        return {"timestamp": datetime.now().isoformat(), "recommendations": [], "affected_sectors": {}}


@router.get("/safe-haven")
def get_safe_haven():
    try:
        result = _analyzer.analyze_geopolitical_sentiment()
        return {"timestamp": datetime.now().isoformat(),
                "recommendations": result.get("trading_recommendations", {}).get("commodities", []),
                "risk_assessment": result.get("risk_assessment", {})}
    except Exception as e:
        logger.error(f"Safe haven error: {e}")
        return {"timestamp": datetime.now().isoformat(), "recommendations": [], "risk_assessment": {}}

