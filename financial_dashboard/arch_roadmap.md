Unified Master Roadmap
This document is the single source of truth for the development of the Unified Financial Dashboard. It details the sprint-by-sprint plan to refactor the existing application into a professional, modular architecture and build out its features on a 100% free, self-hosted infrastructure platform.
Core Architecture
This project is composed of two distinct but connected systems that will be developed in parallel on your local machine.
1. The Platform Stack (~/platform-stack/)
This is the foundational infrastructure. It's a collection of open-source services (databases, MLOps, etc.) managed by a single docker-compose.yml file. It's the "power plant" for your application.
2. The Application (~/financial_dashboard/)
This is the code you write. It includes a modular Dash UI (one file per tab), all backend FastAPI microservices, and its own docker-compose.yml to manage the application containers.
The Connection: Shared Docker Network
A shared Docker network (shared-network) is the "magic" that allows containers from both projects to discover and communicate with each other by name (e.g., your FastAPI service can connect to postgres:5432).
The Unified Roadmap
Sprint 0: Foundational Remediation & Modular Refactoring
Goal: Fix all 17 critical bugs by refactoring the unstable monolithic application into the clean, modular architecture. Establish the core infrastructure foundation on your local machine.
Task 0.1 (Platform): Establish Core Environment
What: Install WSL 2 and Docker Desktop. Create the ~/platform-stack and ~/financial_dashboard directories. Create the shared-network via docker network create.
Why: Creates the stable, containerized Linux environment where the entire system will run.
Task 0.2 (Application): Refactor to Modular Dash UI
What: In ~/financial_dashboard, delete the monolithic integrated_dashboard.py. Create the new structure: app.py (for the Dash instance), index.py (the assembler), and a tabs/ folder. Move the UI layout and callbacks for each feature (Analysis Hub, Options Lab, etc.) into its own file within tabs/.
Why: This is the most critical fix. It immediately solves all duplicate ID conflicts, makes the code debuggable, and provides a stable structure for all future work. All UI/console bugs will be fixed during this refactoring.
Task 0.3 (Application): Create Backend Microservices
What: For each feature that requires backend logic (Options Lab, AI Chatbot, Market Forecast), create a corresponding FastAPI service in the services/ directory with its own Dockerfile. Create the application's docker-compose.yml to run these services.
Why: This moves heavy logic out of the UI, fixing performance issues and Connection refused errors by providing the actual backend services that were missing.
Task 0.4 (Platform): Deploy Core Data Stack
What: In ~/platform-stack, create a docker-compose.yml and launch the postgres and timescaledb services on the shared-network.
Why: Provides the professional-grade databases that the application's microservices will connect to.
Task 0.5 (Integration): Fix Data Quality & Connectivity
What: Update the new FastAPI services to connect to the postgres:5432 database. Implement .fillna() logic within the services before returning data to the UI.
Why: Fixes all "N/A" errors at the source and validates the end-to-end connection from UI -> Service -> Database.
Task 0.6 (Validation): Overhaul Test Suite
What: Create the new tests/test_final_validation.py. This suite will contain Playwright tests that target the now-stable, modular application.
Why: Provides a definitive E2E test suite that validates all bug fixes and ensures the new architecture is working correctly.
Sprint 1: Strategy Proving Ground with Options Alpha
(No Change)
Goal: Use the no-code Options Alpha platform for rapid prototyping and live paper-trading validation of 3-5 bot strategies, identifying 1-2 "graduates" to be re-coded into our Python system.
Sprint 2: Data Pipelines & MLOps Integration
Goal: Establish professional data pipeline orchestration and machine learning lifecycle management.
Task 2.1 (Platform): Launch Workflow & MLOps Stack
What: Add the dagster and mlflow services to the platform-stack/docker-compose.yml.
Why: Deploys the tools for professional data pipeline orchestration (Dagster) and MLOps (MLflow).
Task 2.2 (Application): Build First Data Pipeline
What: Create a new, separate ~/dagster_project/. Inside, create a Dagster pipeline to parse all historical picks_*.csv and Financial_Data/*.parquet files and load them into the postgres and timescaledb databases.
Why: Replaces fragile one-off scripts with a robust, observable, and schedulable data engineering workflow.
Task 2.3 (Application): Implement Pluggable Strategy Engine
What: In the options_service, create the strategies/base_strategy.py abstract base class and a sample covered_call_screener.py.
Why: Establishes the flexible architecture for adding new trading strategies, including the "graduates" from Sprint 1.
Task 2.4 (Application): Build Initial Backtester
What: Create the initial backtester.py module within the options_service. It will query historical data from the timescaledb database. Add the "Backtest Trend Signals" feature to the tabs/market_trends.py UI.
Why: Enables quantitative validation of strategies against a centralized, high-performance database.
Sprints 3-11: Advanced Feature Implementation
The following sprints from the original MASTER_ROADMAP are now implemented within the new, robust architecture.
Sprint 3: Live Options System & Advanced UI
Goal: Bring the options system to life.
Implementation: All UI components (Visual Strategy Builder, Greeks View, "What-If" Sliders) will be built in the modular tabs/options_lab.py file. The core logic (Risk Manager, Live Loop) will be implemented inside the containerized options_service.
Sprint 4: Production Readiness & Full Monitoring
Goal: Harden the platform and add "mission control" visibility.
Implementation:
Platform: Add rabbitmq, grafana, loki, and jaeger to the platform-stack/docker-compose.yml.
Application: Instrument all FastAPI services with OpenTelemetry to send logs and traces to the platform.
CI/CD: Create the GitHub Actions workflow to build, test, and scan Docker images for the application services.
Sprint 5: Advanced Analytics & Integrated UX
Goal: Evolve the platform into an intelligent, interconnected system.
Implementation:
UI: New features like "Volatility Lab" and "Correlation Lab" become new tabs/volatility_lab.py files. The customizable "Home" dashboard is built in tabs/home.py.
Backend: The logic for these new labs will be new FastAPI microservices (services/volatility_service/).
Data: All new data sources (Macro-Economic, Alternative, Social Sentiment) will be implemented as new Dagster pipelines.
MLOps: All new predictive models (Regime-Aware Forecasting, etc.) will have their experiments and final versions tracked in MLflow.
Sprint 6: AI-Powered Insights
Goal: Integrate a conversational AI interface.
Implementation: The "AI Chatbot Assistant" and "Automated Narrative Generation" will be powered by a dedicated ai_chatbot_service, which integrates with the Gemini API and calls other internal service APIs to fulfill requests.
Sprint 7: Enterprise Operations & Resilience
Goal: Harden the deployment process.
Implementation: The "Staging Environment" will be a dedicated namespace in your local Kubernetes cluster (from Docker Desktop). The CI/CD pipeline will be enhanced to deploy to this K8s environment. Feature flags and security scanning (Trivy) will be added to this pipeline.
Sprint 8: Real-Time & Event-Driven Architecture
Goal: Evolve to a real-time platform.
Implementation: A new websocket_service will stream live Alpaca data into TimescaleDB and to the UI. The options_service and portfolio_service will be refactored to use the RabbitMQ message bus for asynchronous communication.
Sprint 9: Next-Generation AI & Strategy Generation
Goal: Use AI to discover and create new strategies.
Implementation: The "RL Lab" will be a new tab and a new GPU-enabled rl_service container, with all training managed by MLflow. The "Natural Language Strategy Generation" feature will be an enhancement to the ai_chatbot_service.
Sprint 10: Professional Backtesting & Strategy Validation
Goal: Upgrade the backtesting engine to an institutional-grade system.
Implementation: A new, dedicated backtesting_service will be created. It will use an event-driven engine (Backtrader), implement walk-forward optimization, and fully integrate with the platform: pulling data from TimescaleDB and pulling models/logging results to MLflow.
