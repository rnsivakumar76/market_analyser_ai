"""
Real-Time Geopolitical Sentiment Analyzer with NewsAPI Integration
Combines real-time news with advanced sentiment analysis
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics
import logging
import re

from .geopolitical_realtime import RealTimeGeopoliticalAnalyzer

logger = logging.getLogger(__name__)

class RealTimeSentimentAnalyzer:
    def __init__(self):
        self.news_analyzer = RealTimeGeopoliticalAnalyzer()
        
        # Enhanced sentiment keywords with weights
        self.positive_keywords = {
            'peace': 0.8, 'agreement': 0.7, 'cooperation': 0.6, 'stability': 0.7,
            'growth': 0.5, 'recovery': 0.6, 'optimistic': 0.5, 'bullish': 0.4
        }
        
        self.negative_keywords = {
            'war': 1.0, 'conflict': 0.9, 'crisis': 0.8, 'tension': 0.7,
            'sanctions': 0.8, 'embargo': 0.7, 'military': 0.6, 'attack': 0.9,
            'threat': 0.7, 'risk': 0.5, 'bearish': 0.4, 'volatility': 0.3
        }
        
        # Geopolitical impact weights
        self.impact_weights = {
            'iran': 0.9, 'usa': 0.8, 'russia': 0.9, 'ukraine': 0.8,
            'china': 0.8, 'taiwan': 0.7, 'nuclear': 1.0, 'war': 1.0,
            'oil': 0.8, 'energy': 0.7, 'sanctions': 0.8, 'military': 0.9
        }
    
    def analyze_article_sentiment(self, article: Dict) -> Dict:
        """Analyze sentiment of a single article"""
        title = article.get('title', '')
        description = article.get('description', '')
        content = f"{title} {description}".lower()
        
        # Calculate sentiment score
        sentiment_score = self.calculate_sentiment_score(content)
        
        # Calculate impact level based on sentiment and keywords
        impact_level = self.determine_impact_level(sentiment_score, content)
        
        # Extract additional metadata
        affected_sectors = self.news_analyzer.get_affected_sectors(content)
        affected_regions = self.news_analyzer.get_affected_regions(content)
        conflict_keywords = self.news_analyzer.extract_conflict_keywords(content)
        
        return {
            'title': title,
            'description': description,
            'source': article.get('source', 'Unknown'),
            'published': article.get('published', datetime.now()),
            'sentiment_score': sentiment_score,
            'impact_level': impact_level,
            'affected_regions': affected_regions,
            'affected_sectors': affected_sectors,
            'conflict_keywords': conflict_keywords,
            'url': article.get('url', ''),
            'keyword_count': article.get('keyword_count', 0),
            'data_source': 'newsapi_realtime'
        }
    
    def calculate_sentiment_score(self, content: str) -> float:
        """Calculate sentiment score using keyword analysis"""
        positive_score = 0
        negative_score = 0
        
        # Count positive keywords
        for word, weight in self.positive_keywords.items():
            count = len(re.findall(r'\b' + word + r'\b', content))
            positive_score += count * weight
        
        # Count negative keywords
        for word, weight in self.negative_keywords.items():
            count = len(re.findall(r'\b' + word + r'\b', content))
            negative_score += count * weight
        
        # Calculate geopolitical impact weight
        geopolitical_weight = self.calculate_geopolitical_weight(content)
        
        # Normalize and combine scores
        total_words = len(content.split())
        if total_words == 0:
            return 0.0
        
        # Base sentiment
        base_sentiment = (positive_score - negative_score) / (total_words * 0.1)
        
        # Apply geopolitical weighting
        weighted_sentiment = base_sentiment * (1 + geopolitical_weight * 0.5)
        
        # Clamp between -1 and 1
        return max(-1.0, min(1.0, weighted_sentiment))
    
    def calculate_geopolitical_weight(self, content: str) -> float:
        """Calculate geopolitical importance weight"""
        weight = 0.0
        
        for keyword, keyword_weight in self.impact_weights.items():
            if keyword in content:
                weight += keyword_weight * 0.1
        
        return min(weight, 1.0)  # Cap at 1.0
    
    def determine_impact_level(self, sentiment_score: float, content: str) -> str:
        """Determine impact level based on sentiment and content"""
        # Strong negative sentiment with geopolitical keywords = Critical
        if sentiment_score < -0.6:
            geopolitical_weight = self.calculate_geopolitical_weight(content)
            if geopolitical_weight > 0.5:
                return 'CRITICAL'
            else:
                return 'HIGH'
        
        # Moderate negative sentiment = High impact
        elif sentiment_score < -0.3:
            return 'HIGH'
        
        # Slightly negative = Medium impact
        elif sentiment_score < -0.1:
            return 'MEDIUM'
        
        # Neutral or positive = Low impact
        else:
            return 'LOW'
    
    def analyze_geopolitical_sentiment(self) -> Dict[str, any]:
        """Complete real-time geopolitical sentiment analysis"""
        logger.info("Starting real-time geopolitical sentiment analysis...")
        
        # Fetch real news
        articles = self.news_analyzer.fetch_geopolitical_news()
        
        if not articles:
            logger.warning("No real-time articles found, using fallback")
            return self.get_fallback_analysis()
        
        # Analyze sentiment for each article
        analyzed_events = []
        for article in articles:
            analyzed = self.analyze_article_sentiment(article)
            analyzed_events.append(analyzed)
        
        # Categorize events by impact level
        critical_events = [e for e in analyzed_events if e['impact_level'] == 'CRITICAL']
        high_impact_events = [e for e in analyzed_events if e['impact_level'] == 'HIGH']
        
        # Calculate overall sentiment
        overall_sentiment = self.calculate_overall_sentiment(analyzed_events)
        
        # Generate trading recommendations
        trading_recommendations = self.generate_trading_recommendations(analyzed_events, overall_sentiment)
        
        # Analyze sector impacts
        affected_sectors = self.analyze_sector_impacts(analyzed_events)
        
        # Assess market risk
        risk_assessment = self.assess_market_risk(analyzed_events)
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'total_events_analyzed': len(analyzed_events),
            'overall_sentiment': overall_sentiment,
            'critical_events': critical_events,
            'high_impact_events': high_impact_events,
            'trading_recommendations': trading_recommendations,
            'affected_sectors': affected_sectors,
            'risk_assessment': risk_assessment,
            'data_source': 'real_time_newsapi',
            'last_updated': datetime.now().isoformat(),
            'news_sources': list(set([e['source'] for e in analyzed_events])),
            'keyword_analysis': self.get_keyword_analysis(analyzed_events)
        }
        
        logger.info(f"Real-time analysis completed: {len(critical_events)} critical, {len(high_impact_events)} high impact events")
        return result
    
    def calculate_overall_sentiment(self, events: List[Dict]) -> Dict[str, float]:
        """Calculate overall sentiment across all events"""
        if not events:
            return {'overall_score': 0.0, 'trend': 'stable', 'volatility_risk': 0.0}
        
        sentiment_scores = [event['sentiment_score'] for event in events]
        overall_score = sum(sentiment_scores) / len(sentiment_scores)
        
        # Calculate trend based on recency
        recent_events = [e for e in events if (datetime.now() - e['published']).hours < 12]
        older_events = [e for e in events if 12 <= (datetime.now() - e['published']).hours < 24]
        
        if recent_events and older_events:
            recent_avg = sum(e['sentiment_score'] for e in recent_events) / len(recent_events)
            older_avg = sum(e['sentiment_score'] for e in older_events) / len(older_events)
            trend = 'improving' if recent_avg > older_avg else 'worsening'
        else:
            trend = 'stable'
        
        # Calculate volatility risk
        if len(sentiment_scores) > 1:
            variance = sum((x - overall_score) ** 2 for x in sentiment_scores) / len(sentiment_scores)
            volatility_risk = min((variance ** 0.5) * 2, 1.0)
        else:
            volatility_risk = 0.0
        
        return {
            'overall_score': overall_score,
            'trend': trend,
            'volatility_risk': volatility_risk,
            'event_count': len(events),
            'critical_count': len([e for e in events if e['impact_level'] == 'CRITICAL'])
        }
    
    def generate_trading_recommendations(self, events: List[Dict], sentiment: Dict) -> Dict[str, any]:
        """Generate trading recommendations based on real-time analysis"""
        recommendations = {
            'energy_markets': [],
            'commodities': [],
            'equities': [],
            'currencies': [],
            'risk_assessment': 'MODERATE'
        }
        
        # Analyze energy markets
        energy_events = [e for e in events if 'energy' in e['affected_sectors']]
        if energy_events:
            avg_sentiment = sum(e['sentiment_score'] for e in energy_events) / len(energy_events)
            critical_count = len([e for e in energy_events if e['impact_level'] == 'CRITICAL'])
            
            if critical_count > 0 or avg_sentiment < -0.3:
                confidence = min(critical_count * 0.3 + abs(avg_sentiment) * 0.4, 0.9)
                recommendations['energy_markets'].append({
                    'asset': 'Crude Oil (WTI/Brent)',
                    'action': 'BUY',
                    'reason': f'Real-time geopolitical tension detected ({len(energy_events)} events)',
                    'confidence': confidence,
                    'time_horizon': '1-2 weeks',
                    'volatility_expectation': 'HIGH',
                    'data_source': 'real_time_analysis'
                })
        
        # Analyze commodities (safe haven)
        commodity_events = [e for e in events if 'commodities' in e['affected_sectors']]
        if commodity_events:
            avg_sentiment = sum(e['sentiment_score'] for e in commodity_events) / len(commodity_events)
            critical_count = len([e for e in commodity_events if e['impact_level'] == 'CRITICAL'])
            
            if critical_count > 0 or avg_sentiment < -0.2:
                confidence = min(critical_count * 0.25 + abs(avg_sentiment) * 0.3, 0.8)
                recommendations['commodities'].append({
                    'asset': 'Gold (XAU/USD)',
                    'action': 'BUY',
                    'reason': f'Safe-haven demand due to real-time geopolitical uncertainty ({len(commodity_events)} events)',
                    'confidence': confidence,
                    'time_horizon': '2-4 weeks',
                    'volatility_expectation': 'MEDIUM-HIGH',
                    'data_source': 'real_time_analysis'
                })
        
        # Overall risk assessment
        critical_count = len([e for e in events if e['impact_level'] == 'CRITICAL'])
        if critical_count >= 3:
            recommendations['risk_assessment'] = 'HIGH'
        elif critical_count >= 1:
            recommendations['risk_assessment'] = 'MODERATE-HIGH'
        elif len([e for e in events if e['impact_level'] == 'HIGH']) >= 3:
            recommendations['risk_assessment'] = 'MODERATE'
        
        return recommendations
    
    def analyze_sector_impacts(self, events: List[Dict]) -> Dict[str, float]:
        """Analyze impact on different sectors"""
        sector_impacts = {}
        
        for sector in ['energy', 'commodities', 'defense', 'transportation', 'finance']:
            sector_events = [e for e in events if sector in e['affected_sectors']]
            if sector_events:
                avg_sentiment = sum(e['sentiment_score'] for e in sector_events) / len(sector_events)
                impact_score = abs(avg_sentiment) * len(sector_events)
                sector_impacts[sector] = min(impact_score, 1.0)
            else:
                sector_impacts[sector] = 0.0
        
        return sector_impacts
    
    def assess_market_risk(self, events: List[Dict]) -> Dict[str, any]:
        """Assess overall market risk"""
        critical_events = [e for e in events if e['impact_level'] == 'CRITICAL']
        high_events = [e for e in events if e['impact_level'] == 'HIGH']
        
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
            'recommended_position_sizing': 'REDUCE' if risk_level == 'CRITICAL' else 'NORMAL',
            'data_source': 'real_time_analysis'
        }
    
    def get_keyword_analysis(self, events: List[Dict]) -> Dict[str, any]:
        """Analyze keyword frequency across all events"""
        all_keywords = []
        for event in events:
            all_keywords.extend(event['conflict_keywords'])
        
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Sort by frequency
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_keywords': len(all_keywords),
            'unique_keywords': len(keyword_counts),
            'top_keywords': top_keywords,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def get_fallback_analysis(self) -> Dict[str, any]:
        """Fallback analysis when real-time data is unavailable"""
        logger.info("Using fallback analysis")
        
        # Return a minimal structure indicating fallback mode
        return {
            'timestamp': datetime.now().isoformat(),
            'total_events_analyzed': 0,
            'overall_sentiment': {
                'overall_score': 0.0,
                'trend': 'stable',
                'volatility_risk': 0.0,
                'event_count': 0,
                'critical_count': 0
            },
            'critical_events': [],
            'high_impact_events': [],
            'trading_recommendations': {
                'energy_markets': [],
                'commodities': [],
                'equities': [],
                'currencies': [],
                'risk_assessment': 'LOW'
            },
            'affected_sectors': {
                'energy': 0.0,
                'commodities': 0.0,
                'defense': 0.0,
                'transportation': 0.0,
                'finance': 0.0
            },
            'risk_assessment': {
                'overall_risk_level': 'LOW',
                'critical_event_count': 0,
                'high_impact_count': 0,
                'volatility_expectation': 'LOW',
                'recommended_position_sizing': 'NORMAL',
                'data_source': 'fallback_mode'
            },
            'data_source': 'fallback_mode',
            'last_updated': datetime.now().isoformat(),
            'news_sources': [],
            'keyword_analysis': {
                'total_keywords': 0,
                'unique_keywords': 0,
                'top_keywords': [],
                'analysis_timestamp': datetime.now().isoformat()
            },
            'error_message': 'Real-time news unavailable - using fallback mode'
        }
