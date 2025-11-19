

## Options Trading System Roadmap for Claude Sonnet

This document provides precise, step-by-step instructions for Claude Sonnet to build a modular, extensible options trading system, and to run comprehensive tests for verification. Each sprint contains clear implementation tasks and validation steps. Follow each instruction exactly and ensure all code is testable and robust.

---


### Sprint 0: Foundational Stability & Refactoring


**Goal:** Eliminate technical debt, stabilize application startup, and establish a unified end-to-end test suite. This sprint is foundational for all future work.

**Task 0.1: Refactor `attribution_analysis.py`**
    - Break down the large, monolithic `attribution_analysis.py` file into: `attribution_tab.py`, `portfolio_tab.py`, and `scenario_tab.py`. Update `analysis_app.py` to import and compose layouts/callbacks from these modules.

**Task 0.2: Enhance Service Management Scripts**
    - Update `start_all.sh` to use a polling health-check loop (`curl`) for each service.
    - Create `stop_all.sh` to read PIDs from `pids/` and issue `kill` commands for precise shutdown.

**Task 0.3: Standardize Logging**
    - Create `utils/logging_config.py` for standardized logging. Import and apply in all services.

**Task 0.4: Consolidate E2E Test Suite**
    - Unify Playwright test scripts into `tests/e2e/test_main_workflows.py` using `pytest-playwright`.

**Task 0.5: Create Master Test Script**
    - Create `run_all_tests.sh` to execute all E2E and unit tests. This is the single source of truth for system validation.

---


### Sprint 1: Centralized Data & API Gateway

**Goal:** Mature the application's architecture by moving from a file-based data system to a robust central database and simplifying service communication with an API Gateway.

**Task 1.1: Implement Central Database**
    - Upgrade `utils/db_utils.py` to use PostgreSQL. Read credentials from `keys.env`.

**Task 1.2: Migrate Historical Data**
    - Create `scripts/migrate_picks_to_db.py` to load all historical `picks_*.csv` into a `picks_history` table in PostgreSQL. Update Attribution Analysis to use this table.

**Task 1.3: Introduce API Gateway**
    - Build a FastAPI API Gateway to proxy all frontend requests. Update `start_all.sh` to run this service.

**Task 1.4: Database & Gateway Tests**
    - Create `tests/test_db_migration.py` to verify CSV data loads into PostgreSQL.
    - Update E2E tests to use API Gateway URLs.

---


### Sprint 2: Pluggable Strategy Engine & Backtesting


**Goal:** Build a flexible strategy engine and a lightweight backtester to validate strategies.

**Task 2.1: Create Core Service (`options_service.py`)**
    * **What:** A new, lightweight FastAPI application to orchestrate all options-related logic (data fetching, strategy application, risk checks, trade execution).
    * **Why:** Centralizes options logic in a dedicated, scalable service, separate from the main dashboard UI.
    * **Integration:** Add this service to `start_all.sh` to run on a dedicated port (e.g., 8060) and register its routes with the API Gateway.

**Task 2.2: Centralize Options Configuration (`options_config.yaml`)**
    * **What:** Create a YAML file to store all options-specific configuration: API endpoints, strategy parameters, risk limits. The `options_service.py` will load this file at startup.
    * **Why:** Decouples configuration from code, making strategy adjustments, API changes, and risk parameter updates easy without code changes.

**Task 2.3: Build Finnhub Client (`utils/finnhub_client.py`)**
    * **What:** A class-based module to handle all Finnhub API calls (options chains, quotes, historical data). It will manage API key rotation and implement a simple disk-based cache to reduce redundant calls and respect rate limits.
    * **Why:** Provides a robust and rate-limit-aware interface for all external options market data.

**Task 2.4: Build Alpaca Trading Client (`utils/alpaca_trader.py`)**
    * **What:** A class-based module to encapsulate all trade execution logic. It must be initializable in `paper=True` (for testing) or `paper=False` (for live trading) mode. It will expose simple methods like `place_order()`, `get_positions()`, `get_order_status()`, and `get_account_details()`.
    * **Why:** Provides a secure and reliable interface for interacting with the broker, abstracting away API complexity.

**Task 2.5: Define Strategy Interface (`strategies/base_strategy.py`)**
    * **What:** Create an abstract base class `BaseStrategy` with a required method: `generate_signals(self, data)`. This method will take market data and return potential trade signals.
    * **Why:** This defines the "contract" that all future trading strategies must follow, ensuring they are pluggable and interchangeable.

**Task 2.6: Implement Sample Strategy (`strategies/covered_call_screener.py`)**
    * **What:** Create a concrete strategy class that inherits from `BaseStrategy`. Implement its `generate_signals` method with specific logic to identify potential covered call trades based on market conditions.
    * **Why:** Provides a working example of a strategy and allows for immediate testing of the strategy engine.

