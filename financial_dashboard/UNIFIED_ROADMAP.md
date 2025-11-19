# Unified Financial Dashboard - In-Depth Development Roadmap

This document outlines the strategic, sprint-based development plan, building upon the successful "Application Shell" refactoring. Each sprint has a clear goal and a set of implementation tasks to guide development.

---

## Sprint 0: Complete Foundational Refactoring

**Goal:** Finish the "Application Shell" migration for all remaining tabs and establish robust service management and testing infrastructure.

*   **Task 0.1: Refactor Remaining Tabs to "Application Shell"**
    *   **What:** Replicate the successful pattern used for "Market Trends" and "Analysis Hub" for the following services:
        1.  `market_forecast_app.py`
        2.  `portfolio_app.py`
        3.  `research_lab_app.py`
    *   For each, create a headless FastAPI backend service in the `services/` directory and a lightweight UI tab in the `tabs/` directory that communicates via the API Gateway.
    *   **Why:** This completes the architectural migration, ensuring the entire dashboard is stable, modular, and performant.

*   **Task 0.2: Finalize API Gateway Integration**
    *   **What:** Update `api_gateway.py` to include routing rules for the newly refactored services (Forecast, Portfolio, Research).
    *   **Why:** This centralizes all frontend-to-backend communication, simplifying the UI code and standardizing the API entry point.

*   **Task 0.3: Enhance Service Management Scripts**
    *   **What:**
        1.  Modify `start_all.sh` to use a polling health-check loop (`curl`) for each service instead of a fixed `sleep`.
        2.  Create `stop_all.sh` to read PIDs from a `pids/` directory and issue precise `kill` commands for reliable shutdowns.
    *   **Why:** This provides faster, more reliable application startup and shutdown, which is crucial for development and deployment.

*   **Task 0.4: Standardize Logging**
    *   **What:** Create a `utils/logging_config.py` module that defines a standard logging format. Import and apply this configuration in every service (`integrated_dashboard.py`, `api_gateway.py`, and all services in `services/`).
    *   **Why:** Ensures all log outputs are consistent, making them easier to parse, search, and debug across the entire distributed system.

*   **Task 0.5: Consolidate E2E Test Suite**
    *   **What:** Unify all existing Playwright tests into a single, organized suite in `tests/e2e/test_main_workflows.py`. Create a master `run_all_tests.sh` script to execute this suite.
    *   **Why:** Provides a single command to validate the entire application, which is essential for CI/CD and ensuring that new changes don't break existing functionality.

---

## Sprint 1: Centralized Data & Validation

**Goal:** Replace the fragile file-based data system with a production-grade central database and enforce data integrity.

*   **Task 1.1: Implement Central Database**
    *   **What:** Upgrade `utils/db_utils.py` to use **PostgreSQL**. The connection logic should read credentials from `keys.env`.
    *   **Why:** PostgreSQL is a scalable, concurrent database suitable for a multi-service architecture, replacing the limitations of file-based data and SQLite.

*   **Task 1.2: Migrate Historical Picks Data**
    *   **What:** Create a one-time script, `scripts/migrate_picks_to_db.py`, to parse all historical `picks_*.csv` files and load them into a new `picks_history` table in PostgreSQL.
    *   **Why:** Centralizes historical data, making it easier to manage, back up, and query for complex analysis.

*   **Task 1.3: Refactor Analysis Hub to Use Database**
    *   **What:** Modify the `services/analysis_service.py` to source its data directly from the `picks_history` table in PostgreSQL instead of scanning the filesystem.
    *   **Why:** Dramatically improves the performance and reliability of the Attribution Analysis feature.

*   **Task 1.4: Implement Data Validation Layer**
    *   **What:** Use a library like `pandera` to create data schemas for key data inputs (e.g., options chain data, trade requests). Validate data within the API services before processing.
    *   **Why:** Prevents corrupted or malformed data from causing downstream errors, making the system more robust.

---

## Sprint 2: Options System - Core Engine & Backtesting

**Goal:** Build the core backend services and strategy engine for the "Options Lab" feature.

*   **Task 2.1: Create Core Options Service (`options_service.py`)**
    *   **What:** A new, lightweight FastAPI application to orchestrate all options-related logic (data fetching, strategy application, risk checks, trade execution).
    *   **Why:** Centralizes options logic in a dedicated, scalable service.

*   **Task 2.2: Build API Clients (`finnhub_client.py`, `alpaca_trader.py`)**
    *   **What:** Create class-based clients for Finnhub (with caching and rate-limiting) and Alpaca (with paper/live modes).
    *   **Why:** Provides robust, reusable, and testable interfaces for all external market data and brokerage interactions.

