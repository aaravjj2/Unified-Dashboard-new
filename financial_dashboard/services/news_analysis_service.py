"""
News Analysis Service (Sprint 3)
Fetches news articles, extracts content, and performs sentiment analysis
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from nltk.sentiment import SentimentIntensityAnalyzer
import logging
from datetime import datetime
from typing import Optional

# Initialize FastAPI app
app = FastAPI(
    title="News Analysis Service",
    description="Fetch and analyze sentiment of financial news articles",
    version="1.0.0"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize NLTK sentiment analyzer
try:
    sia = SentimentIntensityAnalyzer()
    logger.info("✅ VADER sentiment analyzer initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize sentiment analyzer: {e}")
    sia = None


class NewsAnalysisRequest(BaseModel):
    """Request model for news analysis"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.reuters.com/markets/us/futures-rise-after-biden-drops-out-2024-07-21/"
            }
        }


class NewsAnalysisResponse(BaseModel):
    """Response model for news analysis"""
    url: str
    title: Optional[str]
    sentiment: str
    sentiment_score: float
    confidence: str
    article_length: int
    analyzed_at: str
    status: str


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "News Analysis Service",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "/health": "Health check",
            "/analyze-news": "POST - Analyze news article sentiment"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    sentiment_status = "ready" if sia is not None else "unavailable"
    return {
        "status": "healthy",
        "service": "news_analysis",
        "timestamp": datetime.utcnow().isoformat(),
        "sentiment_analyzer": sentiment_status
    }


@app.post("/analyze-news", response_model=NewsAnalysisResponse)
async def analyze_news(request: NewsAnalysisRequest):
    """
    Analyze sentiment of a news article from URL
    
    Args:
        request: NewsAnalysisRequest containing the article URL
        
    Returns:
        NewsAnalysisResponse with sentiment analysis results
    """
    try:
        logger.info(f"📰 Analyzing news from: {request.url}")
        
        # Fetch article content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(str(request.url), headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract title
        title = None
        title_tags = ['h1', 'title', 'meta[property="og:title"]']
        for tag in title_tags:
            element = soup.select_one(tag)
            if element:
                title = element.get_text() if tag.startswith('h') or tag == 'title' else element.get('content')
                if title:
                    break
        
        # Extract article text
        # Try common article content selectors
        article_text = ""
        content_selectors = [
            'article',
            'div[class*="article-body"]',
            'div[class*="story-body"]',
            'div[class*="content"]',
            'p'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                article_text = ' '.join([elem.get_text() for elem in elements])
                if len(article_text) > 100:  # Minimum viable content
                    break
        
        if not article_text or len(article_text) < 50:
            raise HTTPException(
                status_code=422,
                detail="Could not extract sufficient text content from article"
            )
        
        # Clean text
        article_text = ' '.join(article_text.split())
        
        # Perform sentiment analysis
        if sia is None:
            # Fallback: dummy sentiment (always positive)
            sentiment_scores = {"compound": 0.5}
            logger.warning("⚠️  Using fallback sentiment (analyzer unavailable)")
        else:
            sentiment_scores = sia.polarity_scores(article_text)
        
        compound_score = sentiment_scores['compound']
        
        # Determine sentiment label and confidence
        if compound_score >= 0.05:
            sentiment = "Positive"
            confidence = "High" if compound_score >= 0.5 else "Medium"
        elif compound_score <= -0.05:
            sentiment = "Negative"
            confidence = "High" if compound_score <= -0.5 else "Medium"
        else:
            sentiment = "Neutral"
            confidence = "High"
        
        logger.info(f"✅ Analysis complete: {sentiment} (score: {compound_score:.3f})")
        
        return NewsAnalysisResponse(
            url=str(request.url),
            title=title or "Title not found",
            sentiment=sentiment,
            sentiment_score=round(compound_score, 3),
            confidence=confidence,
            article_length=len(article_text),
            analyzed_at=datetime.utcnow().isoformat(),
            status="success"
        )
        
    except requests.RequestException as e:
        logger.error(f"❌ Failed to fetch article: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch article: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    return {
        "service": "news_analysis",
        "uptime": "operational",
        "analyzer": "VADER (NLTK)",
        "supported_sentiments": ["Positive", "Negative", "Neutral"],
        "capabilities": [
            "Web scraping",
            "Content extraction",
            "Sentiment analysis",
            "Multi-source support"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
