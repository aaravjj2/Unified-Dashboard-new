"""
Options Bot Scheduler - Automated Recipe Execution
===================================================

Background scheduler that runs Options Engine recipes automatically,
similar to OptionsAlpha's automation.

Features:
- Starts/stops bots from dashboard without Python scripts
- Runs in background thread (non-blocking)
- Checks conditions at configurable intervals
- Supports multiple concurrent bots
- Persists bot state to SQLite
- WebSocket events for real-time UI updates

Usage:
------
```python
from financial_dashboard.engines.options_engine.scheduler import OptionsScheduler

# Create scheduler
scheduler = OptionsScheduler()

# Create a recipe for GLD
recipe = create_short_put_spread_recipe(
    symbol="GLD",
    entry_condition="RSI < 30 AND VIX > 20"
)

# Start the bot (runs automatically!)
bot_id = scheduler.create_bot("GLD RSI Bot", recipe)
scheduler.start_bot(bot_id)

# Check status
status = scheduler.get_bot_status(bot_id)
print(f"Running: {status['is_running']}, Trades: {status['total_trades']}")
```
"""

from __future__ import annotations
import asyncio
import aiohttp
import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

from .schema import Recipe, TriggerType, create_short_put_spread_recipe
from .engine import RecipeExecutor, ExecutionEvent, ExecutorState
from .live_data import AlpacaDataHandler, create_live_data_handler
from .broker import PaperBroker

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class BotConfig:
    """Configuration for an options bot."""
    bot_id: str
    name: str
    symbol: str
    recipe_json: str
    status: str = "stopped"  # stopped, running, paused, error
    created_at: str = ""
    updated_at: str = ""
    check_interval: int = 60  # seconds between condition checks
    paper_mode: bool = True
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class BotStats:
    """Runtime statistics for a bot."""
    bot_id: str
    total_checks: int = 0
    conditions_met: int = 0
    trades_executed: int = 0
    total_pnl: float = 0.0
    last_check: str = ""
    last_trade: str = ""
    errors: int = 0


# =============================================================================
# SQLITE DATABASE
# =============================================================================

