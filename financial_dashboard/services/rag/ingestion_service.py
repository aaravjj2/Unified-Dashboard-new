"""
Automated RAG Data Ingestion Service

Periodically fetches financial news and documents, processes them, and updates the RAG index.
Runs as a background task within the dashboard or as a standalone service.

Features:
- News fetching from multiple sources (Alpaca, Finnhub, NewsAPI)
- SEC filings ingestion (if needed)
- Automatic chunking and indexing
- Configurable schedule (hourly, daily, etc.)
- Graceful error handling and logging
"""

import os
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class RAGDataIngestionService:
    """Background service for automated RAG data ingestion."""

    def __init__(self, index_dir: str = "data/rag_index", update_interval_hours: int = 6):
        """
        Initialize the ingestion service.

        Args:
            index_dir: Directory for RAG index storage
            update_interval_hours: Hours between automatic updates (default: 6)
        """
        self.index_dir = Path(index_dir)
        self.update_interval = update_interval_hours * 3600  # Convert to seconds
        self.running = False
        self.thread = None
        self.last_update = None

        # Load local keys.env as fallback (do not overwrite existing env vars)
        try:
            keys_path = os.path.join(os.getcwd(), 'keys.env')
            if os.path.exists(keys_path):
                with open(keys_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            if os.environ.get(k.strip()) is None:
                                os.environ[k.strip()] = v.strip()
                logger.info('✓ Loaded keys.env for ingestion service fallback')
        except Exception:
            pass

        # API keys from environment
        self.alpaca_key = os.getenv('APCA_API_KEY_ID')
        self.alpaca_secret = os.getenv('APCA_API_SECRET_KEY')
        self.finnhub_key = os.getenv('FINNHUB_API_KEY')
        self.newsapi_key = os.getenv('NEWSAPI_KEY')

        logger.info(f"📰 RAG Ingestion Service initialized (update interval: {update_interval_hours}h)")

    def _normalize_to_symbol_list(self, raw) -> List[str]:
        """Normalize different symbol representations into a list of UPPERCASE tickers."""
        if not raw:
            return []

        # If already a list/tuple, normalize elements
        if isinstance(raw, (list, tuple)):
            items = [str(x).strip().upper() for x in raw if x]
            return list(dict.fromkeys(items))

        # If string like 'AAPL,NVDA' or 'AAPL NVDA'
        if isinstance(raw, str):
            # Replace semi/pipe/space with comma to unify
            sep_fixed = raw.replace(';', ',').replace('|', ',')
            parts = [p.strip().upper() for p in sep_fixed.split(',') if p.strip()]
            if parts:
                return list(dict.fromkeys(parts))

        # Fallback: try to extract attribute 'symbols' or 'symbol' if object-like
        try:
            if hasattr(raw, 'symbols'):
                return self._normalize_to_symbol_list(getattr(raw, 'symbols'))
            if hasattr(raw, 'symbol'):
                return self._normalize_to_symbol_list(getattr(raw, 'symbol'))
        except Exception:
            pass

        return []

    def fetch_alpaca_news(self, symbols: Optional[List[str]] = None, days_back: int = 7) -> List[Dict]:
        """
        Fetch news from Alpaca News API.
        Supports two SDK variants: per-symbol param or general feed with article.symbols fields.

        Args:
            symbols: List of ticker symbols to fetch news for (None = general market news)
            days_back: Number of days to look back

        Returns:
            List of news articles with metadata
        """
        if not self.alpaca_key or not self.alpaca_secret:
            logger.warning("Alpaca credentials not configured, skipping Alpaca news")
            return []

        try:
            from alpaca.data import NewsClient

            client = NewsClient(self.alpaca_key, self.alpaca_secret)

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            articles = []

            # If symbols provided, attempt per-symbol query when SDK supports it
            if symbols:
                logger.info(f"Fetching Alpaca news for {len(symbols)} symbols (attempting per-symbol fetch)")
                for s in symbols:
                    try:
                        # Some SDK versions accept symbol param, others do not; prefer guarded call
                        try:
                            news = client.get_news(symbols=[s], start=start_date.isoformat(), end=end_date.isoformat(), limit=50)
                        except TypeError:
                            # Fallback to general call and filter by article.symbols
                            news = client.get_news(start=start_date.isoformat(), end=end_date.isoformat(), limit=200)

                        for article in news:
                            # Extract and normalize symbols from different article shapes
                            art_symbols = []
                            try:
                                if isinstance(article, dict):
                                    art_symbols = self._normalize_to_symbol_list(article.get('symbols') or article.get('symbol') or '')
                                else:
                                    art_symbols = self._normalize_to_symbol_list(getattr(article, 'symbols', None) or getattr(article, 'symbol', None))
                            except Exception:
                                art_symbols = []

                            # If per-symbol fetch was requested, skip articles that don't mention that symbol
                            if symbols and art_symbols and s.upper() not in [x.upper() for x in art_symbols]:
                                continue

                            # Extract fields robustly for dicts and objects
                            if isinstance(article, dict):
                                title = article.get('headline') or article.get('title') or ''
                                content_field = article.get('summary') or article.get('description') or ''
                                url_field = article.get('url') or article.get('link') or ''
                                created = article.get('created_at') or article.get('datetime')
                            else:
                                title = getattr(article, 'headline', None) or getattr(article, 'title', '')
                                content_field = getattr(article, 'summary', None) or getattr(article, 'description', '') or ''
                                url_field = getattr(article, 'url', None) or getattr(article, 'link', '')
                                created = getattr(article, 'created_at', None) or getattr(article, 'datetime', None)

                            # Normalize published time
                            pub_iso = ''
                            try:
                                if hasattr(created, 'isoformat'):
                                    pub_iso = created.isoformat()
                                elif isinstance(created, (int, float)):
                                    pub_iso = datetime.fromtimestamp(created).isoformat()
                                elif isinstance(created, str) and created:
                                    pub_iso = created
                            except Exception:
                                pub_iso = ''

                            articles.append({
                                'title': title or '',
                                'content': content_field or '',
                                'url': url_field or '',
                                'published_at': pub_iso,
                                'source': 'alpaca',
                                'symbols': art_symbols or [s]
                            })
                    except Exception as e:
                        logger.debug(f"Alpaca per-symbol fetch failed for {s}: {e}")

                logger.info(f"✅ Fetched {len(articles)} articles from Alpaca (per-symbol attempts)")
                return articles

            # No symbols or per-symbol attempts failed; fall back to general news fetch
            logger.info("Fetching general market news from Alpaca (fallback)")
            news = client.get_news(start=start_date.isoformat(), end=end_date.isoformat(), limit=200)

            for article in news:
                articles.append({
                    'title': getattr(article, 'headline', '') or getattr(article, 'title', ''),
                    'content': getattr(article, 'summary', '') or getattr(article, 'headline', ''),
                    'url': getattr(article, 'url', '') or getattr(article, 'link', ''),
                        'published_at': getattr(article, 'created_at', None).isoformat() if getattr(article, 'created_at', None) and hasattr(getattr(article, 'created_at', None), 'isoformat') else str(getattr(article, 'created_at', ''))
                    })

            logger.info(f"✅ Fetched {len(articles)} articles from Alpaca")
            return articles
        except Exception as e:
            logger.exception(f"Error fetching Alpaca news: {e}")
            return []

    def fetch_finnhub_news(self, category: str = 'general', days_back: int = 7) -> List[Dict]:
        """
        Fetch news from Finnhub general feed.

        Args:
            category: News category ('general', 'forex', 'crypto', 'merger')
            days_back: Number of days to look back

        Returns:
            List of news articles
        """
        if not self.finnhub_key:
            logger.warning("Finnhub API key not configured, skipping Finnhub news")
            return []

        try:
            import finnhub

            client = finnhub.Client(api_key=self.finnhub_key)

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Fetch market news: guard for SDK signature variants
            try:
                news = client.general_news(category)
                logger.debug("Finnhub: used general_news(category)")
            except TypeError:
                try:
                    news = client.general_news(category, 0)
                    logger.debug("Finnhub: used general_news(category, minId)")
                except TypeError as e:
                    logger.error(f"Finnhub.general_news signature not supported: {e}")
                    return []

            articles = []
            for article in news[:100]:  # Limit to 100 most recent
                pub_time = datetime.fromtimestamp(article.get('datetime', 0))

                # Filter by date range
                if pub_time < start_date:
                    continue

                related = article.get('related', '') if isinstance(article, dict) else ''
                symbols = self._normalize_to_symbol_list(related)

                articles.append({
                    'title': article.get('headline', ''),
                    'content': article.get('summary', article.get('headline', '')),
                    'url': article.get('url', ''),
                    'published_at': pub_time.isoformat(),
                    'source': 'finnhub',
                    'symbols': symbols
                })

            logger.info(f"✅ Fetched {len(articles)} articles from Finnhub")
            return articles

        except Exception as e:
            logger.error(f"Error fetching Finnhub news: {e}")
            return []

    def fetch_newsapi_business(self, query: str = "stock market OR earnings OR fed", days_back: int = 7) -> List[Dict]:
        """
        Fetch business news from NewsAPI.
        """
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured, skipping NewsAPI")
            return []

        try:
            from datetime import datetime, timedelta

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 100,
                'apiKey': self.newsapi_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            articles = []

            for article in data.get('articles', []):
                articles.append({
                    'title': article.get('title', ''),
                    'content': article.get('description', '') or article.get('content', ''),
                    'url': article.get('url', ''),
                    'published_at': article.get('publishedAt', ''),
                    'source': f"newsapi_{article.get('source', {}).get('name', 'unknown')}",
                    'symbols': []  # NewsAPI doesn't provide symbol tags
                })

            logger.info(f"✅ Fetched {len(articles)} articles from NewsAPI")
            return articles

        except Exception as e:
            logger.error(f"Error fetching NewsAPI articles: {e}")
            return []

    def fetch_yahoo_news(self, symbols: Optional[List[str]] = None, days_back: int = 3) -> List[Dict]:
        """
        Fetch recent headlines from Yahoo Finance for provided symbols (best-effort).

        Args:
            symbols: List of ticker symbols to fetch news for
            days_back: Number of days to look back

        Returns:
            List[news article dicts]
        """
        try:
            import yfinance as yf
        except Exception:
            logger.warning("yfinance not available, skipping Yahoo news")
            return []

        symbols = symbols or []
        articles = []
        cutoff = datetime.now() - timedelta(days=days_back)

        for s in symbols:
            try:
                t = yf.Ticker(s)
                news = getattr(t, 'news', None)
                logger.debug(f'fetch_yahoo_news: symbol={s} news_len={len(news) if news else 0}')
                if not news:
                    continue

                for item in news[:50]:
                    logger.debug(f'fetch_yahoo_news: symbol={s} item_keys={list(item.keys())}')
                    # yfinance news items often have nested 'content' dict with fields
                    content = item.get('content') if isinstance(item, dict) else {}
                    title = content.get('title') or item.get('title') or ''
                    summary = content.get('summary') or content.get('description') or item.get('summary') or ''

                    # canonical or clickThrough URL if present
                    url = None
                    if isinstance(content, dict):
                        url = (content.get('clickThroughUrl') or {}).get('url') if content.get('clickThroughUrl') else None
                        if not url:
                            url = (content.get('canonicalUrl') or {}).get('url') if content.get('canonicalUrl') else None

                    # published date
                    pub_date = content.get('pubDate') or content.get('displayTime') or item.get('pubDate')
                    pub_time = None
                    try:
                        if pub_date:
                            # ISO formatted date
                            from dateutil import parser as _parser
                            pub_time = _parser.parse(pub_date)
                            # Normalize to naive datetime for simple cutoff comparison
                            if getattr(pub_time, 'tzinfo', None) is not None:
                                pub_time = pub_time.astimezone(tz=None).replace(tzinfo=None)
                    except Exception:
                        pub_time = None

                    if pub_time and pub_time < cutoff:
                        continue

                    articles.append({
                        'title': title[:300],
                        'content': summary,
                        'url': url or '',
                        'published_at': pub_time.isoformat() if pub_time else '',
                        'source': 'yahoo',
                        'symbols': [s]
                    })
            except Exception as e:
                logger.debug(f"Yahoo news fetch failed for {s}: {e}")

        logger.info(f"✅ Fetched {len(articles)} Yahoo news items for {len(symbols)} symbols")
        return articles

    def process_and_ingest_articles(self, articles: List[Dict]) -> int:
        """
        Process articles and add them to the RAG index.

        Args:
            articles: List of article dictionaries

        Returns:
            Number of documents successfully ingested
        """
        if not articles:
            logger.info("No articles to ingest")
            return 0

        try:
            from financial_dashboard.agents.fingpt_ingest import ingest_documents, chunk_text
            from financial_dashboard.services.rag import update_index

            documents = []

            for article in articles:
                # Create document with metadata
                doc_id = f"{article['source']}_{hash(article['url'])}"

                # Combine title and content
                full_text = f"{article['title']}\n\n{article['content']}"

                # Chunk the text
                chunks = chunk_text(full_text, chunk_size=800, chunk_overlap=128)

                for idx, chunk in enumerate(chunks):
                    # Build metadata - include ticker when the article references a single symbol
                    symbols_list = article.get('symbols', []) or []
                    try:
                        # normalize to uppercase list
                        symbols_list = [s.strip().upper() for s in symbols_list if s]
                    except Exception:
                        symbols_list = []

                    metadata = {
                        'title': article['title'],
                        'source': article['source'],
                        'url': article['url'],
                        'published_at': article['published_at'],
                        'symbols': ','.join(symbols_list),
                        'chunk_index': idx,
                        'type': 'news'
                    }

                    # If exactly one symbol, add 'ticker' field so retrieval by ticker works
                    if len(symbols_list) == 1:
                        metadata['ticker'] = symbols_list[0]

                    documents.append({
                        'id': f"{doc_id}_chunk{idx}",
                        'text': chunk,
                        'metadata': metadata
                    })

            # Ingest into RAG index
            logger.info(f"📥 Ingesting {len(documents)} chunks from {len(articles)} articles")
            update_index(documents, index_dir=str(self.index_dir))

            logger.info(f"✅ Successfully ingested {len(documents)} document chunks")
            return len(documents)

        except Exception as e:
            logger.error(f"Error processing and ingesting articles: {e}")
            return 0

    def run_ingestion_cycle(self):
        """Run one complete ingestion cycle."""
        logger.info("🔄 Starting RAG ingestion cycle")
        cycle_start = time.time()

        try:
            # Fetch from all sources
            all_articles = []

            # Alpaca news (with major tickers)
            major_tickers = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'JPM']
            alpaca_articles = self.fetch_alpaca_news(symbols=major_tickers, days_back=3)
            all_articles.extend(alpaca_articles)

            # Finnhub general news
            finnhub_articles = self.fetch_finnhub_news(category='general', days_back=3)
            all_articles.extend(finnhub_articles)

            # Yahoo Finance headlines (per major tickers)
            yahoo_articles = self.fetch_yahoo_news(major_tickers, days_back=3)
            all_articles.extend(yahoo_articles)

            # NewsAPI business news
            newsapi_articles = self.fetch_newsapi_business(days_back=3)
            all_articles.extend(newsapi_articles)

            # Deduplicate articles by URL or title+published_at (allow items without URLs)
            seen_keys = set()
            unique_articles = []
            for article in all_articles:
                key = article.get('url') or (article.get('title', '').strip() + '|' + article.get('published_at', '').strip())
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    unique_articles.append(article)

            logger.info(f"📊 Collected {len(unique_articles)} unique articles from {len(all_articles)} total")

            # Process and ingest
            ingested_count = self.process_and_ingest_articles(unique_articles)

            # Update last run time
            self.last_update = datetime.now()

            elapsed = time.time() - cycle_start
            logger.info(f"✅ Ingestion cycle complete in {elapsed:.1f}s | Ingested: {ingested_count} chunks")

            return ingested_count

        except Exception as e:
            logger.error(f"❌ Ingestion cycle failed: {e}", exc_info=True)
            return 0

    def start(self):
        """Start the background ingestion service."""
        if self.running:
            logger.warning("Ingestion service already running")
            return

        logger.info("🚀 Starting RAG ingestion service")
        self.running = True

        def worker():
            # Run initial ingestion
            self.run_ingestion_cycle()

            # Then run on schedule
            while self.running:
                time.sleep(self.update_interval)
                if self.running:  # Check again after sleep
                    self.run_ingestion_cycle()

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()

        logger.info("✅ RAG ingestion service started")

    def stop(self):
        """Stop the background ingestion service."""
        if not self.running:
            return

        logger.info("🛑 Stopping RAG ingestion service")
        self.running = False

        if self.thread:
            self.thread.join(timeout=5)

        logger.info("✅ RAG ingestion service stopped")

    def get_status(self) -> Dict:
        """Get service status information."""
        return {
            'running': self.running,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'update_interval_hours': self.update_interval / 3600,
            'configured_sources': {
                'alpaca': bool(self.alpaca_key and self.alpaca_secret),
                'finnhub': bool(self.finnhub_key),
                'newsapi': bool(self.newsapi_key)
            }
        }


# Global service instance (singleton)
_ingestion_service = None


def get_ingestion_service() -> RAGDataIngestionService:
    """Get or create the global ingestion service instance."""
    global _ingestion_service

    if _ingestion_service is None:
        _ingestion_service = RAGDataIngestionService()

    return _ingestion_service


def start_ingestion_service(update_interval_hours: int = 6):
    """Start the global ingestion service."""
    service = get_ingestion_service()
    service.update_interval = update_interval_hours * 3600
    service.start()
    return service


def stop_ingestion_service():
    """Stop the global ingestion service."""
    global _ingestion_service

    if _ingestion_service:
        _ingestion_service.stop()
        _ingestion_service = None