**Task 2.7: Build Lightweight Backtester (`backtester.py`)**
    * **What:** A simple backtesting engine that takes a strategy object, historical market data (from Finnhub or a database), and a date range. It will loop through the historical data, pass it to the strategy's `generate_signals` method, and simulate the resulting trades to calculate P&L and other performance metrics.
    * **Why:** Enables quantitative validation of strategy performance against historical data before risking real capital.

---


### Sprint 3: Risk Management & Alerting


**Goal:** Integrate safety features before enabling any live execution.

**Task 3.1: Create Risk Management Module (`utils/risk_manager.py`)**
    * **What:** A module with `check_trade_risk(trade)` and `check_position_risk(position)` methods. It will enforce rules such as maximum position size, daily/overall risk limits, and concentration limits (e.g., max % in one ticker). These rules will be loaded from `options_config.yaml`. The module will return an approval or a rejection with a detailed reason.
    * **Why:** Essential for preventing excessive losses and ensuring strategy adherence to predefined risk parameters.

**Task 3.2: Integrate Risk Manager**
    * **What:** Modify the `place_order` method in `utils/alpaca_trader.py` (and any other trade execution points in `options_service.py`) to explicitly call the risk manager before sending any order to the broker. If the risk manager rejects the trade, it will not be placed.
    * **Why:** Creates a mandatory safety gate for all trades, protecting capital.

**Task 3.3: Create Generic Alerter (`utils/alerter.py`)**
    * **What:** A simple module with a function `send_alert(message, severity, category)`. Initially, it will just log to the console and to a `logs/alerts.log` file, but it is designed for easy extension to send alerts via email (SMTP), Slack, or Telegram.
    * **Why:** Provides critical, real-time notifications for important events such as trade executions, failures, risk limit breaches, and unexpected market conditions, keeping the user informed.

---


### Sprint 4: Live Trading, Monitoring & Manual UI


**Goal:** Connect backend components for live paper-trading, build a comprehensive UI for monitoring and manual options trading.

**Task 4.1: Implement Live Execution Loop**
    * **What:** Add an endpoint (e.g., `/run_strategy`) to `options_service.py` that, when triggered (manually or on a schedule), runs the full automation cycle: fetch data -> generate signals -> validate risk -> execute trades -> send alerts. This endpoint can be called by a background worker or an external scheduler.
    * **Why:** Enables the core automated trading functionality.

