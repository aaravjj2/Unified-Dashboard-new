# Comprehensive Development Roadmap

This document outlines the strategic, sprint-based development plan for the Unified Financial Dashboard. Each sprint has a clear goal, a set of implementation tasks, and a corresponding set of validation tasks. This structure ensures that development is iterative, test-driven, and results in a stable, scalable, and feature-rich platform.

---

## Sprint 0: Foundational Stability & Refactoring

**Goal:** Eliminate the most critical technical debt, stabilize the core application startup, and establish a clean, consolidated end-to-end testing suite. This sprint is foundational for all future work.

*   **Task 0.1 (Implementation): Complete `attribution_analysis.py` Refactoring**
    *   **What:** Break down the large, monolithic `attribution_analysis.py` file into smaller, more focused modules: `attribution_tab.py`, `portfolio_tab.py`, and `scenario_tab.py`. The main `analysis_app.py` will import and compose the layouts and callbacks from these smaller files.
    *   **Why:** The current file is over 1300 lines and handles three distinct features, making it extremely difficult to debug and maintain. This refactoring will isolate concerns, improve code readability, and make it easier to add new features to each analysis section independently.

*   **Task 0.2 (Implementation): Enhance Service Management Scripts**
    *   **What:**
        1.  Modify `start_all.sh` to replace the fixed `sleep 10` with a polling health-check loop that uses `curl` to verify each service is responsive before declaring success.
        2.  Create a new `stop_all.sh` script. This script will read from a `pids/` directory where each service, upon startup, writes its own Process ID (PID) file (e.g., `analysis_app.pid`). The stop script will read these PIDs and issue a `kill` command to each, ensuring precise and reliable shutdowns.
    *   **Why:** Polling provides a faster and more reliable startup. Using PID files is a robust industry practice that is much safer than the brittle `pkill -f` approach, which can terminate unintended processes.

*   **Task 0.3 (Implementation): Standardize Logging**
    *   **What:** Create a `utils/logging_config.py` module. This module will define a standardized logging format and configuration. Each application (`analysis_app.py`, `portfolio_app.py`, etc.) will import and apply this configuration at startup.
    *   **Why:** This ensures all log outputs across all microservices are consistent in format, making them easier to parse, search, and debug.

*   **Task 0.4 (Validation): Consolidate the E2E Test Suite**
    *   **What:** Unify the various Playwright test scripts (`test_three_issues.py`, `test_final_verification.py`, `test_comprehensive_clicker.py`, etc.) into a single, organized test suite using `pytest-playwright`. Create a new file `tests/e2e/test_main_workflows.py`.
----
----
----
    *   **Why:** The current tests have significant overlap. Consolidation will reduce maintenance overhead, make the test suite faster to run, and provide a clearer picture of overall test coverage that can be run reliably after every change.

*   **Task 0.5 (Validation): Create Master Test Script**
    *   **What:** Create a `run_all_tests.sh` script that executes the consolidated `pytest-playwright` suite and any other unit tests (`pytest`). This script will be the single source of truth for validating the system's health.
    *   **Why:** This provides a simple, one-command way to ensure the entire application is stable, which is crucial for CI/CD and pre-deployment checks.

---

## Sprint 1: Centralized Data, Validation & API Gateway

**Goal:** Mature the application's architecture by moving to a robust central database, **enforcing data integrity**, and simplifying service communication with an API Gateway.

*   **Task 1.1 (Implementation): Implement Central Database**
    *   **What:** The existing `utils/db_utils.py` uses SQLite. Upgrade this to use **PostgreSQL** for better scalability and concurrent access. Update the connection logic to read credentials from `keys.env`.
    *   **Why:** PostgreSQL is a production-grade database that is more suitable for a multi-service application than a file-based SQLite database.

*   **Task 1.2 (Implementation): Implement Data Validation Layer**
    *   **What:** Create data schemas using `pandera` for key data sources (e.g., picks CSVs). Validate data upon loading in functions like `_load_and_enrich_picks` and before database insertion.
    *   **Why:** Prevents corrupted or malformed data from causing downstream errors, making the entire system more robust.

*   **Task 1.3 (Implementation): Migrate Historical Data**
    *   **What:** Create a one-time script `scripts/migrate_picks_to_db.py`. This script will parse all historical `picks_*.csv` files and load them into a new `picks_history` table in the PostgreSQL database. Modify the "Attribution Analysis" tab to source its data from this table instead of the filesystem.
    *   **Why:** This centralizes all historical data, making it easier to manage, back up, and analyze performance over long periods.