class OptionsBotDB:
    """SQLite database for options bot persistence."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_dir = Path("/home/aarav/Unified-Dashboard/data")
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "options_bots.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bot configurations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_configs (
                bot_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                recipe_json TEXT NOT NULL,
                status TEXT DEFAULT 'stopped',
                check_interval INTEGER DEFAULT 60,
                paper_mode INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Bot statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_stats (
                bot_id TEXT PRIMARY KEY,
                total_checks INTEGER DEFAULT 0,
                conditions_met INTEGER DEFAULT 0,
                trades_executed INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                last_check TEXT,
                last_trade TEXT,
                errors INTEGER DEFAULT 0,
                FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id)
            )
        """)
        
        # Trade history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                strategy TEXT,
                action TEXT,
                quantity INTEGER,
                price REAL,
                pnl REAL DEFAULT 0,
                timestamp TEXT,
                details TEXT,
                FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id)
            )
        """)
        
        # Event logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT NOT NULL,
                event_type TEXT,
                message TEXT,
                data TEXT,
                timestamp TEXT,
                FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Options bot database initialized at {self.db_path}")
    
    def save_bot(self, config: BotConfig) -> None:
        """Save or update bot configuration."""
        config.updated_at = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO bot_configs 
            (bot_id, name, symbol, recipe_json, status, check_interval, paper_mode, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            config.bot_id, config.name, config.symbol, config.recipe_json,
            config.status, config.check_interval, 1 if config.paper_mode else 0,
            config.created_at, config.updated_at
        ))
        
        # Initialize stats if needed
        cursor.execute("""
            INSERT OR IGNORE INTO bot_stats (bot_id) VALUES (?)
        """, (config.bot_id,))
        
        conn.commit()
        conn.close()
    
    def get_bot(self, bot_id: str) -> Optional[BotConfig]:
        """Get bot configuration by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT bot_id, name, symbol, recipe_json, status, check_interval, 
                   paper_mode, created_at, updated_at
            FROM bot_configs WHERE bot_id = ?
        """, (bot_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return BotConfig(
                bot_id=row[0],
                name=row[1],
                symbol=row[2],
                recipe_json=row[3],
                status=row[4],
                check_interval=row[5],
                paper_mode=bool(row[6]),
                created_at=row[7],
                updated_at=row[8]
            )
        return None
    
    def get_all_bots(self) -> List[BotConfig]:
        """Get all bot configurations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT bot_id, name, symbol, recipe_json, status, check_interval,
                   paper_mode, created_at, updated_at
            FROM bot_configs ORDER BY created_at DESC
        """)
        
        bots = []
        for row in cursor.fetchall():
            bots.append(BotConfig(
                bot_id=row[0],
                name=row[1],
                symbol=row[2],
                recipe_json=row[3],
                status=row[4],
                check_interval=row[5],
                paper_mode=bool(row[6]),
                created_at=row[7],
                updated_at=row[8]
            ))
        
        conn.close()
        return bots
    
    def update_bot_status(self, bot_id: str, status: str) -> None:
        """Update bot status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE bot_configs SET status = ?, updated_at = ? WHERE bot_id = ?
        """, (status, datetime.now().isoformat(), bot_id))
        
        conn.commit()
        conn.close()
    
    def delete_bot(self, bot_id: str) -> None:
        """Delete a bot and its data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM bot_trades WHERE bot_id = ?", (bot_id,))
        cursor.execute("DELETE FROM bot_events WHERE bot_id = ?", (bot_id,))
        cursor.execute("DELETE FROM bot_stats WHERE bot_id = ?", (bot_id,))
        cursor.execute("DELETE FROM bot_configs WHERE bot_id = ?", (bot_id,))
        
        conn.commit()
        conn.close()
    
    def get_stats(self, bot_id: str) -> BotStats:
        """Get bot statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT total_checks, conditions_met, trades_executed, total_pnl,
                   last_check, last_trade, errors
            FROM bot_stats WHERE bot_id = ?
        """, (bot_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return BotStats(
                bot_id=bot_id,
                total_checks=row[0],
                conditions_met=row[1],
                trades_executed=row[2],
                total_pnl=row[3],
                last_check=row[4] or "",
                last_trade=row[5] or "",
                errors=row[6]
            )
        return BotStats(bot_id=bot_id)
    
    def update_stats(self, stats: BotStats) -> None:
        """Update bot statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE bot_stats SET
                total_checks = ?, conditions_met = ?, trades_executed = ?,
                total_pnl = ?, last_check = ?, last_trade = ?, errors = ?
            WHERE bot_id = ?
        """, (
            stats.total_checks, stats.conditions_met, stats.trades_executed,
            stats.total_pnl, stats.last_check, stats.last_trade, stats.errors,
            stats.bot_id
        ))
        
        conn.commit()
        conn.close()
    
    def log_trade(self, bot_id: str, symbol: str, strategy: str, action: str,
                  quantity: int, price: float, pnl: float = 0, details: str = "") -> None:
        """Log a trade."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO bot_trades (bot_id, symbol, strategy, action, quantity, price, pnl, timestamp, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (bot_id, symbol, strategy, action, quantity, price, pnl, datetime.now().isoformat(), details))
        
        conn.commit()
        conn.close()
    
    def log_event(self, bot_id: str, event_type: str, message: str, data: dict = None) -> None:
        """Log an event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO bot_events (bot_id, event_type, message, data, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (bot_id, event_type, message, json.dumps(data or {}), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_recent_trades(self, bot_id: str, limit: int = 20) -> List[Dict]:
        """Get recent trades for a bot."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT trade_id, symbol, strategy, action, quantity, price, pnl, timestamp, details
            FROM bot_trades WHERE bot_id = ? ORDER BY timestamp DESC LIMIT ?
        """, (bot_id, limit))
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                "trade_id": row[0],
                "symbol": row[1],
                "strategy": row[2],
                "action": row[3],
                "quantity": row[4],
                "price": row[5],
                "pnl": row[6],
                "timestamp": row[7],
                "details": row[8],
            })
        
        conn.close()
        return trades
    
    def get_trades(self, bot_id: str, limit: int = 50) -> List[Dict]:
        """Alias for get_recent_trades."""
        return self.get_recent_trades(bot_id, limit)
    
    def get_events(self, bot_id: str, limit: int = 100) -> List[Dict]:
        """Alias for get_recent_events."""
        return self.get_recent_events(bot_id, limit)
    
    def get_recent_events(self, bot_id: str, limit: int = 50) -> List[Dict]:
        """Get recent events for a bot."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT event_id, event_type, message, data, timestamp
            FROM bot_events WHERE bot_id = ? ORDER BY timestamp DESC LIMIT ?
        """, (bot_id, limit))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "event_id": row[0],
                "event_type": row[1],
                "message": row[2],
                "data": json.loads(row[3]) if row[3] else {},
                "timestamp": row[4],
            })
        
        conn.close()
        return events


