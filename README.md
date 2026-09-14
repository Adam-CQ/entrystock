# EntryStock

EntryStock is an explainable investor-analysis proof of concept. It combines a
Django product application, a FastAPI analytical boundary, Celery-compatible
background jobs, and a framework-independent Python analytics core.

The current demonstration is fixture-backed and intentionally cautious. It
shows company selection, peer proposals, valuation, forecasts, momentum,
composite scoring, recommendations, data-quality warnings, charts, and a
minimum recommendation backtest. It is not financial advice and does not make
claims about predictive performance.

## Architecture at a glance

```text
Browser
   │ HTML / HTMX
   ▼
Django product application ───────┐
   │                              │ application services
   │                              ▼
   │                       Framework-independent analytics
   │                              ▲
FastAPI analytical API ───────────┘

Celery jobs ───────> application services ───────> analytics

Fixture/provider data ─> contracts and normalization ─> Django persistence
```

The repository is in a staged package migration. The existing top-level
packages remain the active compatibility and Django runtime packages. The new
`src/entrystock/` namespace is the target boundary for new code and will absorb
the implementations gradually.

## Repository structure

```text
.
├── analytics/                 # Current framework-independent analytics engine
├── api/                       # Legacy FastAPI compatibility entrypoint
├── companies/                 # Django companies and peer-group product app
├── config/                    # Django, ASGI/WSGI, Celery, and URL configuration
├── financials/                # Django financial models and analysis-run workflow
├── market_data/               # Django market-data models and migrations
├── templates/                 # Server-rendered Django dashboard templates
├── tests/                     # Unit, integration, API, and workflow tests
├── src/entrystock/            # Target application namespace and migration seams
├── _docs/                     # Architecture, process, and migration documentation
├── manage.py                  # Django command-line entrypoint
├── pyproject.toml             # Dependencies, package metadata, and test settings
├── uv.lock                    # Locked Python dependency resolution
├── docker-compose.yml         # Optional PostgreSQL and Redis services
└── README.md                 # This guide
```

### Current analytics engine: `analytics/`

This package contains the actual reusable analytical implementations. It must
remain independent of Django, FastAPI, Celery, and ORM models.

| File | Responsibility |
| --- | --- |
| `analytics/provider_contracts.py` | Provider-neutral records for companies, statements, forecasts, prices, classifications, and corporate actions. |
| `analytics/fixture_provider.py` | Deterministic, network-free provider used by the PoC and ingestion tests. |
| `analytics/data_quality.py` | Freshness, coverage, warning, and blocking-status calculations. |
| `analytics/forecasts.py` | Forecast inputs, internal forecasts, and source comparison. |
| `analytics/valuation.py` | DCF, relative valuation, historical valuation, and sensitivity calculations. |
| `analytics/momentum.py` | Return windows, moving averages, volatility, volume, relative strength, and peer breadth. |
| `analytics/peer_analysis.py` | Transparent peer-candidate scoring and peer proposals. |
| `analytics/scoring.py` | Versioned weighted composite scores and contribution details. |
| `analytics/hard_rules.py` | Rules that can override a weighted recommendation, such as an excessive price/fair-value gap. |
| `analytics/recommendations.py` | Structured rating, evidence, explanation, confidence, and disclaimer output. |
| `analytics/explanations.py` | Reusable explanation helpers and plain-language analytical summaries. |
| `analytics/dashboard.py` | Assembles dashboard data by coordinating the analytical engines. |
| `analytics/visualizations.py` | Builds chart payloads for the dashboard. |
| `analytics/backtesting.py` | Point-in-time fixture data and the minimum recommendation backtest. |
| `analytics/__init__.py` | Exposes the analytics package version. |

### Django product apps

#### `companies/`

Owns company, exchange, sector, industry, security, ticker, and peer-group
models. It also contains the peer-group form, dashboard views, and the current
fixture import command.

- `models.py` — company and peer-group persistence models.
- `forms.py` — peer selection and confirmation validation.
- `views.py` — dashboard and peer-group workflow views; these coordinate the
  request and delegate calculations to `analytics`.
- `ingestion.py` — imports provider-neutral fixture records into Django models.
- `management/commands/load_fixture_data.py` — Django command that runs the
  deterministic fixture import.
- `migrations/` — database schema history for this Django app.

#### `financials/`

Owns financial statements, forecast persistence, and reproducible analysis-run
state.

- `models.py` — reporting periods, filings, statements, forecasts, and
  `AnalysisRun` records.
- `services.py` — creates, queues, starts, completes, and fails analysis runs.
- `tasks.py` — Celery boundary for executing an analysis run.
- `migrations/` — database schema history.

#### `market_data/`

Owns persisted price observations and corporate actions associated with
securities.

- `models.py` — price, adjustment, and corporate-action models.
- `migrations/` — database schema history.

### Runtime configuration: `config/`