*   **Task 1.4 (Implementation): Introduce API Gateway**
    *   **What:** Create a new, lightweight **FastAPI** application to act as an API Gateway. This gateway will be the single entry point for all frontend requests. Initially, it will simply proxy requests to the appropriate backend Dash/Flask services (e.g., `/api/portfolio/*` -> `localhost:8056/*`). Update `start_all.sh` to run this service.
    *   **Why:** An API Gateway simplifies the frontend code (no more hardcoded ports), centralizes authentication and rate limiting, and improves security by hiding the internal service architecture.

*   **Task 1.5 (Validation): Database, Validation & Gateway Tests**
    *   **What:**
        1.  Create `tests/test_db_migration.py` to verify that data from a sample CSV is correctly loaded into the PostgreSQL database.
        2.  Create `tests/test_data_validation.py` to test the `pandera` schemas with both valid and invalid data.
        2.  Update the `tests/e2e/test_main_workflows.py` Playwright tests to make all their requests through the new API Gateway's URL instead of the individual service ports.
    *   **Why:** This ensures the data migration is correct and that the API Gateway is functioning transparently as a proxy for all existing UI functionality.

---

## Sprint 2: Options Trading, Caching & Resilient Tasks

**Goal:** Build the core "Options Lab" feature, **implement a high-performance caching layer**, and make long-running analyses more robust with a dedicated task queue.

*   **Task 2.1 (Implementation): Implement "Options Lab" (Phases 1-3)**
    *   **What:**
        1.  Create `tabs/options_lab.py` and `utils/options_data.py` to build the foundational options chain viewer (fetching data from Finnhub).
        2.  Create `strategies/options_screener.py` to add a layer of analysis (e.g., highlighting contracts that meet certain criteria).
        3.  Enhance `utils/trade_utils.py` and the `options_lab.py` callbacks to create a "Trade Ticket" UI and execute option trades via the Alpaca API.
    *   **Why:** This delivers a complete, end-to-end workflow for a major new feature, from analysis to execution.

*   **Task 2.2 (Implementation): Implement Resilient Task Queue**
    *   **What:** Integrate **Redis** and **Celery** into the architecture. Refactor the "Run Attribution Analysis" and "Run Scenario" features in the Analysis Hub. Instead of running in a local thread, clicking the "Run" button will now dispatch a job to a Celery worker. The UI will poll a status endpoint for completion.
    *   **Why:** Heavy computations can time out or crash a web server process. A dedicated task queue offloads this work, making the UI more responsive and the analyses more robust, scalable, and resilient to server restarts.

*   **Task 2.3 (Implementation): Implement Centralized Cache**
    *   **What:** Leverage the Redis instance from the task queue to serve as a centralized cache. Create a `utils/caching.py` module and apply caching decorators to expensive, frequently called functions (e.g., API calls for market data).
    *   **Why:** Dramatically improves UI responsiveness and reduces external API call costs.

*   **Task 2.4 (Validation): Options, Cache & Tasks E2E Tests**
    *   **What:**
        1.  Create a new Playwright test file, `tests/e2e/test_options_lab.py`. This test will navigate to the Options Lab, enter a ticker, verify the options chain loads, select a contract, and verify the trade ticket is populated.
        2.  Modify the Analysis Hub E2E test to check for the "Analysis running..." status message after clicking "Run" and then poll until the results container is visible, validating the async Celery workflow.
    *   **Why:** This provides automated verification for the new options trading workflow and ensures the migration to the async task queue is working correctly from a user's perspective.

---

## Sprint 3: Advanced UX, Optimization & User Customization

**Goal:** Make the dashboard feel more dynamic and professional with real-time updates, **add actionable portfolio optimization**, and introduce personalization features.

*   **Task 3.1 (Implementation): Implement Real-Time Portfolio**
    *   **What:** Add a WebSocket layer to the `portfolio_app.py` (e.g., using Flask-SocketIO). Modify the frontend to connect to the WebSocket for live price updates for positions, removing the need for the `dcc.Interval` polling component.
    *   **Why:** WebSockets provide instantaneous, push-based updates for portfolio value and P/L, creating a much smoother and more professional real-time user experience compared to the noticeable lag of polling.

*   **Task 3.2 (Implementation): Implement Portfolio Optimization Engine**
    *   **What:** Integrate `PyPortfolioOpt`. Add a new "Optimizer" sub-tab in the Portfolio section to calculate and display optimal portfolio weights based on user-selected goals (e.g., Max Sharpe).
    *   **Why:** Transforms the portfolio from a passive monitoring tool into an active decision-support system.