**Task 4.2: Create Comprehensive Options Lab UI (`tabs/options_lab.py`)**
    * **What:** Build a new Dash tab (`tabs/options_lab.py`) to be integrated into the main dashboard. This tab will now be a central "Options Hub" with **sub-tabs or distinct panels** to serve multiple functions:
        * **2a. Automated Strategy Monitoring Panel:** This section will display data fetched from `options_service.py` API endpoints dedicated to monitoring. It will include:
            * A display of the automated strategy's current open positions (showing P/L, strike, expiration).
            * A status indicator for the automated strategy (e.g., "Running," "Paused," "Last Run: [Timestamp]," "Last Signal: BUY SPY Call").
            * A scrollable log or table of recent automated trade executions and any alerts issued by the `alerter.py` module.
            * Buttons to start/stop/pause the automated strategy loop (which calls the `/run_strategy` endpoint on `options_service`).
        * **2b. Manual Options Trade Ticket Panel:** Create a separate, distinct sub-tab or panel that directly mirrors and enhances the "Google Colab experience" for manual trading. This section will feature:
            * An input field for a stock ticker.
            * A dropdown to select an expiration date.
            * A table (`dash_table.DataTable`) to display the live options chain for the selected ticker/expiration, fetched directly via `finnhub_client.py` within the Dash app's callbacks.
            * Interactive elements (e.g., clicking a row in the options table pre-populates a "Trade Entry" form) for:
                * Entering `strike`, `quantity`, and selecting `Call/Put`.
                * Selecting `Buy/Sell`.
                * A button to `Submit Manual Trade` (which calls `alpaca_trader.py` directly through the Dash app's callbacks, with risk checks).
            * A section to display the user's **manually entered options positions** (clearly distinct from automated strategy positions, perhaps in a separate table or labeled as "Discretionary Trades").
        * **2c. P&L Visualization Panel (Phase 4 from original roadmap):** Integrate the "Visualize P/L" button and the Plotly chart modal here, providing critical risk/reward analysis for both manual and simulated trades.
    * **Why:** Creates a comprehensive central hub for all options activities, providing both powerful automation and essential manual control, all within a single, coherent UI.

---


### Sprint 5: API Abstraction & Refinement


**Goal:** Refactor for broker-agnostic design and streamlined interactions.

**Task 5.1: Define Broker Interface (`trading/base_broker.py`)**
    * **What:** Create an abstract base class `BaseBroker` with standardized methods like `execute_trade()`, `get_positions()`, `get_account_details()`, `get_order_status()`.
    * **Why:** Ensures all broker implementations provide a consistent interface, allowing the core `options_service.py` and strategy logic to work with any broker.

**Task 5.2: Refactor Alpaca Trader**
    * **What:** Modify the existing `AlpacaTrader` class in `utils/alpaca_trader.py` to formally implement the `BaseBroker` interface.
    * **Why:** Makes Alpaca one of potentially many interchangeable broker backends.

**Task 5.3: Refactor Options Service to Use Interface**
    * **What:** Update the `options_service.py` and any strategies to interact with the `BaseBroker` interface rather than directly with the `AlpacaTrader` implementation.
    * **Why:** Decouples the application logic from specific broker APIs, significantly improving modularity and future extensibility (e.g., easily add a Robinhood or Interactive Brokers client).

---



### Future Enhancements & Ideas

This section contains a backlog of improvements to be considered after the core system is operational. Each is categorized for clarity and direct implementation by Claude Sonnet.

## 🧠 Advanced Analytics & Strategy

- **Implement Monte Carlo Simulation:**
    - Simulate thousands of possible future market paths to predict portfolio risk and value ranges.
    - Use results to answer questions like "Probability of losing more than 20% in 3 months?"

- **Add P&L Attribution:**
    - Break down strategy returns by sector, volatility, and options Greeks (e.g., theta decay).
    - Integrate into the analysis tab for deeper performance insights.

- **Support Multi-Strategy Execution:**
    - Enhance `options_service` to run multiple strategies in parallel, each with its own capital allocation and risk limits in `options_config.yaml`.

- **Multi-leg Options Strategies:**
    - Add support for analyzing and trading spreads, straddles, and other complex options strategies.

## ⚙️ Operational Robustness & Security

- **Containerize the Entire Application (Docker):**
    - Wrap each service in a Docker container and manage with `docker-compose.yml`.

- **Implement a CI/CD Pipeline:**
    - Use GitHub Actions (or similar) to build containers, run all tests, and deploy on success.

- **Use a Secure Secrets Manager:**
    - Store API keys in HashiCorp Vault or a cloud secrets manager, not plain text files.

- **Database Integration (for Options):**
    - Use a database for persistent storage of options trade history, backtest results, and performance metrics.

- **Simulation Mode:**
    - Implement a "paper-live" mode that logs intended trades to the database without executing them.

- **Environment-based Configuration:**
    - Support multiple config files for dev, test, and prod environments.

- **API Usage Analytics:**
    - Track API calls to monitor costs and stay within rate limits.

- **Unit & Integration Testing:**
    - Add a dedicated suite of `pytest` tests for all critical modules and endpoints.

## ✨ User Experience (UX) & Interface

- **Add Advanced Order Types:**
    - Support Limit, Stop-Loss, and Trailing Stop orders in the manual Trade Ticket UI.

- **Implement Real-Time UI Alerts (Toast Notifications):**
    - Display immediate, visual feedback for trades and risk events as pop-up notifications in the dashboard.

- **Add Export/Reporting Functionality:**
    - Add "Download as CSV" buttons to portfolio and trade history tables for easy export.

- **Advanced Visualization Tools:**
    - Add options chain heatmaps, P&L profile charts, and other specialized visualizations.

- **Formal Plugin System:**
    - Automatically discover and load new strategy or data source modules from a `plugins/` directory.

- **Proactive Market Alerts:**
    - Monitor for and alert on unusual market conditions (e.g., volatility spikes, high options volume).

---


### Final Testing & Verification Instructions for Claude Sonnet

After completing all sprints, perform the following detailed tests to verify system correctness and robustness:

1. **Unit Tests:**
    - Run `pytest` on all modules, including utils, strategies, trading, and service code. Ensure 100% pass rate.
2. **Integration Tests:**
    - Run integration tests for API Gateway, database, options service, and broker interface. Validate end-to-end data flow and trade execution.
3. **E2E Tests:**
    - Run `pytest-playwright` on `tests/e2e/test_main_workflows.py` to validate all UI workflows, including automated and manual options trading, monitoring, and visualization.
4. **Service Startup/Shutdown:**
    - Run `start_all.sh` and confirm all services start and pass health checks.
    - Run `stop_all.sh` and confirm all services shut down cleanly (no zombie processes).
5. **Manual UI Verification:**
    - Open the dashboard in a browser, verify login, dashboard, portfolio, analysis hub, and options lab tabs function as described.
    - Test manual trade ticket, options chain loading, trade submission, and P&L visualization.
6. **Automated Strategy Verification:**
    - Start/pause/stop the automated strategy loop from the UI. Confirm trades are executed, risk checks are enforced, and logs/alerts are generated.
7. **Database Consistency:**
    - Verify all trades, positions, and historical data are correctly stored and retrievable from PostgreSQL.
8. **Logging Consistency:**
    - Check all logs for standardized format and completeness across services.
9. **API Documentation:**
    - Confirm FastAPI auto-generates API docs and all endpoints are documented and accessible.

If any test fails, debug and fix the issue before proceeding. Only consider the build complete when all tests and manual checks pass.

---

### Full Preview of the Final System

Here's a comprehensive vision of what your Unified Financial Dashboard will look like and how it will function once all these sprints are completed.

**1. Seamless Startup & Shutdown:**
* You'll run `start_all.sh`, and within seconds, all necessary services (Dash apps, API Gateway, Options Service, Celery workers) will spin up reliably, confirmed by health checks, not just a timer.
* `stop_all.sh` will gracefully shut down everything, leaving no zombie processes.

**2. A Single, Polished Entry Point:**
* You'll open your browser to a single URL (e.g., `http://localhost:8000`).
* A clean **login screen** greets you first, enabling personalized experiences.

**3. The Home Page / Dashboard:**
* After logging in, you'll land on a main dashboard displaying an overview of your portfolio.
* The **Portfolio tab** will be dynamic: `lastPrice` and `P/L` values for your holdings will **flash green/red in real-time** as market data updates via WebSockets.
* You can **click on chart segments** (e.g., a sector in a pie chart) to instantly filter related tables/data on the page, providing highly interactive exploration.
* A **Light/Dark theme toggle** in the header lets you instantly switch the entire UI's appearance.

**4. The Powerful "Analysis Hub":**
* The **"Attribution Analysis" and "Scenario Analysis" tabs** (now modularized) will be available.
* When you click "Run Analysis" on a complex scenario, it **won't freeze your UI**. Instead, a "Running..." message or spinner will appear, and the job will be handed off to a **Celery worker** for background processing. You can continue using other parts of the dashboard, and the results will populate when ready.

**5. The Centralized "Options Lab" (The Core of Your Request):**
* A prominent **"Options Lab" tab** will be available, acting as your comprehensive options trading and monitoring hub.
* **Sub-Tab 1: "Strategy Monitor"** (for the automated robot):
    * This panel will show the **current state of your automated trading strategies.**
    * You'll see a list of **open positions** managed by the robot (ticker, strike, expiration, P/L, etc.).
    * A status indicator will show if your strategy is "Running," "Paused," or "Idle," with details like "Last Trade: BUY GLD Put @ 10:30 AM."
    * A dedicated **log pane** will scroll through all recent automated trade executions and system alerts (e.g., "Risk limit reached for TSLA calls," "Finnhub API rate limit hit").
    * Buttons will allow you to **Start/Pause/Stop** the automated strategy's execution loop.
* **Sub-Tab 2: "Manual Trade Ticket"** (your Google Colab experience, but better):
    * This panel provides a **direct, hands-on options trading interface.**
    * An input box for a ticker (e.g., "TSLA"). As you type, a dropdown might suggest expirations.
    * Clicking "Get Chain" (or auto-loading) will populate a **live options chain table** (calls and puts) directly below.
    * You can **click on any row in this options chain table**, and a "Trade Entry Form" will automatically pre-populate with that contract's details (strike, type, symbol).
    * You'll then input `quantity`, select `Buy/Sell`, and click a `Submit Manual Trade` button.
    * A status message will confirm the Alpaca order or report any error (e.g., "Trade Submitted: TSLA call," or "Error: Insufficient buying power").
    * A separate table will show your **discretionary (manually placed) options positions**, clearly distinguished from the robot's positions.
* **Sub-Tab 3: "P&L Visualizer":**
    * This panel (or a modal from the Trade Ticket) will allow you to quickly visualize the **profit/loss profile of any options trade or strategy** (single leg initially, multi-leg later). You'll input details or select a trade, and a Plotly chart will dynamically show the P/L curve at expiration, helping you assess risk/reward visually.

**6. User Customization & Personalization:**
* You can create and manage **watchlists** of securities you're interested in, accessible from a dedicated tab.
* Your settings (like theme preference) might be saved based on your user profile.

**7. Robust & Extensible Backend:**
* Behind the scenes, all data is stored in a scalable **PostgreSQL database**.
* The system is highly **modular**. You can easily swap out `Finnhub` for another data provider or `Alpaca` for another broker (like Interactive Brokers) because the code is built on abstract interfaces.
* **API documentation** is automatically generated by FastAPI, providing a clear reference for all backend services.

In essence, your dashboard will evolve into a sophisticated, professional-grade platform that combines powerful automated trading capabilities with flexible, real-time manual control and analysis, all within a visually appealing and highly interactive user interface.
