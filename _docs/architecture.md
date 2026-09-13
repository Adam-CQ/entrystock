# Technical Architecture

## 1. Architecture goals

The PoC must provide a complete, explainable company-analysis workflow while keeping the analytical logic reusable for future daily recalculation and backtesting.

The architecture should therefore:

- keep the user-facing product simple and Python-oriented;
- separate presentation, application workflow, and analytical calculations;
- expose assumptions, inputs, weights, rules, and calculation results;
- preserve historical data so analyses can be reproduced and backtested;
- support background processing for data collection and longer analyses;
- remain small enough to deploy and operate as a PoC.

## 2. Selected stack

### Version policy

The versions below are the target baseline for the PoC, checked on **2026-09-13**. Exact patch versions must be resolved and recorded in `uv.lock`; container image tags should be pinned rather than using `latest`.

The project favors the latest stable release that has good compatibility across the selected Python ecosystem. It does not automatically adopt a newly released Python interpreter or a pre-release database/library version. Patch releases should be upgraded regularly after the test suite passes.

Python **3.13** is selected instead of Python 3.14. Python 3.14 is the newest stable Python release, but 3.13 has broader third-party wheel and integration maturity while still receiving bug fixes through 2027 and security fixes through 2029. This is a deliberate PoC stability tradeoff, not a restriction against upgrading later.

### Version baseline

| Component | Target version | Selection and compatibility note |
| --- | --- | --- |
| Python | 3.13.15 | Mature supported runtime for the scientific Python ecosystem; reconsider 3.14 after dependency validation |
| Django | 6.1.1 | Latest stable Django series; supports the selected Python line |
| Django REST Framework | 3.18.1 | Latest stable release; optional initially and used only for API endpoints exposed by Django |
| FastAPI | 0.141.1 | Latest stable release; analytical API with Pydantic and Starlette dependencies |
| Uvicorn | 0.52.4 | Current stable ASGI server for FastAPI |
| Gunicorn | 26.2.0 | Current stable process manager for Django deployment |
| Polars | 1.44.x | Latest stable release line; primary dataframe engine |
| pandas | 2.3.x | Compatibility fallback for provider and scientific libraries that require pandas |
| NumPy | 2.5.3 | Current stable release; numerical array operations |
| SciPy | 1.18.1 | Current stable release; statistics and numerical methods |
| PostgreSQL | 18.6 | Latest stable major release; use the official PostgreSQL 18 image |
| DuckDB Python package | 1.5.5 | Latest stable release; do not use the 1.6 development builds |
| Parquet | Apache Parquet format 2.x | Interchange format used by DuckDB and Polars; implementation supplied through compatible Arrow tooling when needed |
| Celery | 5.6.3 | Current stable release with Django and Redis integrations |
| Redis Python client | 8.1.0 | Current stable client compatible with the selected Redis server line |
| Redis server | 8.x stable | Use a pinned stable 8.x image; fall back to 7.4.x only if a Celery/provider compatibility issue is found |
| HTMX | 2.0.x stable | Browser enhancement layer for Django-rendered pages |
| Alpine.js | 3.x stable | Small client-side state and interaction layer |
| Plotly | 6.x stable | Interactive charts rendered from Django responses |
| Docker Engine | Current stable 29.x line | Container runtime; pin the deployment environment separately from application dependencies |
| Docker Compose | v2.x | Local multi-container orchestration |
| pytest | 9.1.1 | Test runner for Python and Django tests |

Frontend assets should be vendored or served from a version-pinned package/CDN URL. The project should not use unversioned URLs for HTMX, Alpine.js, or charting assets.

The version check should be repeated before implementation begins. If dependency resolution shows a conflict, retain the newest compatible patch/minor line and document the exception in the lockfile or project notes.

