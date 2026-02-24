import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging
from typing import List, Dict, Any
from ..models import NewsSentiment, NewsItem

logger = logging.getLogger(__name__)

def fetch_rss_news(symbol: str) -> List[Dict[str, str]]:
    """Fetch news from various RSS sources."""
    news_items = []
    
    # Financial symbols often work well with Yahoo Finance and Google News search
    # This is a robust free way to get headlines
    urls = [
        f"https://www.google.com/search?q={symbol}+stock+news&tbm=nws&tbs=qdr:d",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Google News scrape (simplified)
                # Google often changes its structure, so we look for common title patterns
                for item in soup.find_all('div', attrs={'role': 'heading'}):
                    title = item.get_text()
                    if title and len(title) > 10:
                        news_items.append({
                            "title": title,
                            "source": "Google News (Search)",
                            "url": url
                        })
                
                # If Google News div fails, try common anchor tags in news search
                if not news_items:
                    for a in soup.find_all('a'):
                        text = a.get_text()
                        if len(text) > 30: # Likely a headline
                            news_items.append({
                                "title": text,
                                "source": "News Search",
                                "url": url
                            })
                            
            if len(news_items) >= 10:
                break
        except Exception as e:
            logger.error(f"Failed to fetch news for {symbol}: {e}")
            
    return news_items[:10]

def analyze_news_sentiment(symbol: str) -> NewsSentiment:
    """Analyze sentiment of recent news for a symbol."""
    news_data = fetch_rss_news(symbol)
    
    if not news_data:
        return NewsSentiment(
            score=0.0,
            label="Neutral",
            sentiment_summary="No recent news found.",
            news_items=[]
        )
    
    analyzer = SentimentIntensityAnalyzer()
    total_compound = 0
    analyzed_items = []
    
    for item in news_data:
        title = item["title"]
        vs = analyzer.polarity_scores(title)
        compound = vs['compound']
        total_compound += compound
        
        # Determine individual item sentiment
        item_label = "Neutral"
        if compound >= 0.05:
            item_label = "Bullish"
        elif compound <= -0.05:
            item_label = "Bearish"
            
        analyzed_items.append(NewsItem(
            title=title,
            source=item["source"],
            url=item["url"],
            sentiment_score=round(compound, 2),
            sentiment_label=item_label
        ))
    
    avg_score = total_compound / len(news_data)
    
    # Determine overall label
    if avg_score >= 0.05:
        label = "Bullish"
    elif avg_score <= -0.05:
        label = "Bearish"
    else:
        label = "Neutral"
        
    summary = f"Sentiment is {label} based on {len(news_data)} recent headlines."
    if avg_score > 0.3:
        summary += " Very strong positive bias detected."
    elif avg_score < -0.3:
        summary += " Significant negative news pressure."
        
    return NewsSentiment(
        score=round(avg_score, 2),
        label=label,
        sentiment_summary=summary,
        news_items=analyzed_items
    )