*   **Task 3.3 (Implementation): User Profiles & Watchlists**
    *   **What:** Add simple user authentication to the system (via the API Gateway). Create database tables for `users` and `watchlists`. Implement UI elements for creating and managing watchlists in a new "Watchlist" tab.
    *   **Why:** This is a key feature for user retention, allowing users to personalize the dashboard and track securities they are interested in.

*   **Task 3.4 (Implementation): Advanced Options Lab Visualizations**
    *   **What:** Implement "Options Lab" (Phase 4). Add a "Visualize P/L" button to the Trade Ticket that opens a modal with a Plotly chart showing the option's profit/loss profile at expiration.
    *   **Why:** This provides critical risk/reward analysis for options trades, elevating the lab from a simple execution tool to a true analysis platform.

*   **Task 3.5 (Validation): Real-Time, Optimization & Customization Tests**
    *   **What:**
        1.  Create a new Playwright test, `tests/e2e/test_watchlist.py`, that logs in, creates a new watchlist, adds a ticker, and verifies it appears in the list.
        2.  Enhance the `test_options_lab.py` to click the "Visualize P/L" button and verify that the P/L chart modal appears.
        3.  (Manual Test) Manually verify the real-time portfolio updates, as automating WebSocket testing can be complex.
    *   **Why:** This ensures the new user-facing features are working as expected and adds coverage for the advanced options visualizations.

---

## Sprint 4: Final Polish & Interactivity

**Goal:** Improve the overall user experience with advanced interactive enhancements and ensure the system is well-documented.

*   **Task 4.1 (Implementation): Interactive Cross-Filtering**
    *   **What:** Implement client-side callbacks in the Portfolio and Analysis tabs to enable interactive filtering between charts and tables (e.g., clicking on the "Technology" sector in a pie chart should filter the positions table to show only tech stocks).
    *   **Why:** This makes the dashboard more dynamic and powerful, allowing users to explore their data more intuitively.

*   **Task 4.2 (Implementation): Light/Dark Theme Toggle**
    *   **What:** Add a UI switch in the main dashboard header that dynamically changes the app's stylesheet between the current dark theme (`CYBORG`) and a light alternative (`BOOTSTRAP`).
    *   **Why:** This is a common user experience enhancement that improves accessibility and user preference.

*   **Task 4.3 (Implementation): API Documentation**
    *   **What:** Leverage FastAPI's automatic documentation generation. Add OpenAPI metadata and Pydantic models to the API Gateway endpoints to create a clean, self-documenting API available at `/docs`.
    *   **Why:** This provides clear, interactive documentation for all available API endpoints, which is invaluable for future development and potential third-party integrations.

*   **Task 4.4 (Validation): Final UI/UX Clicker Tests**
    *   **What:**
        1.  Enhance the main E2E test suite to include clicking the theme toggle and asserting that the page background color changes.
        2.  Add a test case that clicks a segment in a pie chart and verifies that the corresponding data table is filtered.
        3.  Add a simple `curl` test to the `run_all_tests.sh` script to verify that the `/docs` endpoint on the API Gateway returns a `200 OK` status.
    *   **Why:** This provides final validation for the UI polish features and confirms that the automated API documentation is being generated correctly.

---

## Sprint 5: Proactive Intelligence & Strategy Validation

**Goal:** Extend the platform's capabilities from analysis to proactive intelligence and strategy validation with a backtesting engine and user-defined alerts.

*   **Task 5.1 (Implementation): Implement Backtesting Engine**
    *   **What:** Create a new "Backtester" tab using a library like `backtesting.py`. Allow users to test simple strategies (e.g., moving average crossover) on historical data.
    *   **Why:** Empowers users to validate their trading ideas before risking capital, a core feature of advanced trading platforms.

*   **Task 5.2 (Implementation): Implement Alerting System**
    *   **What:** Create a UI for users to set price or event-based alerts. A scheduled background job will check these rules and trigger in-app or email notifications.
    *   **Why:** Makes the dashboard a proactive tool that brings important events to the user's attention.

*   **Task 5.3 (Validation): Backtesting & Alerting E2E Tests**
    *   **What:** Create new Playwright tests for the Backtester and Alerting system to verify their core functionality.
    *   **Why:** Ensures these critical new intelligence features are working correctly from end to end.

