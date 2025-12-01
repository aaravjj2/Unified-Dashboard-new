"""
Bot Execution Scheduler Service
================================

Background task scheduler for trading bots with:
- APScheduler for job management
- State persistence with SQLite
- Real-time execution monitoring
- Performance tracking

Author: Enhanced Dashboard Team
Date: December 2025
"""

import logging
import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import APScheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.executors.pool import ThreadPoolExecutor
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not available. Install with: pip install apscheduler sqlalchemy")


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BotJob:
    """Represents a scheduled bot job."""
    job_id: str
    bot_id: str
    bot_type: str
    schedule_type: str  # 'interval', 'cron', 'once'
    schedule_config: Dict[str, Any]
    status: str = "pending"
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    total_pnl: float = 0.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BotStateDB:
    """SQLite database for bot state persistence."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = Path(__file__).parent.parent.parent / "data"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "bot_state.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bot configurations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_configs (
                bot_id TEXT PRIMARY KEY,
                bot_type TEXT NOT NULL,
                name TEXT,
                symbols TEXT,  -- JSON array
                config TEXT,   -- JSON config
                status TEXT DEFAULT 'stopped',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Bot jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_jobs (
                job_id TEXT PRIMARY KEY,
                bot_id TEXT NOT NULL,
                schedule_type TEXT,
                schedule_config TEXT,  -- JSON
                status TEXT DEFAULT 'pending',
                last_run TEXT,
                next_run TEXT,
                run_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id)
            )
        """)
        
        # Trade history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT NOT NULL,
                job_id TEXT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                pnl REAL DEFAULT 0,
                timestamp TEXT NOT NULL,
                order_id TEXT,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id)
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT NOT NULL,
                date TEXT NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                sharpe_ratio REAL DEFAULT 0,
                FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id),
                UNIQUE(bot_id, date)
            )
        """)
        
        # Execution logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT,
                job_id TEXT,
                level TEXT,
                message TEXT,
                details TEXT,  -- JSON
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Bot state database initialized at {self.db_path}")
    
    def save_bot_config(self, bot_id: str, bot_type: str, name: str, 
                        symbols: List[str], config: Dict) -> bool:
        """Save or update bot configuration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT OR REPLACE INTO bot_configs 
                (bot_id, bot_type, name, symbols, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM bot_configs WHERE bot_id = ?), ?
                ), ?)
            """, (bot_id, bot_type, name, json.dumps(symbols), 
                  json.dumps(config), bot_id, now, now))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save bot config: {e}")
            return False
    
    def get_bot_config(self, bot_id: str) -> Optional[Dict]:
        """Get bot configuration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT bot_id, bot_type, name, symbols, config, status, 
                       created_at, updated_at
                FROM bot_configs WHERE bot_id = ?
            """, (bot_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'bot_id': row[0],
                    'bot_type': row[1],
                    'name': row[2],
                    'symbols': json.loads(row[3]) if row[3] else [],
                    'config': json.loads(row[4]) if row[4] else {},
                    'status': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get bot config: {e}")
            return None
    
    def get_all_bots(self) -> List[Dict]:
        """Get all bot configurations."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT bot_id, bot_type, name, symbols, config, status, 
                       created_at, updated_at
                FROM bot_configs ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'bot_id': row[0],
                'bot_type': row[1],
                'name': row[2],
                'symbols': json.loads(row[3]) if row[3] else [],
                'config': json.loads(row[4]) if row[4] else {},
                'status': row[5],
                'created_at': row[6],
                'updated_at': row[7]
            } for row in rows]
        except Exception as e:
            logger.error(f"Failed to get all bots: {e}")
            return []
    
    def update_bot_status(self, bot_id: str, status: str) -> bool:
        """Update bot status."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE bot_configs 
                SET status = ?, updated_at = ?
                WHERE bot_id = ?
            """, (status, datetime.now().isoformat(), bot_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to update bot status: {e}")
            return False
    
    def log_trade(self, bot_id: str, job_id: str, symbol: str, side: str,
                  quantity: float, price: float, order_id: str = None,
                  pnl: float = 0, status: str = "executed") -> int:
        """Log a trade execution."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO bot_trades 
                (bot_id, job_id, symbol, side, quantity, price, pnl, 
                 timestamp, order_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (bot_id, job_id, symbol, side, quantity, price, pnl,
                  datetime.now().isoformat(), order_id, status))
            
            trade_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return trade_id
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
            return -1
    
    def get_bot_trades(self, bot_id: str, limit: int = 100) -> List[Dict]:
        """Get trade history for a bot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT trade_id, symbol, side, quantity, price, pnl, 
                       timestamp, order_id, status
                FROM bot_trades 
                WHERE bot_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (bot_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'trade_id': row[0],
                'symbol': row[1],
                'side': row[2],
                'quantity': row[3],
                'price': row[4],
                'pnl': row[5],
                'timestamp': row[6],
                'order_id': row[7],
                'status': row[8]
            } for row in rows]
        except Exception as e:
            logger.error(f"Failed to get bot trades: {e}")
            return []
    
    def get_bot_performance(self, bot_id: str) -> Dict:
        """Calculate bot performance metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get trade stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as max_profit,
                    MIN(pnl) as max_loss
                FROM bot_trades
                WHERE bot_id = ? AND status = 'executed'
            """, (bot_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] > 0:
                total_trades = row[0]
                winning_trades = row[1] or 0
                total_pnl = row[2] or 0
                avg_pnl = row[3] or 0
                max_profit = row[4] or 0
                max_loss = row[5] or 0
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                return {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': total_trades - winning_trades,
                    'win_rate': win_rate,
                    'total_pnl': total_pnl,
                    'avg_pnl': avg_pnl,
                    'max_profit': max_profit,
                    'max_loss': max_loss
                }
            
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'max_profit': 0,
                'max_loss': 0
            }
        except Exception as e:
            logger.error(f"Failed to get bot performance: {e}")
            return {}
    
    def log_execution(self, bot_id: str, job_id: str, level: str, 
                      message: str, details: Dict = None):
        """Log execution event."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO execution_logs 
                (bot_id, job_id, level, message, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (bot_id, job_id, level, message, 
                  json.dumps(details) if details else None,
                  datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log execution: {e}")
    
    def get_execution_logs(self, bot_id: str = None, limit: int = 100) -> List[Dict]:
        """Get execution logs."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if bot_id:
                cursor.execute("""
                    SELECT log_id, bot_id, job_id, level, message, details, timestamp
                    FROM execution_logs
                    WHERE bot_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (bot_id, limit))
            else:
                cursor.execute("""
                    SELECT log_id, bot_id, job_id, level, message, details, timestamp
                    FROM execution_logs
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'log_id': row[0],
                'bot_id': row[1],
                'job_id': row[2],
                'level': row[3],
                'message': row[4],
                'details': json.loads(row[5]) if row[5] else None,
                'timestamp': row[6]
            } for row in rows]
        except Exception as e:
            logger.error(f"Failed to get execution logs: {e}")
            return []


