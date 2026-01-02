"""
ML Performance Tracking
Stores and analyzes performance of AI recommendations.
"""

import sqlite3
import logging
import json
from datetime import datetime
import os
import pandas as pd

logger = logging.getLogger(__name__)

DB_PATH = 'ml_recommendations.db'

def init_db():
    """Initialize the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                ticker TEXT,
                spot_price REAL,
                strategy TEXT,
                confidence REAL,
                rationale TEXT,
                model_votes TEXT,
                actual_outcome REAL,
                pnl REAL
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("ML performance database initialized")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

def store_recommendation(ticker: str, spot_price: float, consensus: dict):
    """Store recommendation for later analysis."""
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        strategy = consensus.get('consensus_strategy', 'Unknown')
        confidence = consensus.get('confidence_score', 0)
        rationale = consensus.get('rationale', '')
        model_votes = json.dumps(consensus.get('model_votes', {}))
        
        c.execute('''
            INSERT INTO recommendations 
            (timestamp, ticker, spot_price, strategy, confidence, rationale, model_votes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, ticker, spot_price, strategy, confidence, rationale, model_votes))
        
        conn.commit()
        conn.close()
        logger.info(f"Stored recommendation for {ticker}")
    except Exception as e:
        logger.error(f"Error storing recommendation: {e}")

def get_performance_history():
    """Get history of recommendations."""
    try:
        if not os.path.exists(DB_PATH):
            return pd.DataFrame()
            
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM recommendations ORDER BY timestamp DESC", conn)
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return pd.DataFrame()
