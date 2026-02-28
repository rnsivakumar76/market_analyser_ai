"""
Geopolitical News API Routes
Real-time analysis for crisis scenarios and trading opportunities
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

from .geopolitical_sentiment_basic import BasicGeopoliticalSentimentAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geopolitical", tags=["geopolitical"])

# Global analyzer instance
geopolitical_analyzer = BasicGeopoliticalSentimentAnalyzer()

class GeopoliticalRequest(BaseModel):
    regions: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    time_horizon: Optional[str] = "24h"  # 24h, 72h, 1w

class TradingRecommendation(BaseModel):
    asset: str
    action: str  # BUY, SELL, HOLD
    reason: str
    confidence: float
    time_horizon: str
    volatility_expectation: str

class GeopoliticalResponse(BaseModel):
    timestamp: str
    overall_sentiment: Dict[str, float]
    critical_events: List[Dict]
    high_impact_events: List[Dict]
    trading_recommendations: Dict[str, List[TradingRecommendation]]
    affected_sectors: Dict[str, float]
    risk_assessment: Dict[str, str | float | int]
    market_impact_forecast: Dict[str, str | float | int]

@router.get("/sentiment", response_model=GeopoliticalResponse)
def get_geopolitical_sentiment():
    """Get real-time geopolitical sentiment analysis"""
    try:
        logger.info("Starting geopolitical sentiment analysis...")
        
        # Run analysis
        analysis_result = geopolitical_analyzer.analyze_geopolitical_sentiment()
        
        # Convert to response format
        response = GeopoliticalResponse(
            timestamp=analysis_result['timestamp'],
            overall_sentiment=analysis_result['overall_sentiment'],
            critical_events=[{
                'title': event.title,
                'description': event.description,
                'source': event.source,
                'published': event.published.isoformat(),
                'sentiment_score': event.sentiment_score,
                'affected_regions': event.affected_regions,
                'affected_sectors': event.affected_sectors,
                'conflict_keywords': event.conflict_keywords
            } for event in analysis_result['critical_events']],
            high_impact_events=[{
                'title': event.title,
                'description': event.description,
                'source': event.source,
                'published': event.published.isoformat(),
                'sentiment_score': event.sentiment_score,
                'affected_regions': event.affected_regions,
                'affected_sectors': event.affected_sectors,
                'conflict_keywords': event.conflict_keywords
            } for event in analysis_result['high_impact_events']],
            trading_recommendations=analysis_result['trading_recommendations'],
            affected_sectors=analysis_result['affected_sectors'],
            risk_assessment={
                'overall_risk_level': analysis_result['risk_assessment']['overall_risk_level'],
                'critical_event_count': analysis_result['risk_assessment']['critical_event_count'],
                'high_impact_count': analysis_result['risk_assessment']['high_impact_count'],
                'volatility_expectation': analysis_result['risk_assessment']['volatility_expectation'],
                'recommended_position_sizing': analysis_result['risk_assessment']['recommended_position_sizing']
            },
            market_impact_forecast={
                'energy_outlook': 'BULLISH',
                'commodities_outlook': 'BULLISH',
                'overall_volatility': 'HIGH'
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in geopolitical sentiment analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/crisis-alerts")
def get_crisis_alerts():
    """Get immediate crisis alerts for trading"""
    try:
        analysis_result = geopolitical_analyzer.analyze_geopolitical_sentiment()
        
        # Filter for critical and high-impact events
        alerts = []
        
        for event in analysis_result['critical_events']:
            alerts.append({
                'severity': 'CRITICAL',
                'title': event.title,
                'description': event.description,
                'source': event.source,
                'published': event.published.isoformat(),
                'affected_sectors': event.affected_sectors,
                'trading_impact': 'HIGH_VOLATILITY_EXPECTED',
                'recommended_actions': ['REDUCE_POSITIONS', 'INCREASE_HEDGES', 'MONITOR_CLOSELY']
            })
        
        for event in analysis_result['high_impact_events']:
            alerts.append({
                'severity': 'HIGH',
                'title': event.title,
                'description': event.description,
                'source': event.source,
                'published': event.published.isoformat(),
                'affected_sectors': event.affected_sectors,
                'trading_impact': 'MODERATE_VOLATILITY_EXPECTED',
                'recommended_actions': ['ASSESS_RISK', 'CONSIDER_HEDGES']
            })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'alert_count': len(alerts),
            'alerts': alerts,
            'overall_risk_level': analysis_result['risk_assessment']['overall_risk_level']
        }
        
    except Exception as e:
        logger.error(f"Error getting crisis alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Alert generation failed: {str(e)}")

@router.get("/energy-markets")
def get_energy_markets_analysis():
    """Specific analysis for energy markets (crude oil, natural gas)"""
    try:
        analysis_result = geopolitical_analyzer.analyze_geopolitical_sentiment()
        
        energy_recommendations = analysis_result['trading_recommendations'].get('energy_markets', [])
        energy_events = [e for e in analysis_result['critical_events'] + analysis_result['high_impact_events'] 
                        if 'energy' in e.affected_sectors]
        
        # Calculate energy-specific sentiment
        energy_sentiment = 0.0
        if energy_events:
            energy_sentiment = sum(e.sentiment_score for e in energy_events) / len(energy_events)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'energy_sentiment': energy_sentiment,
            'volatility_risk': abs(energy_sentiment) * len(energy_events),
            'recommendations': energy_recommendations,
            'key_events': [{
                'title': event.title,
                'description': event.description,
                'impact_level': event.impact_level,
                'published': event.published.isoformat()
            } for event in energy_events],
            'market_outlook': 'BULLISH' if energy_sentiment < -0.2 else 'NEUTRAL',
            'price_impact_expectation': 'HIGH' if len(energy_events) >= 2 else 'MODERATE'
        }
        
    except Exception as e:
        logger.error(f"Error in energy markets analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Energy analysis failed: {str(e)}")

@router.get("/safe-haven")
def get_safe_haven_analysis():
    """Analysis for safe-haven assets (gold, USD, bonds)"""
    try:
        analysis_result = geopolitical_analyzer.analyze_geopolitical_sentiment()
        
        commodity_recommendations = analysis_result['trading_recommendations'].get('commodities', [])
        safe_haven_events = [e for e in analysis_result['critical_events'] + analysis_result['high_impact_events'] 
                           if 'commodities' in e.affected_sectors]
        
        # Calculate safe-haven demand indicator
        safe_haven_demand = 0.0
        if safe_haven_events:
            safe_haven_demand = sum(abs(e.sentiment_score) for e in safe_haven_events) / len(safe_haven_events)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'safe_haven_demand': safe_haven_demand,
            'gold_recommendations': [r for r in commodity_recommendations if 'Gold' in r['asset']],
            'key_events': [{
                'title': event.title,
                'description': event.description,
                'impact_level': event.impact_level,
                'published': event.published.isoformat()
            } for event in safe_haven_events],
            'market_outlook': 'BULLISH' if safe_haven_demand > 0.3 else 'NEUTRAL',
            'volatility_expectation': 'MEDIUM-HIGH'
        }
        
    except Exception as e:
        logger.error(f"Error in safe haven analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Safe haven analysis failed: {str(e)}")

@router.post("/custom-analysis")
async def get_custom_analysis(request: GeopoliticalRequest):
    """Custom analysis based on specific regions and sectors"""
    try:
        # Get full analysis
        full_analysis = await geopolitical_analyzer.analyze_geopolitical_sentiment()
        
        # Filter based on request parameters
        filtered_events = []
        
        for event in full_analysis['critical_events'] + full_analysis['high_impact_events']:
            # Filter by regions
            if request.regions:
                if not any(region in event.affected_regions for region in request.regions):
                    continue
            
            # Filter by sectors
            if request.sectors:
                if not any(sector in event.affected_sectors for sector in request.sectors):
                    continue
            
            filtered_events.append(event)
        
        # Generate custom recommendations
        custom_recommendations = geopolitical_analyzer._generate_trading_recommendations(
            filtered_events, 
            full_analysis['overall_sentiment']
        )
        
        return {
            'timestamp': datetime.now().isoformat(),
            'request_parameters': {
                'regions': request.regions,
                'sectors': request.sectors,
                'time_horizon': request.time_horizon
            },
            'filtered_events': len(filtered_events),
            'custom_recommendations': custom_recommendations,
            'risk_assessment': geopolitical_analyzer._assess_market_risk(filtered_events)
        }
        
    except Exception as e:
        logger.error(f"Error in custom analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Custom analysis failed: {str(e)}")

@router.get("/historical-sentiment")
async def get_historical_sentiment(days: int = 7):
    """Get historical sentiment trends"""
    try:
        # This would typically query a database
        # For now, return mock historical data
        historical_data = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            # Mock sentiment calculation
            sentiment_score = -0.3 + (i * 0.05)  # Improving sentiment over time
            volatility_risk = 0.7 - (i * 0.08)   # Decreasing volatility over time
            
            historical_data.append({
                'date': date.isoformat(),
                'sentiment_score': sentiment_score,
                'volatility_risk': volatility_risk,
                'event_count': max(1, 10 - i)
            })
        
        return {
            'period_days': days,
            'historical_data': historical_data,
            'trend': 'IMPROVING' if historical_data[-1]['sentiment_score'] > historical_data[0]['sentiment_score'] else 'DECLINING'
        }
        
    except Exception as e:
        logger.error(f"Error getting historical sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Historical analysis failed: {str(e)}")
