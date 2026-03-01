import requests
import xml.etree.ElementTree as ET
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging
import time
from typing import List, Dict, Any
from ..models import NewsSentiment, NewsItem

logger = logging.getLogger(__name__)

# Global cache for news sentiment (15 minute TTL)
_news_cache = {}
_CACHE_TTL = 900  # 15 minutes

# Map internal symbols to Yahoo Finance tickers for RSS
_YAHOO_SYMBOL_MAP = {
    'XAU':  ('GC=F',       'Gold'),
    'XAG':  ('SI=F',       'Silver'),
    'WTI':  ('CL=F',       'Crude Oil'),
    'SPX':  ('^GSPC',      'S&P 500'),
    'BTC':  ('BTC-USD',    'Bitcoin'),
    'ETH':  ('ETH-USD',    'Ethereum'),
    'EUR':  ('EURUSD=X',   'Euro'),
    'GBP':  ('GBPUSD=X',   'British Pound'),
    'JPY':  ('USDJPY=X',   'US Dollar Yen'),
    'DXY':  ('DX-Y.NYB',   'US Dollar Index'),
    'NAS':  ('NQ=F',       'Nasdaq'),
    'DOW':  ('YM=F',       'Dow Jones'),
}


def fetch_rss_news(symbol: str) -> List[Dict[str, str]]:
    """Fetch news from Yahoo Finance RSS. Works reliably from AWS Lambda."""
    news_items = []
    symbol_upper = symbol.upper()

    yf_ticker, _ = _YAHOO_SYMBOL_MAP.get(symbol_upper, (symbol_upper, symbol_upper))

    urls = [
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={yf_ticker}&region=US&lang=en-US",
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; MarketAnalyser/1.0)'
    }

    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200 and response.content:
                try:
                    root = ET.fromstring(response.content)
                    channel = root.find('channel')
                    if channel is not None:
                        for item in channel.findall('item'):
                            title_el = item.find('title')
                            link_el  = item.find('link')
                            source_el = item.find('source')

                            if title_el is not None and title_el.text and len(title_el.text.strip()) > 10:
                                news_items.append({
                                    "title":  title_el.text.strip(),
                                    "source": (source_el.text.strip()
                                               if source_el is not None and source_el.text
                                               else "Yahoo Finance"),
                                    "url":    (link_el.text.strip()
                                               if link_el is not None and link_el.text
                                               else url)
                                })
                except ET.ParseError as e:
                    logger.error(f"RSS parse error for {symbol}: {e}")

            if len(news_items) >= 10:
                break
        except Exception as e:
            logger.error(f"Failed to fetch news for {symbol}: {e}")

    return news_items[:10]

def analyze_news_sentiment(symbol: str) -> NewsSentiment:
    """Analyze sentiment of recent news for a symbol with basic caching."""
    global _news_cache
    
    symbol = symbol.upper()
    now = time.time()
    
    # Check cache
    if symbol in _news_cache:
        cached_time, cached_sentiment = _news_cache[symbol]
        if now - cached_time < _CACHE_TTL:
            return cached_sentiment

    news_data = fetch_rss_news(symbol)
    
    if not news_data:
        sentiment = NewsSentiment(
            score=0.0,
            label="Neutral",
            sentiment_summary="No recent news found.",
            news_items=[]
        )
        _news_cache[symbol] = (now, sentiment)
        return sentiment
    
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
        
    sentiment = NewsSentiment(
        score=round(avg_score, 2),
        label=label,
        sentiment_summary=summary,
        news_items=analyzed_items
    )
    
    # Update cache
    _news_cache[symbol] = (now, sentiment)
    return sentiment