| Area | Technology | Purpose |
| --- | --- | --- |
| Product frontend | Django templates (Django 6.1.x) | Server-rendered dashboard, forms, navigation, and pages |
| Dynamic interactions | HTMX 2.0.x | Partial page updates without building a separate frontend application |
| Small browser interactions | Alpine.js 3.x | Local UI state such as toggles, tabs, and editable controls |
| Product backend | Django 6.1.x | Authentication, permissions, application workflow, persistence, and admin |
| Optional Django API | Django REST Framework 3.18.x | Django-owned endpoints where a separate client or integration needs them |
| Analytical API | FastAPI 0.141.x | Typed HTTP interface for valuation, forecasts, momentum, scoring, and explanations |
| Core analytical logic | Python | Reusable domain services shared by FastAPI and background jobs |
| Data processing | Polars 1.44.x, with pandas 2.3.x where compatibility requires it | Financial and market-data transformations |
| Numerical analysis | NumPy 2.5.x and SciPy 1.18.x | Numerical calculations, statistics, and model support |
| Application database | PostgreSQL 18.x | Normalized financial data, user data, configurations, and analysis results |
| Analytical storage | DuckDB 1.5.x and Parquet 2.x | Historical time series, feature datasets, research, and backtesting |
| Background processing | Celery 5.6.x | Data ingestion, analysis jobs, scheduled recalculation, and backtesting jobs |
| Queue and cache | Redis server 8.x and redis-py 8.1.x | Celery broker/result backend and short-lived application caching |
| Visualizations | Plotly 6.x | Valuation, historical multiples, momentum, and sensitivity charts |
| API server | Uvicorn 0.52.x | Serves FastAPI |
| Django server | Gunicorn 26.2.x | Serves Django in deployment |
| Packaging and deployment | Docker Engine 29.x and Docker Compose v2 | Reproducible local development and PoC deployment |
| Testing | pytest 9.1.x, pytest-django, and HTTP client tests | Unit, integration, API, and workflow tests |

The initial deployment should remain provider-neutral. A Docker-based deployment can run on a managed platform such as Render, Fly.io, Railway, or a comparable cloud service.

## 3. High-level system structure

```text
                         ┌────────────────────┐
                         │      Browser       │
                         └─────────┬──────────┘
                                   │ HTML / HTMX
                                   ▼
                         ┌────────────────────┐
                         │ Django application │
                         │ UI, auth, workflow │
                         └──────┬───────┬─────┘
                                │       │
                 read/write app │       │ analysis requests
                                ▼       ▼
                       ┌──────────┐  ┌──────────────┐
                       │PostgreSQL│  │   FastAPI    │
                       │          │  │ analytics API│
                       └──────────┘  └──────┬───────┘
                                             │
                                             ▼
                                    ┌────────────────┐
                                    │ Python engines │
                                    │ DCF, peers,    │
                                    │ momentum, score│
                                    └───────┬────────┘
                                            │
                 batch and scheduled jobs  │ analytical datasets
                                            ▼
                         ┌──────────┐  ┌──────────────┐
                         │Celery +  │  │DuckDB +      │
                         │Redis     │  │Parquet       │
                         └──────────┘  └──────────────┘
```

The Django application is the product entry point. FastAPI is the reusable interface to the analytical engine. Celery runs operations that should not block a web request.

## 4. Responsibilities by application

### Django application

Django owns the user-facing product and application state:

- company selection and search;
- proposed peer review, addition, and removal;
- analysis configuration and saved assumptions;
- scoring weights and hard decision rules;
- authentication and permissions;
- dashboard pages and HTMX partials;
- recommendation history and data freshness display;
- Django Admin for operational data review.

Django views should coordinate workflows and render results. They should not contain DCF, momentum, or composite-score formulas.

### FastAPI analytical service

FastAPI exposes typed analytical operations such as:

- peer similarity and peer-group proposals;
- DCF valuation and sensitivity analysis;
- peer-relative valuation;
- historical valuation statistics and bands;
- management, analyst, and internal forecast comparison;
- company, peer, and industry momentum;
- peer-leader and laggard analysis;
- composite scoring and hard-rule evaluation;
- confidence and uncertainty calculations;
- recommendation explanation generation.

FastAPI route handlers should validate requests and delegate to shared Python domain modules. They should not become the location of domain logic.

### Shared Python analytical modules

The analytical engine should be organized as reusable Python packages, for example:

```text
analytics/
├── data_quality/
├── peer_analysis/
├── forecasts/
├── valuation/
│   ├── dcf.py
│   ├── relative.py
│   └── historical.py
├── momentum/
├── scoring/
├── explanations/
└── backtesting/
```

These modules should be callable from FastAPI, Celery workers, tests, and later research notebooks.

## 5. Data architecture

PostgreSQL is the source of truth for application-facing and normalized data. It should contain, at minimum:

- companies, securities, exchanges, sectors, and industries;
- financial statements and filing metadata;
- management guidance and analyst estimates;
- market-price snapshots and corporate-action metadata;
- peer groups and peer-selection explanations;
- analysis configurations, assumptions, weights, and hard rules;
- calculation runs, outputs, confidence values, and explanations;
- data-source and freshness metadata.

DuckDB and Parquet are intended for analytical datasets that benefit from columnar storage and inexpensive historical scans:

- daily or weekly price histories;
- historical valuation-multiple series;
- derived momentum features;
- point-in-time datasets for backtesting;
- intermediate research and model outputs.

Raw provider data should be retained where licensing permits. Normalized records should include source, retrieval time, effective date, and data quality status so that recommendations can show data freshness and analyses can be reproduced.

## 6. Request and job flow

For a short calculation, Django may call FastAPI synchronously and render the returned result.

For data ingestion, full company analysis, or backtesting:

1. Django creates an analysis-run record with the selected inputs and configuration.
2. Django submits a Celery task through Redis.
3. The worker loads the required data and calls the shared analytical modules.
4. The worker stores inputs, intermediate summaries, outputs, and errors.
5. Django displays status and refreshes the result area using HTMX.

Every recommendation should be traceable to a calculation run, its data snapshot, its assumptions, its score configuration, and its hard-rule results.

## 7. Initial PoC boundaries

The first implementation should focus on:

- US-listed companies;
- one coherent demonstration scenario, preferably GE Vernova in a confirmed nuclear/energy-technology peer context;
- a limited set of financial data sources;
- DCF, peer-relative, and three-to-five-year historical valuation;
- explicitly separated management, consensus, and internal forecasts;
- a focused set of momentum indicators;
- configurable weights and hard rules;
- an explainable dashboard.

Global coverage, production-scale news analysis, portfolio management, broker integration, personalized models, and automated alerts remain outside the initial architecture implementation.

## 8. Architectural principles

- Keep calculation logic independent of Django and FastAPI.
- Treat data freshness, source, and effective date as first-class fields.
- Store point-in-time inputs needed to avoid look-ahead bias in backtesting.
- Keep weighted scoring separate from hard decision rules.
- Return explanations alongside numerical outputs.
- Make assumptions and configuration versioned or associated with each analysis run.
- Prefer synchronous execution for simple PoC interactions and Celery for expensive or repeatable work.
- Add further services only when workload, deployment, or ownership boundaries justify them.

## 9. Future evolution

The stack can evolve without replacing the core analytical modules:

- React or Next.js can replace Django templates if richer client-side interactions become necessary.
- FastAPI can serve external clients or a mobile application.
- Scheduled Celery pipelines can support daily watchlist recalculation.
- Object storage can supplement Parquet datasets at larger scale.
- A dedicated workflow orchestrator can replace simple Celery scheduling if ingestion becomes complex.
- Additional markets and providers can be added behind provider-specific ingestion adapters.

The PoC should not introduce these components until the recommendation workflow and its validation criteria have been demonstrated.