*   **Task 2.3: Define Pluggable Strategy Engine**
    *   **What:**
        1.  Create an abstract base class `strategies/base_strategy.py` with a `generate_signals(self, data)` method.
        2.  Implement a sample `strategies/covered_call_screener.py` that inherits from the base class.
    *   **Why:** Establishes a flexible, "pluggable" architecture that allows new trading strategies to be added easily.

*   **Task 2.4: Build Lightweight Backtester (`backtester.py`)**
    *   **What:** A simple backtesting engine that takes a strategy object and historical data to simulate trades and calculate performance metrics (P&L, Sharpe ratio).
    *   **Why:** Enables quantitative validation of trading strategies against historical data before any capital is risked.

---

## Sprint 3: Options System - Risk Management & Alerting

**Goal:** Integrate critical safety features into the options trading system before enabling any live execution.

*   **Task 3.1: Create Risk Management Module (`utils/risk_manager.py`)**
    *   **What:** A module with a `check_trade_risk(trade)` method that enforces rules (max position size, daily loss limits) loaded from `options_config.yaml`.
    *   **Why:** Creates a mandatory safety gate for all trades to protect capital and prevent catastrophic errors.

*   **Task 3.2: Integrate Risk Manager into Trade Flow**
    *   **What:** Modify the `place_order` method in `utils/alpaca_trader.py` to call the risk manager before sending any order to the broker. The trade is rejected if it fails the risk check.
    *   **Why:** Ensures no trade can bypass the system's safety rules.

*   **Task 3.3: Create Generic Alerter (`utils/alerter.py`)**
    *   **What:** A simple module with a `send_alert(message, severity)` function that logs to the console and a file. It should be designed for easy extension to email or Slack.
    *   **Why:** Provides critical, real-time notifications for important events like trade executions, failures, and risk limit breaches.

---

## Sprint 4: Options System - Live UI & Monitoring

**Goal:** Build the comprehensive "Options Lab" user interface and connect it to the backend services for live paper-trading and monitoring.

*   **Task 4.1: Implement Live Execution Loop in `options_service.py`**
    *   **What:** Add an endpoint that runs the full automation cycle: fetch data -> generate signals -> validate risk -> execute trades.
    *   **Why:** Enables the core automated trading functionality.

*   **Task 4.2: Create Comprehensive "Options Lab" UI (`tabs/options_lab.py`)**
    *   **What:** Build a new Dash tab with three distinct panels:
        1.  **Strategy Monitor:** Displays the automated strategy's status, open positions, and recent activity logs. Includes controls to start/stop the strategy.
        2.  **Manual Trade Ticket:** An interactive UI to fetch live options chains, select contracts, and submit manual trades.
        3.  **P&L Analyzer:** A tool to visualize the profit/loss profile of any potential options trade.
    *   **Why:** Creates a central hub for all options activities, providing both powerful automation and essential manual control within a single, coherent UI.

*   **Task 4.3: Integrate Options Lab with API Gateway**
    *   **What:** Add routing rules to `api_gateway.py` for the `options_service.py` and ensure all callbacks in `tabs/options_lab.py` communicate through the gateway.
    *   **Why:** Fully integrates the new feature into the "Application Shell" architecture.

---

## Sprint 5: API Abstraction & Production Readiness

**Goal:** Refactor the system to be broker-agnostic and prepare for production deployment.

*   **Task 5.1: Define and Implement Broker Interface (`trading/base_broker.py`)**
    *   **What:** Create an abstract `BaseBroker` class with standardized methods like `execute_trade()` and `get_positions()`. Refactor the `AlpacaTrader` to implement this interface.
    *   **Why:** Decouples the application logic from any specific broker API, making it easy to add support for other brokers (e.g., Interactive Brokers) in the future.

*   **Task 5.2: Refactor Options Service to Use Interface**
    *   **What:** Update `options_service.py` to be programmed against the `BaseBroker` interface, not the concrete `AlpacaTrader` implementation.
    *   **Why:** Completes the broker-agnostic design, making the system highly modular and extensible.

*   **Task 5.3: Production Hardening (Initial Steps)**
    *   **What:**
        1.  Add basic authentication (e.g., API key in header) to the API Gateway.
        2.  Containerize the entire application using Docker and `docker-compose.yml`.
    *   **Why:** These are the first steps toward making the application secure and easily deployable in a production environment.

---

## Future Sprints (Backlog)

-   **Advanced Analytics:** Monte Carlo simulations, P&L attribution.
-   **Advanced Trading:** Multi-leg options strategies, additional order types.
-   **Operational Robustness:** CI/CD pipeline, secure secrets management (Vault), external alert channels (Email/Slack).
-   **User Experience:** Light/dark theme toggle, interactive cross-filtering, real-time WebSocket updates.

This roadmap provides a clear path from the current state to a feature-complete, robust, and scalable trading and analysis platform.