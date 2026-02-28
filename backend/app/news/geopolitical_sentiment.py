"""
Geopolitical News Sentiment Analyzer
Specialized for crisis scenarios like Iran-US tensions, wars, conflicts
"""

import requests
import feedparser
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

class GeopoliticalSentimentAnalyzer:
    def __init__(self):
        self.geopolitical_sources = [
            'https://feeds.bbci.co.uk/news/world/rss.xml',
            'https://feeds.reuters.com/reuters/worldNews',
            'https://feeds.bloomberg.com/markets/news.rss',
            'https://www.aljazeera.com/xml/rss/all.xml',
            'https://feeds.feedburner.com/axios/world',
            'https://feeds.feedburner.com/foreignpolicy/articles'
        ]
        
        self.conflict_keywords = {
            'iran': ['iran', 'persian gulf', 'tehran', 'nuclear', 'sanctions'],
            'middle_east': ['middle east', 'gulf', 'oil', 'petroleum', 'opec'],
            'us_military': ['pentagon', 'us military', 'defense', 'navy', 'air force'],
            'crisis': ['conflict', 'tension', 'escalation', 'military action', 'strike'],
            'energy': ['crude oil', 'gold', 'commodities', 'energy security', 'supply chain']
        }
        
        self.sector_impacts = {
            'energy': ['crude oil', 'natural gas', 'renewable energy', 'oil companies'],
            'defense': ['defense contractors', 'aerospace', 'military', 'weapons'],
            'commodities': ['gold', 'silver', 'precious metals', 'safe haven'],
            'transportation': ['shipping', 'logistics', 'airlines', 'supply chain'],
            'finance': ['banks', 'insurance', 'risk management', 'volatility']
        }
    
    def analyze_geopolitical_sentiment(self) -> Dict[str, any]:
        """Analyze real-time geopolitical news sentiment"""
        logger.info("Starting geopolitical sentiment analysis...")
        
        # Fetch news from all sources
        all_events = []
        for source in self.geopolitical_sources:
            events = self._fetch_news_source(source)
            all_events.extend(events)
        
        # Analyze sentiment and impact
        analyzed_events = []
        for event in all_events:
            analyzed = self._analyze_event(event)
            if analyzed.impact_level in ['HIGH', 'CRITICAL']:
                analyzed_events.append(analyzed)
        
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
    
    def _fetch_news_source(self, rss_url: str) -> List[Dict]:
        """Fetch news from RSS feed"""
        try:
            response = requests.get(rss_url, timeout=10)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                
                events = []
                for entry in feed.entries[:20]:  # Limit to recent 20 items
                    event = {
                        'title': entry.title,
                        'description': entry.get('description', ''),
                        'source': feed.feed.get('title', 'Unknown'),
                        'published': datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now(),
                        'link': entry.get('link', '')
                    }
                    events.append(event)
                
                return events
        except Exception as e:
            logger.error(f"Error fetching from {rss_url}: {e}")
            return []
    
    def _analyze_event(self, event: Dict) -> GeopoliticalEvent:
        """Analyze individual event for sentiment and impact"""
        text = f"{event['title']} {event['description']}".lower()
        
        # Check for conflict keywords
        detected_keywords = []
        for category, keywords in self.conflict_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    detected_keywords.append(keyword)
        
        # Calculate sentiment score
        sentiment_score = self._calculate_sentiment_score(text)
        
        # Determine impact level
        impact_level = self._determine_impact_level(text, detected_keywords, sentiment_score)
        
        # Identify affected regions and sectors
        affected_regions = self._identify_regions(text)
        affected_sectors = self._identify_sectors(text)
        
        return GeopoliticalEvent(
            title=event['title'],
            description=event['description'],
            source=event['source'],
            published=event['published'],
            sentiment_score=sentiment_score,
            impact_level=impact_level,
            affected_regions=affected_regions,
            affected_sectors=affected_sectors,
            conflict_keywords=detected_keywords
        )
    
    def _calculate_sentiment_score(self, text: str) -> float:
        """Calculate sentiment score for text"""
        # Simple sentiment analysis based on keywords
        positive_words = ['peace', 'diplomacy', 'agreement', 'cooperation', 'stability']
        negative_words = ['conflict', 'war', 'tension', 'escalation', 'crisis', 'attack', 'strike']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        # Normalize to -1 to 1 range
        total_words = positive_count + negative_count
        if total_words == 0:
            return 0.0
        
        sentiment = (positive_count - negative_count) / total_words
        return sentiment
    
    def _determine_impact_level(self, text: str, keywords: List[str], sentiment: float) -> str:
        """Determine impact level based on content analysis"""
        critical_indicators = ['war', 'military action', 'attack', 'strike', 'conflict escalation']
        high_indicators = ['tension', 'sanctions', 'military deployment', 'naval']
        medium_indicators = ['diplomatic', 'negotiations', 'discussions']
        
        if any(indicator in text for indicator in critical_indicators):
            return 'CRITICAL'
        elif any(indicator in text for indicator in high_indicators):
            return 'HIGH'
        elif any(indicator in text for indicator in medium_indicators):
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _identify_regions(self, text: str) -> List[str]:
        """Identify affected regions from text"""
        regions = {
            'middle_east': ['middle east', 'gulf', 'iran', 'iraq', 'saudi arabia', 'israel'],
            'north_america': ['usa', 'america', 'canada', 'mexico'],
            'europe': ['europe', 'uk', 'germany', 'france', 'italy'],
            'asia': ['asia', 'china', 'japan', 'india', 'russia'],
            'global': ['global', 'worldwide', 'international']
        }
        
        affected_regions = []
        for region, keywords in regions.items():
            if any(keyword in text for keyword in keywords):
                affected_regions.append(region)
        
        return affected_regions
    
    def _identify_sectors(self, text: str) -> List[str]:
        """Identify affected sectors from text"""
        affected_sectors = []
        for sector, keywords in self.sector_impacts.items():
            if any(keyword in text for keyword in keywords):
                affected_sectors.append(sector)
        
        return affected_sectors
    
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
        
        # Analyze equities
        equity_events = [e for e in events if any(s in e.affected_sectors for s in ['defense', 'transportation'])]
        if equity_events:
            for sector in ['defense', 'transportation']:
                sector_events = [e for e in equity_events if sector in e.affected_sectors]
                if sector_events:
                    if sector == 'defense':
                        recommendations['equities'].append({
                            'sector': 'Defense & Aerospace',
                            'action': 'BUY',
                            'reason': 'Increased defense spending due to tensions',
                            'confidence': 0.7,
                            'time_horizon': '3-6 months'
                        })
                    else:
                        recommendations['equities'].append({
                            'sector': 'Transportation & Logistics',
                            'action': 'SELL',
                            'reason': 'Supply chain disruptions expected',
                            'confidence': 0.6,
                            'time_horizon': '1-3 months'
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