| File | Responsibility |
| --- | --- |
| `config/settings.py` | Django installed apps, middleware, templates, database defaults, static files, and Celery settings. SQLite is the default local database. |
| `config/urls.py` | `/health`, `/dashboard/`, and company peer-group URL routes. |
| `config/asgi.py` | ASGI entrypoint for Django. |
| `config/wsgi.py` | WSGI entrypoint for Django deployment. |
| `config/celery.py` | Creates the Celery application and autodiscovers tasks. |
| `config/analytics_boundary.py` | Confirms the shared analytics package version. |

### FastAPI API: `api/` and `src/entrystock/analytics_api/`

`src/entrystock/analytics_api/main.py` is the new analytical API entrypoint.
`api/main.py` remains a compatibility wrapper for existing commands and tests.

At present the API exposes:

- `GET /health` — returns `{"status": "ok"}`;
- `/docs` — FastAPI's interactive OpenAPI documentation;
- `/openapi.json` — generated OpenAPI schema.

The package contains placeholders for future `routers/` and `schemas/` modules.
Analytical endpoints should validate HTTP data there and delegate to
application services rather than implement formulas in route handlers.

### Target application namespace: `src/entrystock/`

This is the staged destination described in
[`_docs/entrystock_application_structure_guidelines.md`](_docs/entrystock_application_structure_guidelines.md).

| Folder | Responsibility |
| --- | --- |
| `src/entrystock/application/` | Application services coordinating product workflows and analytical engines. |
| `src/entrystock/analytics/` | Compatibility-facing analytics namespace while implementations migrate from the top-level package. |
| `src/entrystock/analytics_api/` | FastAPI application boundary. |
| `src/entrystock/ingestion/` | Provider contracts and provider adapters. |
| `src/entrystock/jobs/` | Celery task migration boundary and backtest job seam. |
| `src/entrystock/product/` | Future Django product-layer organization for companies, peer groups, analyses, configurations, and dashboard concerns. |
| `src/entrystock/storage/` | Reserved PostgreSQL, DuckDB, and Parquet adapter boundaries. |
| `src/entrystock/shared/` | Small cross-cutting utilities only; domain logic does not belong here. |

The new namespace currently uses compatibility imports where the old runtime
packages still own the implementation. This is intentional and allows the
project to migrate incrementally without breaking Django app labels, database
migrations, or public import paths.

### Tests: `tests/`

Tests currently remain in one directory while the architecture migration is in
progress. They cover analytics calculations, provider contracts, fixture
ingestion, Django models, analysis-run workflows, FastAPI health behavior,
Celery tasks, dashboard rendering, peer workflows, data quality, and
point-in-time backtesting.

The planned destination is `tests/unit/`, `tests/integration/`, and
`tests/e2e/`, as documented in the migration map.

### Documentation: `_docs/`

Important documents include:

- [`architecture.md`](_docs/architecture.md) — technical architecture and
  selected technologies;
- [`plan.md`](_docs/plan.md) — product goals and analytical workflow;
- [`tasks.md`](_docs/tasks.md) — issue-oriented implementation backlog;
- [`local-development.md`](_docs/local-development.md) — PostgreSQL, Redis,
  and Celery development infrastructure;
- [`backtesting-dataset.md`](_docs/backtesting-dataset.md) — point-in-time
  fixture and minimum backtest behavior;
- [`entrystock_application_structure_guidelines.md`](_docs/entrystock_application_structure_guidelines.md)
  — desired application structure;
- [`map_entrypoint_structure_guidelines.md`](_docs/map_entrypoint_structure_guidelines.md)
  — step-by-step migration map.

## Requirements

