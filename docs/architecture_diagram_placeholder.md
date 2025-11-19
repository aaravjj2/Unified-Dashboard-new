# Architecture Diagram (Placeholder)

Below is a lightweight ASCII/mermaid-friendly description of the planned
architecture. Replace with a formal diagram when ready.

Mermaid (conceptual):

```mermaid
flowchart LR
  PortfolioData[(Portfolio / prices CSV)] --> ML[ML Models]
  FactorData[(Factor time series)] --> ML
  ML --> Strategy[Strategy Lab]
  Strategy --> Dashboard[Unified Dashboard UI]
  ML -->|endpoint| Azure[Azure ML / AKS Endpoint]
  Azure -->|metrics| AppInsights[Application Insights]
  AppInsights --> Monitoring[Monitoring & Alerts]
```

Data flow:
- Offline: portfolio/factor CSVs -> ML model training -> saved artifact
- Online: ML endpoint receives features -> returns predictions -> Strategy Lab uses predictions to create recommended weights
