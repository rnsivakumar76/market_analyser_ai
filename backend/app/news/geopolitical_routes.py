"""
Geopolitical News API Routes
Placeholder router  geopolitical risk is computed per-instrument
in analyze_instrument_lazy via geo_risk_analyzer.py and embedded
inside InstrumentAnalysis.geopolitical_risk.
"""

from fastapi import APIRouter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geopolitical", tags=["geopolitical"])


@router.get("/health")
def geo_health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