- Ubuntu under WSL2 or another Bash-compatible environment;
- Python 3.13;
- [`uv`](https://docs.astral.sh/uv/);
- Docker and Docker Compose only when using PostgreSQL/Redis locally;
- Redis only when running Celery workers or queued background jobs.

Dependencies are declared in `pyproject.toml` and locked in `uv.lock`. Do not
use `pip install` for this project. Do not commit `.env` files or secrets.

## Install and verify

From the repository root:

```bash
uv sync
uv run python manage.py check
uv run pytest
```

The full test suite should pass before using the application. The test suite is
designed to run without PostgreSQL, Redis, external providers, or credentials;
it uses the default SQLite configuration and deterministic fixture data.

## Launch the application

### Option A: Django dashboard only

This is the simplest local demonstration and does not require Docker, Redis, or
PostgreSQL.

1. Apply the local SQLite migrations:

   ```bash
   uv run python manage.py migrate
   ```

2. Load the deterministic fixture dataset:

   ```bash
   uv run python manage.py load_fixture_data
   ```

3. Start Django:

   ```bash
   uv run python manage.py runserver
   ```

4. Open [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/).

The health endpoint is available at
[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

### Option B: FastAPI analytical service

In a second terminal, run:

```bash
uv run uvicorn entrystock.analytics_api.main:app --reload
```

The service is available at `/health`, `/docs`, and `/openapi.json`. If Django
is already using port 8000, start FastAPI on another port:

```bash
uv run uvicorn entrystock.analytics_api.main:app --reload --port 8001
```

The legacy command `uv run uvicorn api.main:app --reload` remains supported
during the migration.

### Option C: PostgreSQL, Redis, and Celery

The default Django settings use SQLite. Use the infrastructure stack when you
need PostgreSQL and Redis-backed local development:

1. Create a local `.env` file containing the variables required by
   `docker-compose.yml`, including `POSTGRES_DB`, `POSTGRES_USER`,
   `POSTGRES_PASSWORD`, and `REDIS_PASSWORD`.
2. Start the services:

   ```bash
   docker compose up -d
   docker compose ps
   ```

3. Configure Django's database settings for PostgreSQL before using it. The
   current settings use `DJANGO_DB_ENGINE` and `DJANGO_DB_NAME`; the Compose
   services alone do not switch Django away from SQLite.
4. Start a Celery worker in another terminal:

   ```bash
   uv run celery -A config.celery worker --loglevel=INFO
   ```

5. Stop services while retaining their named volumes:

   ```bash
   docker compose stop
   ```

Redis is required for queued Celery work. The dashboard's main fixture-backed
page can be used without a worker.

## How to use the dashboard

1. Start Django and open `/dashboard/`.
2. Select a loaded company from the company dropdown.
3. Review the headline recommendation, confidence, fair-value range, entry
   zone, and explanation.
4. Review the proposed peer group. Open the peer-group link to select peers,
   add or remove candidates, and confirm the group when the validation rule is
   satisfied.
5. Inspect the DCF assumptions and sensitivity table. Values are tied to the
   displayed fixture period and should be read together with the assumptions.
6. Review peer valuation, historical valuation, forecast comparison, and
   momentum sections. `Not evaluable` and insufficient-data states are expected
   for parts of the small fixture.
7. Inspect the composite score breakdown to see component values, weights,
   contributions, coverage, and status.
8. Read the drivers, catalysts, risks, uncertainty, and data-quality sections
   before interpreting the recommendation.
9. Treat `ENTRY`, `WATCH`, `NO_ENTRY`, and other ratings as analytical PoC
   outputs, not instructions to trade.

The peer workflow is available directly at
`/companies/<company_id>/peers`. The exact numeric company ID is displayed in
the dashboard link and is normally not needed manually.

## How to use the analytical Python API

The framework-independent engines can be imported from the current top-level
package or the new migration namespace. New code should prefer the latter:

```python
from entrystock.analytics.backtesting import run_recommendation_backtest
from entrystock.analytics.scoring import calculate_composite_score
from entrystock.analytics.valuation import calculate_dcf
```

The current HTTP API only exposes health and OpenAPI metadata. Analytical HTTP
routers are a subsequent migration step; calculations should currently be
called through Python application services or the Django dashboard.

## Backtesting example

The deterministic backtesting fixture can be used without external data:

```python
from entrystock.analytics.backtesting import (
    build_fixture_backtesting_dataset,
    run_recommendation_backtest,
)

dataset = build_fixture_backtesting_dataset()
result = run_recommendation_backtest(dataset)

print(result.metrics)
print(result.weight_sensitivity)
print(result.lookback_sensitivity)
```

The backtest reports forward returns, benchmark comparison, hit rate,
cumulative return, drawdown, a Sharpe-like descriptive summary, component
results, and sensitivity. The fixture is intentionally very small and does not
establish predictive performance.

## Configuration notes

The most relevant environment variables are:

| Variable | Use | Default |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django signing and security key | Local development placeholder |
| `DJANGO_DEBUG` | Django debug mode | `1` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | `*` |
| `DJANGO_DB_ENGINE` | Django database backend | SQLite backend |
| `DJANGO_DB_NAME` | Django database name/path | `db.sqlite3` in the repository root |
| `CELERY_BROKER_URL` | Celery broker | `REDIS_URL` or local Redis |
| `CELERY_RESULT_BACKEND` | Celery result backend | Broker URL |
| `REDIS_URL` | Redis connection fallback | `redis://localhost:6379/0` |

Do not put credentials in source files. Keep local environment files out of
Git.

## Development checks

Run the smallest relevant test while developing, then the complete suite:

```bash
uv run pytest tests/test_valuation.py
uv run pytest tests/test_backtesting.py
uv run pytest
uv run python manage.py check
git diff --check
```

Useful import checks include:

```bash
uv run python -c "from entrystock.analytics_api.main import app; print(app.title)"
uv run python -c "from entrystock.analytics.backtesting import run_recommendation_backtest; print(run_recommendation_backtest)"
```

## Current limitations

- The application uses deterministic fixture data rather than live provider
  data.
- The sample universe and historical coverage are intentionally small.
- PostgreSQL/DuckDB/Parquet storage boundaries exist in the target namespace,
  but the current runtime still uses Django models and SQLite by default.
- The FastAPI analytical service currently provides health and OpenAPI
  metadata; feature routers are not yet exposed.
- Celery task infrastructure exists, but the dashboard's core fixture workflow
  does not require a running worker.
- Results are decision-support research outputs, not personalized financial
  advice or guarantees of future returns.