class BotScheduler:
    """
    Background scheduler for trading bots.
    Uses APScheduler with SQLite job store for persistence.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db = BotStateDB()
        self.scheduler = None
        self.bot_handlers: Dict[str, Callable] = {}
        self._running_jobs: Dict[str, Dict] = {}
        
        if SCHEDULER_AVAILABLE:
            self._init_scheduler()
        
        self._initialized = True
    
    def _init_scheduler(self):
        """Initialize APScheduler with SQLite job store."""
        try:
            db_dir = Path(__file__).parent.parent.parent / "data"
            db_dir.mkdir(exist_ok=True)
            job_store_path = str(db_dir / "scheduler_jobs.db")
            
            jobstores = {
                'default': SQLAlchemyJobStore(url=f'sqlite:///{job_store_path}')
            }
            executors = {
                'default': ThreadPoolExecutor(10)
            }
            job_defaults = {
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 60
            }
            
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='America/New_York'
            )
            
            logger.info("Bot scheduler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            self.scheduler = None
    
    def start(self):
        """Start the scheduler."""
        if self.scheduler and not self.scheduler.running:
            try:
                self.scheduler.start()
                logger.info("Bot scheduler started")
                
                # Restore saved bot jobs
                self._restore_jobs()
            except Exception as e:
                logger.error(f"Failed to start scheduler: {e}")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler and self.scheduler.running:
            try:
                self.scheduler.shutdown(wait=True)
                logger.info("Bot scheduler stopped")
            except Exception as e:
                logger.error(f"Failed to stop scheduler: {e}")
    
    def _restore_jobs(self):
        """Restore jobs for bots with 'running' status."""
        try:
            bots = self.db.get_all_bots()
            for bot in bots:
                if bot['status'] == 'running':
                    logger.info(f"Restoring job for bot: {bot['bot_id']}")
                    self.schedule_bot(
                        bot_id=bot['bot_id'],
                        bot_type=bot['bot_type'],
                        config=bot['config']
                    )
        except Exception as e:
            logger.error(f"Failed to restore jobs: {e}")
    
    def register_handler(self, bot_type: str, handler: Callable):
        """Register a handler function for a bot type."""
        self.bot_handlers[bot_type] = handler
        logger.info(f"Registered handler for bot type: {bot_type}")
    
    def schedule_bot(self, bot_id: str, bot_type: str, config: Dict,
                     schedule_type: str = 'interval', 
                     schedule_config: Dict = None) -> str:
        """
        Schedule a bot for execution.
        
        Args:
            bot_id: Unique bot identifier
            bot_type: Type of bot (momentum, mean_reversion, etc.)
            config: Bot configuration
            schedule_type: 'interval', 'cron', or 'once'
            schedule_config: Schedule configuration
                - interval: {'minutes': 5}
                - cron: {'hour': '9-16', 'minute': '*/5', 'day_of_week': 'mon-fri'}
                - once: {'run_date': '2025-12-01 09:30:00'}
        
        Returns:
            Job ID
        """
        if not self.scheduler:
            logger.error("Scheduler not available")
            return None
        
        # Default schedule: every 5 minutes during market hours
        if schedule_config is None:
            schedule_config = {
                'hour': '9-16',
                'minute': '*/5',
                'day_of_week': 'mon-fri'
            }
            schedule_type = 'cron'
        
        job_id = f"{bot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Create trigger based on schedule type
            if schedule_type == 'interval':
                trigger = IntervalTrigger(**schedule_config)
            elif schedule_type == 'cron':
                trigger = CronTrigger(**schedule_config)
            else:
                from apscheduler.triggers.date import DateTrigger
                trigger = DateTrigger(**schedule_config)
            
            # Add job to scheduler
            job = self.scheduler.add_job(
                self._execute_bot,
                trigger=trigger,
                id=job_id,
                name=f"Bot: {bot_id}",
                args=[bot_id, bot_type, config],
                replace_existing=True
            )
            
            # Track running job
            self._running_jobs[bot_id] = {
                'job_id': job_id,
                'bot_type': bot_type,
                'config': config,
                'schedule_type': schedule_type,
                'schedule_config': schedule_config,
                'started_at': datetime.now().isoformat()
            }
            
            # Update bot status
            self.db.update_bot_status(bot_id, 'running')
            self.db.log_execution(bot_id, job_id, 'INFO', 
                                  f'Bot scheduled with {schedule_type} trigger')
            
            logger.info(f"Scheduled bot {bot_id} with job {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to schedule bot {bot_id}: {e}")
            self.db.log_execution(bot_id, None, 'ERROR', 
                                  f'Failed to schedule bot: {str(e)}')
            return None
    
    def _execute_bot(self, bot_id: str, bot_type: str, config: Dict):
        """Execute a bot's trading logic."""
        job_id = self._running_jobs.get(bot_id, {}).get('job_id', 'unknown')
        
        try:
            self.db.log_execution(bot_id, job_id, 'INFO', 'Starting bot execution')
            
            # Get handler for this bot type
            handler = self.bot_handlers.get(bot_type)
            
            if handler:
                # Execute the bot handler
                result = handler(bot_id, config)
                
                if result:
                    # Log successful trades
                    if 'trades' in result:
                        for trade in result['trades']:
                            self.db.log_trade(
                                bot_id=bot_id,
                                job_id=job_id,
                                symbol=trade.get('symbol'),
                                side=trade.get('side'),
                                quantity=trade.get('quantity', 0),
                                price=trade.get('price', 0),
                                pnl=trade.get('pnl', 0),
                                order_id=trade.get('order_id'),
                                status='executed'
                            )
                    
                    self.db.log_execution(bot_id, job_id, 'INFO', 
                                          'Bot execution completed', result)
                else:
                    self.db.log_execution(bot_id, job_id, 'INFO', 
                                          'No trading signals generated')
            else:
                # Use default execution logic
                self._default_bot_execution(bot_id, bot_type, config, job_id)
                
        except Exception as e:
            logger.error(f"Bot execution failed for {bot_id}: {e}")
            self.db.log_execution(bot_id, job_id, 'ERROR', 
                                  f'Execution failed: {str(e)}')
    
    def _default_bot_execution(self, bot_id: str, bot_type: str, 
                                config: Dict, job_id: str):
        """Default bot execution logic."""
        try:
            from ..strategy_lab.trading_bot import TradingBot, BotConfig
            
            # Create bot instance
            bot_config = BotConfig(
                bot_id=bot_id,
                bot_type=bot_type,
                symbols=config.get('symbols', ['SPY']),
                position_size=config.get('position_size', 1000),
                max_positions=config.get('max_positions', 5),
                stop_loss_pct=config.get('stop_loss', 2.0),
                take_profit_pct=config.get('take_profit', 5.0),
                parameters=config.get('parameters', {})
            )
            
            bot = TradingBot(bot_config)
            signals = bot.generate_signals()
            
            if signals:
                self.db.log_execution(bot_id, job_id, 'INFO', 
                                      f'Generated {len(signals)} signals', 
                                      {'signals': signals})
                
                # Execute signals (paper trading)
                for signal in signals:
                    if signal.get('action') in ['buy', 'sell']:
                        self.db.log_trade(
                            bot_id=bot_id,
                            job_id=job_id,
                            symbol=signal['symbol'],
                            side=signal['action'].upper(),
                            quantity=signal.get('quantity', 1),
                            price=signal.get('price', 0),
                            status='simulated'
                        )
            else:
                self.db.log_execution(bot_id, job_id, 'INFO', 'No signals generated')
                
        except ImportError:
            self.db.log_execution(bot_id, job_id, 'WARNING', 
                                  'TradingBot not available, using mock execution')
        except Exception as e:
            self.db.log_execution(bot_id, job_id, 'ERROR', 
                                  f'Default execution failed: {str(e)}')
    
    def stop_bot(self, bot_id: str) -> bool:
        """Stop a scheduled bot."""
        try:
            job_info = self._running_jobs.get(bot_id)
            
            if job_info and self.scheduler:
                job_id = job_info['job_id']
                self.scheduler.remove_job(job_id)
                del self._running_jobs[bot_id]
            
            self.db.update_bot_status(bot_id, 'stopped')
            self.db.log_execution(bot_id, None, 'INFO', 'Bot stopped')
            
            logger.info(f"Stopped bot {bot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop bot {bot_id}: {e}")
            return False
    
    def pause_bot(self, bot_id: str) -> bool:
        """Pause a scheduled bot."""
        try:
            job_info = self._running_jobs.get(bot_id)
            
            if job_info and self.scheduler:
                job_id = job_info['job_id']
                self.scheduler.pause_job(job_id)
            
            self.db.update_bot_status(bot_id, 'paused')
            self.db.log_execution(bot_id, None, 'INFO', 'Bot paused')
            
            logger.info(f"Paused bot {bot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause bot {bot_id}: {e}")
            return False
    
    def resume_bot(self, bot_id: str) -> bool:
        """Resume a paused bot."""
        try:
            job_info = self._running_jobs.get(bot_id)
            
            if job_info and self.scheduler:
                job_id = job_info['job_id']
                self.scheduler.resume_job(job_id)
            
            self.db.update_bot_status(bot_id, 'running')
            self.db.log_execution(bot_id, None, 'INFO', 'Bot resumed')
            
            logger.info(f"Resumed bot {bot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume bot {bot_id}: {e}")
            return False
    
    def get_bot_status(self, bot_id: str) -> Dict:
        """Get comprehensive bot status."""
        config = self.db.get_bot_config(bot_id)
        performance = self.db.get_bot_performance(bot_id)
        recent_trades = self.db.get_bot_trades(bot_id, limit=10)
        recent_logs = self.db.get_execution_logs(bot_id, limit=20)
        
        job_info = self._running_jobs.get(bot_id, {})
        
        return {
            'config': config,
            'performance': performance,
            'recent_trades': recent_trades,
            'recent_logs': recent_logs,
            'job_info': job_info,
            'is_running': bot_id in self._running_jobs
        }
    
    def get_all_bot_statuses(self) -> List[Dict]:
        """Get status for all bots."""
        bots = self.db.get_all_bots()
        return [self.get_bot_status(bot['bot_id']) for bot in bots]
    
    def create_bot(self, name: str, bot_type: str, symbols: List[str],
                   config: Dict) -> str:
        """Create and save a new bot."""
        bot_id = f"{bot_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.db.save_bot_config(
            bot_id=bot_id,
            bot_type=bot_type,
            name=name,
            symbols=symbols,
            config=config
        )
        
        return bot_id


# Singleton accessor
def get_bot_scheduler() -> BotScheduler:
    """Get the bot scheduler instance."""
    return BotScheduler()


# Initialize scheduler on module load
_scheduler = None

def init_bot_scheduler():
    """Initialize and start the bot scheduler."""
    global _scheduler
    _scheduler = get_bot_scheduler()
    _scheduler.start()
    return _scheduler
