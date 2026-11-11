#!/usr/bin/env python3
"""
Sentiment Analysis Engine
Fetches news and performs sentiment analysis with source citations.
"""
import json
import sys
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
# For LLM-based sentiment, we'll use a fallback to TextBlob if transformers is not available
try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False
    print("Warning: TextBlob not installed, using a very basic fallback sentiment.", file=sys.stderr)

def fetch_news_headlines(ticker, days=7):
    """Fetch recent news headlines for the ticker from multiple sources."""
    # We'll use a combination of sources: Yahoo Finance news, and optionally others.
    # For simplicity, we'll use Yahoo Finance news and then try to get more from Google News (via scraping, but note ToS).
    # We'll focus on Yahoo Finance for now.
    try:
        # Extract the base symbol without .NS or .BO for Yahoo Finance
        base_ticker = ticker.replace('.NS', '').replace('.BO', '')
        url = f"https://finance.yahoo.com/quote/{base_ticker}/news?p={base_ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find news items (this is a simplified selector; may need adjustment)
        news_items = []
        for item in soup.find_all('li', {'class': 'js-stream-content'}):
            headline_elem = item.find('h3')
            if headline_elem:
                headline = headline_elem.get_text(strip=True)
                # Try to get the link and source
                link_elem = item.find('a', href=True)
                link = link_elem['href'] if link_elem else ''
                source_elem = item.find('div', {'class': 'C(#959595)'})
                source = source_elem.get_text(strip=True) if source_elem else 'Unknown'
                # Try to get the time (simplified)
                time_elem = item.find('time')
                time_str = time_elem['datetime'] if time_elem and time_elem.has_attr('datetime') else ''
                news_items.append({
                    'headline': headline,
                    'link': link,
                    'source': source,
                    'time': time_str
                })
        return news_items
    except Exception as e:
        print(f"Warning: Could not fetch news from Yahoo Finance: {e}")
        return []

def analyze_sentiment_textblob(text):
    """Analyze sentiment using TextBlob."""
    if not HAS_TEXTBLOB:
        return 0.0  # neutral
    blob = TextBlob(text)
    return blob.sentiment.polarity  # -1 to 1

def analyze_sentiment_llm(text):
    """
    Placeholder for LLM-based sentiment analysis.
    In a full implementation, you would use a model like distributilbert-base-uncased-finetuned-sst-2-english
    or a financial BERT model.
    For now, we fall back to TextBlob.
    """
    # If we had transformers, we would do:
    # from transformers import pipeline
    # sentiment_pipeline = pipeline("sentiment-analysis")
    # result = sentiment_pipeline(text)[0]
    # Convert label to score: POSITIVE -> 1, NEGATIVE -> -1, NEUTRAL -> 0
    # But since we don't have it, we use TextBlob.
    return analyze_sentiment_textblob(text)

def main(data):
    try:
        # Parse inputs
        hist_data = json.loads(data) if isinstance(data, str) else data
        ticker = hist_data.get('ticker', 'UNKNOWN')
        
        # Fetch news
        news_items = fetch_news_headlines(ticker, days=7)
        
        # If no news, try to get some from the ticker's name or fallback
        if not news_items:
            # We can try to get news from other sources, but for now, we note the absence.
            news_items = []
        
        # Analyze each headline
        sentiments = []
        for item in news_items:
            headline = item['headline']
            # Use LLM if available, else TextBlob
            sentiment_score = analyze_sentiment_llm(headline)
            sentiments.append({
                'headline': headline,
                'link': item.get('link', ''),
                'source': item.get('source', 'Unknown'),
                'time': item.get('time', ''),
                'sentiment_score': sentiment_score,
                'sentiment_label': 'positive' if sentiment_score > 0.1 else 'negative' if sentiment_score < -0.1 else 'neutral'
            })
        
        # Aggregate sentiment
        if sentiments:
            avg_sentiment = sum(item['sentiment_score'] for item in sentiments) / len(sentiments)
            # Also calculate the proportion of positive, negative, neutral
            pos_count = sum(1 for item in sentiments if item['sentiment_label'] == 'positive')
            neg_count = sum(1 for item in sentiments if item['sentiment_label'] == 'negative')
            neu_count = len(sentiments) - pos_count - neg_count
        else:
            avg_sentiment = 0.0
            pos_count = neg_count = neu_count = 0
        
        # Prepare result
        result = {
            'ticker': ticker,
            'news_items': sentiments,
            'summary': {
                'average_sentiment': avg_sentiment,
                'sentiment_label': 'positive' if avg_sentiment > 0.1 else 'negative' if avg_sentiment < -0.1 else 'neutral',
                'positive_count': pos_count,
                'negative_count': neg_count,
                'neutral_count': neu_count,
                'total_news_items': len(sentiments)
            },
            'note': 'Sentiment analysis based on news headlines from Yahoo Finance. Uses TextBlob for sentiment scoring (fallback).',
            'timestamp': datetime.now().isoformat()
        }
        
        return json.dumps(result)
    
    except Exception as e:
        print(f"Error in sentiment_engine: {e}", file=sys.stderr)
        error_result = {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        return json.dumps(error_result)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python sentiment_engine.py <data_json>")
        sys.exit(1)
    
    data = sys.argv[1]
    print(main(data))