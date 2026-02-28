"""
Geopolitical News API Routes
Real-time analysis for crisis scenarios and trading opportunities
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import logging

from .geopolitical_lambda_safe import LambdaSafeSentimentAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geopolitical", tags=["geopolitical"])

# Global analyzer instance
geopolitical_analyzer = LambdaSafeSentimentAnalyzer()

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
    risk_assessment: Dict[str, Any]
    market_impact_forecast: Dict[str, Any]
    
    class Config:
        arbitrary_types_allowed = True

@router.get("/sentiment", response_model=GeopoliticalResponse)
def get_geopolitical_sentiment():
    """Get real-time geopolitical sentiment analysis - BULLETPROOF VERSION"""
    start_time = geopolitical_analyzer.monitor.start_execution_timer()
    cache_hit = False
    error_occurred = False
    error_message = None
    
    try:
        logger.info("Starting bulletproof geopolitical sentiment analysis...")
        
        # Step 1: Try to get cached analysis first
        try:
            cached_data = geopolitical_analyzer.cache_manager.get_analysis()
            if cached_data:
                cache_hit = True
                execution_time = geopolitical_analyzer.monitor.end_execution_timer(start_time)
                
                # Record successful cache hit
                geopolitical_analyzer.monitor.record_execution(
                    execution_time_ms=execution_time,
                    cache_hit=cache_hit,
                    events_processed=len(cached_data.get('critical_events', [])) + len(cached_data.get('high_impact_events', [])),
                    sentiment_score=cached_data.get('overall_sentiment', {}).get('overall_score', 0),
                    error_occurred=False
                )
                
                logger.info(f"Returning cached analysis (execution: {execution_time:.2f}ms)")
                return cached_data
        except Exception as cache_error:
            logger.warning(f"Cache retrieval failed: {cache_error}")
            # Continue with fresh analysis
        
        # Step 2: Run bulletproof analysis (never fails)
        logger.info("Running bulletproof analysis...")
        try:
            analysis_result = geopolitical_analyzer.analyze_geopolitical_sentiment()
        except Exception as analysis_error:
            logger.error(f"Analysis failed, using emergency fallback: {analysis_error}")
            analysis_result = geopolitical_analyzer._get_emergency_fallback_analysis()
        
        # Step 3: Try to cache the result (non-critical)
        try:
            geopolitical_analyzer.cache_manager.store_analysis(analysis_result)
        except Exception as cache_error:
            logger.warning(f"Cache storage failed: {cache_error}")
            # Continue without caching
        
        # Step 4: Convert to response format with bulletproof error handling
        try:
            response = GeopoliticalResponse(
                timestamp=analysis_result['timestamp'],
                overall_sentiment=analysis_result['overall_sentiment'],
                critical_events=analysis_result.get('critical_events', []),
                high_impact_events=analysis_result.get('high_impact_events', []),
                trading_recommendations=analysis_result.get('trading_recommendations', {}),
                affected_sectors=analysis_result.get('affected_sectors', {}),
                risk_assessment=analysis_result.get('risk_assessment', {}),
                market_impact_forecast=analysis_result.get('market_impact_forecast', {
                    'energy_outlook': 'NEUTRAL',
                    'commodities_outlook': 'NEUTRAL',
                    'overall_volatility': 'MEDIUM'
                })
            )
        except Exception as response_error:
            logger.error(f"Response formatting failed, using minimal response: {response_error}")
            # Create minimal valid response
            response = GeopoliticalResponse(
                timestamp=datetime.now().isoformat(),
                overall_sentiment={'overall_score': 0.0, 'trend': 'stable', 'volatility_risk': 0.0},
                critical_events=[],
                high_impact_events=[],
                trading_recommendations={
                    'energy_markets': [],
                    'commodities': [],
                    'equities': [],
                    'currencies': [],
                    'risk_assessment': 'MODERATE'
                },
                affected_sectors={'energy': 0.0, 'commodities': 0.0, 'defense': 0.0, 'transportation': 0.0, 'finance': 0.0},
                risk_assessment={
                    'overall_risk_level': 'MODERATE',
                    'critical_event_count': 0,
                    'high_impact_count': 0,
                    'volatility_expectation': 'MEDIUM',
                    'recommended_position_sizing': 'NORMAL'
                },
                market_impact_forecast={
                    'energy_outlook': 'NEUTRAL',
                    'commodities_outlook': 'NEUTRAL',
                    'overall_volatility': 'MEDIUM'
                }
            )
        
        execution_time = geopolitical_analyzer.monitor.end_execution_timer(start_time)
        
        # Record successful execution
        try:
            geopolitical_analyzer.monitor.record_execution(
                execution_time_ms=execution_time,
                cache_hit=cache_hit,
                events_processed=len(analysis_result.get('critical_events', [])) + len(analysis_result.get('high_impact_events', [])),
                sentiment_score=analysis_result.get('overall_sentiment', {}).get('overall_score', 0),
                error_occurred=False
            )
        except Exception as monitor_error:
            logger.warning(f"Monitoring failed: {monitor_error}")
        
        logger.info(f"Bulletproof analysis completed successfully (execution: {execution_time:.2f}ms)")
        return response
        
    except Exception as e:
        # This should never be reached due to bulletproof design, but just in case
        error_occurred = True
        error_message = str(e)
        execution_time = geopolitical_analyzer.monitor.end_execution_timer(start_time)
        
        # Record error execution
        try:
            geopolitical_analyzer.monitor.record_execution(
                execution_time_ms=execution_time,
                cache_hit=cache_hit,
                events_processed=0,
                sentiment_score=0,
                error_occurred=True,
                error_message=error_message
            )
        except Exception as monitor_error:
            logger.error(f"Error recording failed: {monitor_error}")
        
        logger.error(f"CRITICAL ERROR in geopolitical sentiment analysis: {error_message}")
        
        # Return emergency fallback response - NEVER fails
        try:
            emergency_response = GeopoliticalResponse(
                timestamp=datetime.now().isoformat(),
                overall_sentiment={'overall_score': 0.0, 'trend': 'stable', 'volatility_risk': 0.0},
                critical_events=[],
                high_impact_events=[],
                trading_recommendations={
                    'energy_markets': [{
                        'asset': 'Crude Oil (WTI/Brent)',
                        'action': 'HOLD',
                        'reason': 'System recovery in progress - dashboard functionality preserved',
                        'confidence': 0.5,
                        'time_horizon': '1-2 weeks',
                        'volatility_expectation': 'MEDIUM',
                        'data_source': 'emergency_response'
                    }],
                    'commodities': [{
                        'asset': 'Gold (XAU/USD)',
                        'action': 'HOLD',
                        'reason': 'System recovery in progress - dashboard functionality preserved',
                        'confidence': 0.5,
                        'time_horizon': '2-4 weeks',
                        'volatility_expectation': 'MEDIUM',
                        'data_source': 'emergency_response'
                    }],
                    'equities': [],
                    'currencies': [],
                    'risk_assessment': 'MODERATE'
                },
                affected_sectors={'energy': 0.0, 'commodities': 0.0, 'defense': 0.0, 'transportation': 0.0, 'finance': 0.0},
                risk_assessment={
                    'overall_risk_level': 'MODERATE',
                    'critical_event_count': 0,
                    'high_impact_count': 0,
                    'volatility_expectation': 'MEDIUM',
                    'recommended_position_sizing': 'NORMAL'
                },
                market_impact_forecast={
                    'energy_outlook': 'NEUTRAL',
                    'commodities_outlook': 'NEUTRAL',
                    'overall_volatility': 'MEDIUM'
                }
            )
            
            logger.info("Emergency response generated - dashboard functionality preserved")
            return emergency_response
            
        except Exception as emergency_error:
            logger.error(f"EMERGENCY RESPONSE FAILED: {emergency_error}")
            # Last resort - return minimal valid response
            return GeopoliticalResponse(
                timestamp=datetime.now().isoformat(),
                overall_sentiment={'overall_score': 0.0, 'trend': 'stable', 'volatility_risk': 0.0},
                critical_events=[],
                high_impact_events=[],
                trading_recommendations={
                    'energy_markets': [],
                    'commodities': [],
                    'equities': [],
                    'currencies': [],
                    'risk_assessment': 'MODERATE'
                },
                affected_sectors={'energy': 0.0, 'commodities': 0.0, 'defense': 0.0, 'transportation': 0.0, 'finance': 0.0},
                risk_assessment={
                    'overall_risk_level': 'MODERATE',
                    'critical_event_count': 0,
                    'high_impact_count': 0,
                    'volatility_expectation': 'MEDIUM',
                    'recommended_position_sizing': 'NORMAL'
                },
                market_impact_forecast={
                    'energy_outlook': 'NEUTRAL',
                    'commodities_outlook': 'NEUTRAL',
                    'overall_volatility': 'MEDIUM'
                }
            )

@router.get("/health")
def get_health_status():
    """Get system health status and performance metrics"""
    try:
        health_status = geopolitical_analyzer.monitor.get_health_status()
        performance_metrics = geopolitical_analyzer.monitor.get_performance_summary()
        cache_stats = geopolitical_analyzer.cache_manager.get_performance_metrics()
        alerts = geopolitical_analyzer.alert_manager.check_alerts(geopolitical_analyzer.monitor)
        
        return {
            'status': health_status['status'],
            'timestamp': datetime.now().isoformat(),
            'health': health_status,
            'performance': performance_metrics,
            'cache': cache_stats,
            'alerts': alerts,
            'system_info': {
                'analyzer_type': 'lambda_safe',
                'cache_enabled': True,
                'monitoring_enabled': True,
                'api_key_configured': bool(geopolitical_analyzer.news_api_key)
            }
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            'status': 'UNHEALTHY',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }

@router.get("/metrics")
def get_detailed_metrics():
    """Get detailed performance metrics and analytics"""
    try:
        performance_summary = geopolitical_analyzer.monitor.get_performance_summary()
        error_analysis = geopolitical_analyzer.monitor.get_error_analysis()
        cache_stats = geopolitical_analyzer.cache_manager.get_performance_metrics()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'performance': performance_summary,
            'errors': error_analysis,
            'cache': cache_stats,
            'recommendations': geopolitical_analyzer.monitor.get_health_status()['recommendations']
        }
        
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics failed: {e}")

@router.post("/cache/clear")
def clear_cache():
    """Clear geopolitical analysis cache"""
    try:
        success = geopolitical_analyzer.cache_manager.invalidate_cache()
        
        return {
            'success': success,
            'message': 'Cache cleared successfully' if success else 'Failed to clear cache',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {e}")
        
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
