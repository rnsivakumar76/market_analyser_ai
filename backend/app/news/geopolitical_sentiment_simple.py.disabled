"""
Simplified Geopolitical News Sentiment Analyzer
Mock data version for Lambda compatibility
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class GeopoliticalEvent:
    title: str
    description: str
    source: str
    published: datetime
    sentiment_score: float
    impact_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    affected_regions: List[str]
    affected_sectors: List[str]
    conflict_keywords: List[str]

class SimpleGeopoliticalSentimentAnalyzer:
    def __init__(self):
        # Mock data for Iran-US tensions scenario
        self.mock_events = [
            {
                'title': 'Iran-US Tensions Escalate in Persian Gulf',
                'description': 'Military forces on high alert as diplomatic talks stall',
                'source': 'Reuters',
                'published': datetime.now() - timedelta(hours=2),
                'sentiment_score': -0.7,
                'impact_level': 'HIGH',
                'affected_regions': ['middle_east', 'global'],
                'affected_sectors': ['energy', 'commodities', 'defense'],
                'conflict_keywords': ['iran', 'military', 'tension', 'gulf']
            },
            {
                'title': 'Oil Prices Surge on Geopolitical Uncertainty',
                'description': 'Crude oil futures jump 5% amid supply disruption fears',
                'source': 'Bloomberg',
                'published': datetime.now() - timedelta(hours=4),
                'sentiment_score': -0.4,
                'impact_level': 'HIGH',
                'affected_regions': ['global'],
                'affected_sectors': ['energy', 'transportation'],
                'conflict_keywords': ['oil', 'supply', 'geopolitical']
            },
            {
                'title': 'Safe Haven Demand Increases as Investors Seek Gold',
                'description': 'Gold prices rise to 3-month high amid market uncertainty',
                'source': 'Financial Times',
                'published': datetime.now() - timedelta(hours=6),
                'sentiment_score': -0.3,
                'impact_level': 'MEDIUM',
                'affected_regions': ['global'],
                'affected_sectors': ['commodities', 'finance'],
                'conflict_keywords': ['gold', 'safe haven', 'uncertainty']
            }
        ]
    
    def analyze_geopolitical_sentiment(self) -> Dict[str, any]:
        """Analyze geopolitical sentiment using mock data"""
        logger.info("Starting geopolitical sentiment analysis with mock data...")
        
        # Convert mock data to GeopoliticalEvent objects
        analyzed_events = []
        for event_data in self.mock_events:
            event = GeopoliticalEvent(
                title=event_data['title'],
                description=event_data['description'],
                source=event_data['source'],
                published=event_data['published'],
                sentiment_score=event_data['sentiment_score'],
                impact_level=event_data['impact_level'],
                affected_regions=event_data['affected_regions'],
                affected_sectors=event_data['affected_sectors'],
                conflict_keywords=event_data['conflict_keywords']
            )
            analyzed_events.append(event)
        
        # Calculate overall sentiment
        sentiment_analysis = self._calculate_overall_sentiment(analyzed_events)
        
        # Generate trading recommendations
        trading_recommendations = self._generate_trading_recommendations(analyzed_events, sentiment_analysis)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_events_analyzed': len(analyzed_events),
            'overall_sentiment': sentiment_analysis,
            'critical_events': [e for e in analyzed_events if e.impact_level == 'CRITICAL'],
            'high_impact_events': [e for e in analyzed_events if e.impact_level == 'HIGH'],
            'trading_recommendations': trading_recommendations,
            'affected_sectors': self._analyze_sector_impacts(analyzed_events),
            'risk_assessment': self._assess_market_risk(analyzed_events)
        }
    
    def _calculate_overall_sentiment(self, events: List[GeopoliticalEvent]) -> Dict[str, float]:
        """Calculate overall sentiment across all events"""
        if not events:
            return {'overall_score': 0.0, 'trend': 'stable', 'volatility_risk': 0.0}
        
        sentiment_scores = [event.sentiment_score for event in events]
        overall_score = np.mean(sentiment_scores)
        
        # Calculate trend (improving or worsening)
        recent_events = [e for e in events if (datetime.now() - e.published).hours < 24]
        older_events = [e for e in events if 24 <= (datetime.now() - e.published).hours < 72]
        
        if recent_events and older_events:
            recent_avg = np.mean([e.sentiment_score for e in recent_events])
            older_avg = np.mean([e.sentiment_score for e in older_events])
            trend = 'improving' if recent_avg > older_avg else 'worsening'
        else:
            trend = 'stable'
        
        # Calculate volatility risk based on sentiment variance
        volatility_risk = np.std(sentiment_scores) if len(sentiment_scores) > 1 else 0.0
        
        return {
            'overall_score': overall_score,
            'trend': trend,
            'volatility_risk': min(volatility_risk * 2, 1.0),  # Scale to 0-1
            'event_count': len(events),
            'critical_count': len([e for e in events if e.impact_level == 'CRITICAL'])
        }
    
    def _generate_trading_recommendations(self, events: List[GeopoliticalEvent], 
                                       sentiment: Dict) -> Dict[str, any]:
        """Generate trading recommendations based on geopolitical events"""
        recommendations = {
            'energy_markets': [],
            'commodities': [],
            'equities': [],
            'currencies': [],
            'risk_assessment': 'MODERATE'
        }
        
        # Analyze energy markets (crude oil)
        energy_events = [e for e in events if 'energy' in e.affected_sectors]
        if energy_events:
            avg_sentiment = np.mean([e.sentiment_score for e in energy_events])
            critical_count = len([e for e in energy_events if e.impact_level == 'CRITICAL'])
            
            if critical_count > 0 or avg_sentiment < -0.3:
                recommendations['energy_markets'].append({
                    'asset': 'Crude Oil (WTI/Brent)',
                    'action': 'BUY',
                    'reason': 'Geopolitical tension likely to increase oil prices',
                    'confidence': min(critical_count * 0.3, 0.9),
                    'time_horizon': '1-2 weeks',
                    'volatility_expectation': 'HIGH'
                })
        
        # Analyze commodities (gold)
        commodity_events = [e for e in events if 'commodities' in e.affected_sectors]
        if commodity_events:
            avg_sentiment = np.mean([e.sentiment_score for e in commodity_events])
            critical_count = len([e for e in commodity_events if e.impact_level == 'CRITICAL'])
            
            if critical_count > 0 or avg_sentiment < -0.2:
                recommendations['commodities'].append({
                    'asset': 'Gold (XAU/USD)',
                    'action': 'BUY',
                    'reason': 'Safe-haven demand due to geopolitical uncertainty',
                    'confidence': min(critical_count * 0.25, 0.8),
                    'time_horizon': '2-4 weeks',
                    'volatility_expectation': 'MEDIUM-HIGH'
                })
        
        # Overall risk assessment
        critical_count = len([e for e in events if e.impact_level == 'CRITICAL'])
        if critical_count >= 3:
            recommendations['risk_assessment'] = 'HIGH'
        elif critical_count >= 1:
            recommendations['risk_assessment'] = 'MODERATE-HIGH'
        elif len([e for e in events if e.impact_level == 'HIGH']) >= 3:
            recommendations['risk_assessment'] = 'MODERATE'
        
        return recommendations
    
    def _analyze_sector_impacts(self, events: List[GeopoliticalEvent]) -> Dict[str, float]:
        """Analyze impact on different sectors"""
        sector_impacts = {}
        
        for sector in ['energy', 'commodities', 'defense', 'transportation', 'finance']:
            sector_events = [e for e in events if sector in e.affected_sectors]
            if sector_events:
                avg_sentiment = np.mean([e.sentiment_score for e in sector_events])
                impact_score = abs(avg_sentiment) * len(sector_events)
                sector_impacts[sector] = min(impact_score, 1.0)
            else:
                sector_impacts[sector] = 0.0
        
        return sector_impacts
    
    def _assess_market_risk(self, events: List[GeopoliticalEvent]) -> Dict[str, any]:
        """Assess overall market risk"""
        critical_events = [e for e in events if e.impact_level == 'CRITICAL']
        high_events = [e for e in events if e.impact_level == 'HIGH']
        
        risk_level = 'LOW'
        if len(critical_events) >= 2:
            risk_level = 'CRITICAL'
        elif len(critical_events) >= 1 or len(high_events) >= 3:
            risk_level = 'HIGH'
        elif len(high_events) >= 1:
            risk_level = 'MODERATE'
        
        return {
            'overall_risk_level': risk_level,
            'critical_event_count': len(critical_events),
            'high_impact_count': len(high_events),
            'volatility_expectation': 'HIGH' if risk_level in ['HIGH', 'CRITICAL'] else 'MEDIUM',
            'recommended_position_sizing': 'REDUCE' if risk_level == 'CRITICAL' else 'NORMAL'
        }