# =============================================================================
# OPTIONS BOT SCHEDULER
# =============================================================================

class OptionsScheduler:
    """
    Background scheduler for automated options trading bots.
    
    Runs recipes from the Options Engine without requiring
    any Python scripts - fully controlled from dashboard UI.
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        data_handler: Optional[AlpacaDataHandler] = None,
        broker: Optional[PaperBroker] = None,
    ):
        self.db = OptionsBotDB(db_path)
        self.data_handler = data_handler or create_live_data_handler()
        self.broker = broker or PaperBroker()
        
        # Runtime state
        self._running_bots: Dict[str, dict] = {}  # bot_id -> runtime info
        self._tasks: Dict[str, asyncio.Task] = {} # bot_id -> asyncio.Task
        self._lock = threading.Lock()
        
        # Asyncio Loop Management
        self.loop = asyncio.new_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=10) # For blocking calls
        self._loop_thread = threading.Thread(target=self._start_background_loop, daemon=True)
        self._loop_thread.start()
        
        # Event callbacks for UI updates
        self._event_callbacks: List[Callable[[str, dict], None]] = []
        
        # Auto-start bots that were running
        self._auto_start_bots()
        
        logger.info("OptionsScheduler initialized (Async Mode)")

    def _start_background_loop(self):
        """Run the asyncio event loop in a background thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def _auto_start_bots(self):
        """Restart bots that were running before shutdown."""
        for config in self.db.get_all_bots():
            if config.status == "running":
                logger.info(f"Auto-starting bot: {config.name}")
                self.start_bot(config.bot_id)
    
    # =========================================================================
    # BOT LIFECYCLE
    # =========================================================================
    
    def create_bot(
        self,
        name: str,
        recipe: Recipe,
        symbol: Optional[str] = None,
        check_interval: int = 60,
        paper_mode: bool = True,
    ) -> str:
        """
        Create a new options trading bot.
        
        Args:
            name: Display name for the bot
            recipe: Recipe object with conditions and actions
            symbol: Trading symbol (defaults to recipe's symbol)
            check_interval: Seconds between condition checks
            paper_mode: If True, use paper trading
            
        Returns:
            bot_id: Unique identifier for the bot
        """
        bot_id = f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        
        # Extract symbol from recipe if not provided
        if symbol is None:
            # Get from first action
            for action in recipe.actions:
                if hasattr(action, 'symbol'):
                    symbol = action.symbol
                    break
            if symbol is None:
                symbol = "SPY"  # Default
        
        config = BotConfig(
            bot_id=bot_id,
            name=name,
            symbol=symbol,
            recipe_json=recipe.model_dump_json(),
            check_interval=check_interval,
            paper_mode=paper_mode,
        )
        
        self.db.save_bot(config)
        self._emit_event(bot_id, "bot_created", {
            "name": name,
            "symbol": symbol,
        })
        
        logger.info(f"Created options bot: {name} ({bot_id}) for {symbol}")
        return bot_id
    
    def start_bot(self, bot_id: str) -> bool:
        """Start a bot's automated execution."""
        config = self.db.get_bot(bot_id)
        if not config:
            logger.error(f"Bot not found: {bot_id}")
            return False
        
        if bot_id in self._running_bots:
            logger.warning(f"Bot already running: {bot_id}")
            return True
        
        # Schedule the bot coroutine on the background loop
        asyncio.run_coroutine_threadsafe(self._start_bot_task(bot_id), self.loop)
        
        with self._lock:
            self._running_bots[bot_id] = {
                "started_at": datetime.now().isoformat(),
                "config": config,
            }
        
        self.db.update_bot_status(bot_id, "running")
        self._emit_event(bot_id, "bot_started", {"name": config.name})
        
        logger.info(f"Started bot: {config.name} ({bot_id})")
        return True

    async def _start_bot_task(self, bot_id):
        """Helper to create task in the loop."""
        task = asyncio.create_task(self._run_bot_loop_async(bot_id))
        self._tasks[bot_id] = task
    
    def stop_bot(self, bot_id: str) -> bool:
        """Stop a bot's execution."""
        if bot_id not in self._running_bots:
            logger.warning(f"Bot not running: {bot_id}")
            return False
        
        # Cancel the task via the loop
        asyncio.run_coroutine_threadsafe(self._stop_bot_task(bot_id), self.loop)
        
        # Clean up
        with self._lock:
            self._running_bots.pop(bot_id, None)
        
        self.db.update_bot_status(bot_id, "stopped")
        
        config = self.db.get_bot(bot_id)
        self._emit_event(bot_id, "bot_stopped", {"name": config.name if config else bot_id})
        
        logger.info(f"Stopped bot: {bot_id}")
        return True

    async def _stop_bot_task(self, bot_id):
        """Helper to cancel task in the loop."""
        if bot_id in self._tasks:
            self._tasks[bot_id].cancel()
            try:
                await self._tasks[bot_id]
            except asyncio.CancelledError:
                pass
            del self._tasks[bot_id]
    
    def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot completely."""
        # Stop if running
        if bot_id in self._running_bots:
            self.stop_bot(bot_id)
        
        self.db.delete_bot(bot_id)
        self._emit_event(bot_id, "bot_deleted", {})
        
        logger.info(f"Deleted bot: {bot_id}")
        return True
    
    # =========================================================================
    # BOT EXECUTION LOOP
    # =========================================================================
    
    async def _run_bot_loop_async(self, bot_id: str):
        """Main execution loop for a bot (runs in asyncio task)."""
        # Run DB access in executor
        config = await self.loop.run_in_executor(self.executor, self.db.get_bot, bot_id)
        if not config:
            return
        
        try:
            # Parse recipe
            recipe = Recipe.model_validate_json(config.recipe_json)
            
            # Create executor for this bot
            # Note: RecipeExecutor init is lightweight, but load_recipe might do I/O?
            # Let's assume it's safe or wrap it if needed.
            executor = RecipeExecutor(
                data_handler=self.data_handler,
                broker=self.broker,
            )
            
            # Load the recipe and get the context
            # Running in executor just in case
            context = await self.loop.run_in_executor(self.executor, executor.load_recipe, recipe)
            
            # Start the bot (sets state to RUNNING)
            executor.start(context.bot_id)
            
            logger.info(f"Bot {config.name} starting execution loop (interval={config.check_interval}s)")
            
            while True:
                try:
                    # Check market status (run in executor)
                    market_status = await self.loop.run_in_executor(self.executor, self.data_handler.get_market_status)
                    
                    # Only check conditions when market is open
                    # (Or always check if configured)
                    if market_status.get("is_open", False) or os.environ.get("BOT_ALWAYS_CHECK", "0") == "1":
                        # Run the check in executor
                        await self.loop.run_in_executor(
                            self.executor, 
                            self._execute_check, 
                            bot_id, executor, config, recipe, context.bot_id
                        )
                    else:
                        await self.loop.run_in_executor(
                            self.executor,
                            self.db.log_event,
                            bot_id, "market_closed", "Market is closed, skipping check"
                        )
                    
                    # Wait for next interval
                    await asyncio.sleep(config.check_interval)
                    
                except asyncio.CancelledError:
                    logger.info(f"Bot {config.name} task cancelled")
                    raise
                except Exception as e:
                    logger.exception(f"Error in bot loop for {bot_id}")
                    await self.loop.run_in_executor(self.executor, self._increment_error, bot_id)
                    await self.loop.run_in_executor(self.executor, self.db.log_event, bot_id, "error", str(e))
                    
                    # Back off on errors
                    await asyncio.sleep(30)
            
        except asyncio.CancelledError:
            logger.info(f"Bot {config.name} execution loop stopped")
        except Exception as e:
            logger.exception(f"Fatal error in bot {bot_id}")
            await self.loop.run_in_executor(self.executor, self.db.update_bot_status, bot_id, "error")
            await self.loop.run_in_executor(self.executor, self.db.log_event, bot_id, "fatal_error", str(e))
    
    def _execute_check(
        self,
        bot_id: str,
        executor: RecipeExecutor,
        config: BotConfig,
        recipe: Recipe,
        context_bot_id: str
    ):
        """Execute a single condition check and potential trade."""
        stats = self.db.get_stats(bot_id)
        stats.total_checks += 1
        stats.last_check = datetime.now().isoformat()
        
        try:
            # Get current market data for logging
            quote = self.data_handler.get_quote(config.symbol)
            rsi = self.data_handler.get_indicator(config.symbol, "RSI", 14)
            
            self.db.log_event(bot_id, "check", f"Price: ${quote.price}, RSI: {rsi.value:.1f}", {
                "price": quote.price,
                "rsi": rsi.value,
                "timestamp": datetime.now().isoformat(),
            })
            
            # Trigger the executor with the correct context bot_id
            trigger_result = executor.trigger(bot_id=context_bot_id)
            
            # Extract result for this specific bot
            bot_result = trigger_result.get(context_bot_id, {})
            triggered = bot_result.get("triggered", False)
            conditions_met = bot_result.get("conditions_met", False)
            actions = bot_result.get("actions_executed", [])
            
            if conditions_met:
                stats.conditions_met += 1
                
                # Check if any actions were executed
                if actions:
                    stats.trades_executed += len(actions)
                    stats.last_trade = datetime.now().isoformat()
                    
                    for action in actions:
                        self.db.log_trade(
                            bot_id=bot_id,
                            symbol=config.symbol,
                            strategy=action.get("type", "unknown"),
                            action="OPEN",
                            quantity=1,
                            price=quote.price,
                            details=json.dumps(action)
                        )
                    
                    self._emit_event(bot_id, "trade_executed", {
                        "actions": actions,
                        "price": quote.price,
                    })
                    
                    logger.info(f"Bot {config.name} executed trade: {actions}")
            
            self.db.update_stats(stats)
            
        except Exception as e:
            logger.error(f"Check failed for {bot_id}: {e}")
            stats.errors += 1
            self.db.update_stats(stats)
            raise
    
    def _increment_error(self, bot_id: str):
        """Increment error count."""
        stats = self.db.get_stats(bot_id)
        stats.errors += 1
        self.db.update_stats(stats)
    
    # =========================================================================
    # STATUS & QUERIES
    # =========================================================================
    
    def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """Get comprehensive status for a bot."""
        config = self.db.get_bot(bot_id)
        if not config:
            return {"error": "Bot not found"}
        
        stats = self.db.get_stats(bot_id)
        trades = self.db.get_recent_trades(bot_id, limit=5)
        events = self.db.get_recent_events(bot_id, limit=10)
        
        # Get live data for symbol
        try:
            quote = self.data_handler.get_quote(config.symbol)
            rsi = self.data_handler.get_indicator(config.symbol, "RSI", 14)
            live_data = {
                "price": quote.price,
                "change": quote.change,
                "change_pct": quote.change_pct,
                "rsi": rsi.value,
            }
        except Exception:
            live_data = {}
        
        return {
            "bot_id": bot_id,
            "name": config.name,
            "symbol": config.symbol,
            "status": config.status,
            "is_running": bot_id in self._running_bots,
            "paper_mode": config.paper_mode,
            "check_interval": config.check_interval,
            "created_at": config.created_at,
            "stats": asdict(stats),
            "live_data": live_data,
            "recent_trades": trades,
            "recent_events": events,
        }
    
    def get_all_bots_status(self) -> List[Dict[str, Any]]:
        """Get status for all bots."""
        return [self.get_bot_status(c.bot_id) for c in self.db.get_all_bots()]
    
    def get_running_bots(self) -> List[str]:
        """Get list of running bot IDs."""
        return list(self._running_bots.keys())
    
    def get_trade_log(self, bot_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get trade log for a bot."""
        return self.db.get_trades(bot_id, limit=limit)
    
    def get_event_log(self, bot_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get event log for a bot."""
        return self.db.get_events(bot_id, limit=limit)
    
    # =========================================================================
    # MANUAL TRIGGER
    # =========================================================================
    
    def trigger_once(self, bot_id: str) -> Dict[str, Any]:
        """
        Manually trigger a bot check once.
        
        Useful for testing without waiting for interval.
        """
        config = self.db.get_bot(bot_id)
        if not config:
            return {"error": "Bot not found"}
        
        try:
            recipe = Recipe.model_validate_json(config.recipe_json)
            executor = RecipeExecutor(
                data_handler=self.data_handler,
                broker=self.broker,
            )
            
            # Load recipe and get context
            context = executor.load_recipe(recipe)
            
            # Start the bot (sets state to RUNNING)
            executor.start(context.bot_id)
            
            # Get current data
            quote = self.data_handler.get_quote(config.symbol)
            rsi = self.data_handler.get_indicator(config.symbol, "RSI", 14)
            
            # Execute with correct bot_id
            trigger_result = executor.trigger(bot_id=context.bot_id)
            
            # Extract the result for this specific bot
            bot_result = trigger_result.get(context.bot_id, {})
            triggered = bot_result.get("triggered", False)
            conditions_met = bot_result.get("conditions_met", False)
            actions = bot_result.get("actions_executed", [])
            
            # Update stats if conditions were met
            if conditions_met:
                stats = self.db.get_stats(bot_id)
                stats.conditions_met += 1
                if actions:
                    stats.trades_executed += len(actions)
                    stats.last_trade = datetime.now().isoformat()
                    
                    # Log trades
                    for action in actions:
                        self.db.log_trade(
                            bot_id=bot_id,
                            symbol=config.symbol,
                            strategy=action.get("type", "unknown"),
                            action="OPEN",
                            quantity=1,
                            price=quote.price,
                            details=json.dumps(action)
                        )
                self.db.update_stats(stats)
            
            return {
                "success": True,
                "triggered": triggered,
                "conditions_met": conditions_met,
                "price": quote.price,
                "rsi": rsi.value,
                "actions_executed": actions,
                "result": bot_result,
            }
            
        except Exception as e:
            logger.exception(f"Manual trigger failed for {bot_id}")
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # EVENT SYSTEM
    # =========================================================================
    
    def on_event(self, callback: Callable[[str, dict], None]) -> None:
        """Register callback for bot events (for UI updates)."""
        self._event_callbacks.append(callback)
    
    def _emit_event(self, bot_id: str, event_type: str, data: dict) -> None:
        """Emit event to all callbacks."""
        event = {
            "bot_id": bot_id,
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.db.log_event(bot_id, event_type, json.dumps(data), data)
        
        for callback in self._event_callbacks:
            try:
                callback(bot_id, event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def stop_all(self):
        """Stop all running bots."""
        for bot_id in list(self._running_bots.keys()):
            self.stop_bot(bot_id)
    
    def __del__(self):
        """Cleanup on destruction."""
        self.stop_all()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_scheduler: Optional[OptionsScheduler] = None

def get_options_scheduler() -> OptionsScheduler:
    """Get or create the global options scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = OptionsScheduler()
    return _scheduler


# =============================================================================
# CONVENIENCE FUNCTIONS FOR DASHBOARD
# =============================================================================

def create_gld_rsi_bot(
    name: str = "GLD RSI Strategy",
    rsi_threshold: float = 30.0,
    check_interval: int = 60,
    require_market_hours: bool = True,
) -> str:
    """
    Create a pre-configured GLD RSI bot.
    
    Strategy: Open short put spread when RSI > rsi_threshold
    
    Args:
        name: Bot display name
        rsi_threshold: RSI value to trigger trade
        check_interval: Seconds between condition checks
        require_market_hours: If False, allow trades outside market hours (for testing)
    """
    recipe = create_short_put_spread_recipe(
        symbol="GLD",
        rsi_threshold=rsi_threshold,
        require_market_hours=require_market_hours,
    )
    
    scheduler = get_options_scheduler()
    return scheduler.create_bot(
        name=name,
        recipe=recipe,
        symbol="GLD",
        check_interval=check_interval,
    )


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Testing OptionsScheduler with GLD")
    print("=" * 60)
    
    # Create scheduler
    scheduler = get_options_scheduler()
    
    # Create a GLD bot
    bot_id = create_gld_rsi_bot(
        name="Test GLD Bot",
        rsi_threshold=30,
        check_interval=10,  # Fast for testing
    )
    
    print(f"\n✅ Created bot: {bot_id}")
    
    # Get status
    status = scheduler.get_bot_status(bot_id)
    print(f"\n📊 Status:")
    print(f"  Name: {status['name']}")
    print(f"  Symbol: {status['symbol']}")
    print(f"  Running: {status['is_running']}")
    
    # Start the bot
    print("\n🚀 Starting bot...")
    scheduler.start_bot(bot_id)
    
    # Let it run for a bit
    print("⏳ Running for 30 seconds...")
    time.sleep(30)
    
    # Check status
    status = scheduler.get_bot_status(bot_id)
    print(f"\n📊 After 30 seconds:")
    print(f"  Total Checks: {status['stats']['total_checks']}")
    print(f"  Conditions Met: {status['stats']['conditions_met']}")
    print(f"  Trades: {status['stats']['trades_executed']}")
    
    # Stop
    print("\n🛑 Stopping bot...")
    scheduler.stop_bot(bot_id)
    
    print("\n" + "=" * 60)
    print("✅ OptionsScheduler Test Complete")
    print("=" * 60)
