# EntryStock Application Structure Guidelines

## Purpose

This document translates `plan.md` and `architecture.md` into a practical repository structure for the EntryStock Proof of Concept.

The target is a small, modular monolith that can evolve into a larger product without coupling analytical calculations to Django, FastAPI, Celery, or a particular data provider.

The project name used in the development workflow is `project_1_ai_native`. The GitHub repository is `Adam-CQ/entrystock`.

## Architectural decision

Use one Python repository with three clear layers:

1. **Django product layer** — authentication, permissions, user workflow, persistence, admin, dashboard, forms, and HTMX responses.
2. **FastAPI analytical API** — typed HTTP endpoints for valuation, forecasts, momentum, peer analysis, and scoring.
3. **Framework-independent analytical core** — reusable Python modules containing the actual calculations and explanations.

Celery workers call application services and analytical modules for expensive or repeatable tasks. They should coordinate work, not contain the analytical formulas themselves.

## Recommended repository structure

```text
entrystock/
├── AGENTS.md
├── README.md
├── Makefile
├── pyproject.toml
├── uv.lock
├── manage.py
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── docs/
│   ├── architecture.md
│   ├── plan.md
│   ├── decisions.md
│   ├── api/
│   │   └── openapi.yaml
│   ├── data-sources/
│   └── runbooks/
│
├── config/
│   ├── django/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   ├── wsgi.py
│   │   └── celery.py
│   └── fastapi/
│       ├── dependencies.py
│       └── settings.py
│
├── src/
│   └── entrystock/
│       ├── product/
│       │   ├── accounts/
│       │   ├── companies/
│       │   ├── peer_groups/
│       │   ├── analyses/
│       │   ├── configurations/
│       │   ├── dashboard/
│       │   └── admin/
│       │
│       ├── analytics_api/
│       │   ├── main.py
│       │   ├── routers/
│       │   │   ├── health.py
│       │   │   ├── peers.py
│       │   │   ├── valuation.py
│       │   │   ├── forecasts.py
│       │   │   ├── momentum.py
│       │   │   └── scoring.py
│       │   ├── schemas/
│       │   └── services.py
│       │
│       ├── analytics/
│       │   ├── data_quality/
│       │   ├── peer_analysis/
│       │   ├── forecasts/
│       │   ├── valuation/
│       │   │   ├── dcf.py
│       │   │   ├── relative.py
│       │   │   ├── historical.py
│       │   │   └── sensitivity.py
│       │   ├── momentum/
│       │   ├── scoring/
│       │   ├── explanations/
│       │   └── backtesting/
│       │
│       ├── ingestion/
│       │   ├── contracts/
│       │   ├── providers/
│       │   │   ├── market_data/
│       │   │   ├── financial_statements/
│       │   │   ├── estimates/
│       │   │   └── classifications/
│       │   ├── normalization/
│       │   └── freshness.py
│       │
│       ├── jobs/
│       │   ├── tasks/
│       │   │   ├── ingest_market_data.py
│       │   │   ├── ingest_financials.py
│       │   │   ├── run_analysis.py
│       │   │   └── run_backtest.py
│       │   └── schedules.py
│       │
│       ├── storage/
│       │   ├── postgres/
│       │   ├── duckdb/
│       │   └── parquet/
│       │
│       └── shared/
│           ├── enums.py
│           ├── exceptions.py
│           ├── dates.py
│           ├── money.py
│           └── logging.py
│
├── templates/
│   ├── base.html
│   ├── dashboard/
│   ├── companies/
│   ├── analyses/
│   └── partials/
│       ├── peer_table.html
│       ├── score_breakdown.html
│       └── analysis_status.html
│
├── static/
│   ├── css/
│   └── js/
│       ├── app.js
│       └── charts.js
│
├── tests/
│   ├── unit/
│   │   ├── analytics/
│   │   ├── ingestion/
│   │   └── shared/
│   ├── integration/
│   │   ├── django/
│   │   ├── fastapi/
│   │   └── database/
│   └── e2e/
│
├── data/
│   ├── fixtures/
│   ├── sample/
│   └── local/
│
└── scripts/
    ├── seed_demo_data.py
    ├── import_parquet.py
    └── check_data_quality.py
```

## Responsibilities and boundaries

### Django product layer

Django owns:

- company selection and search;
- proposed peer review, addition, and removal;
- analysis configuration;
- score weights and hard rules;
- authentication and permissions;
- analysis-run records;
- recommendation history;
- data freshness display;
- dashboard pages and HTMX partials;
- Django Admin.

Django views should coordinate workflows and render responses. They must not contain DCF, momentum, peer-ranking, or composite-score formulas.

### FastAPI analytical API

FastAPI should provide typed endpoints such as:

```text
POST /api/v1/peers/propose
POST /api/v1/valuation/dcf
POST /api/v1/valuation/relative
POST /api/v1/valuation/historical
POST /api/v1/forecasts/compare
POST /api/v1/momentum/analyze
POST /api/v1/scoring/evaluate
POST /api/v1/analysis/run
```

Route handlers should validate requests and delegate to shared services. They should not become the location of domain logic.

### Framework-independent analytical core

The package under `analytics/` is the most important boundary. It should be callable from FastAPI, Celery, tests, notebooks, and future backtesting code.

Example:

```python
result = calculate_composite_score(
    valuation=valuation_result,
    forecasts=forecast_result,
    momentum=momentum_result,
    weights=score_config.weights,
    hard_rules=score_config.hard_rules,
)
```

The analytics package must not import Django models, FastAPI routers, HTTP request objects, or Celery tasks.

### Ingestion and providers

Provider-specific code belongs under `ingestion/providers/`. It should be separated from normalization and analytical calculations.

```text
External provider
    -> provider adapter
    -> provider contract
    -> normalization
    -> PostgreSQL / DuckDB / Parquet
    -> analytics modules
```

Every normalized record should preserve source, retrieval time, effective date, and data-quality status where applicable.

### Celery jobs

Celery tasks should coordinate long-running work:

```python
@shared_task
def run_company_analysis(analysis_run_id: int):
    inputs = load_analysis_inputs(analysis_run_id)
    result = analysis_service.run(inputs)
    save_analysis_result(analysis_run_id, result)
```

The calculation itself belongs in an application service or analytical module, not inside the task body.

## Dependency direction

Use this dependency direction:

```text
Django product ───────┐
                      ├──> application services ───> analytics
FastAPI API ──────────┘

Celery jobs ───────────────> application services ───> analytics

Ingestion providers ───> normalization ───> storage
                                             │
                                             └──> analytics
```

The key rule is:

```text
analytics must not depend on Django or FastAPI
```

## Initial PoC structure

Do not create every future directory immediately. The first working GE Vernova demonstration can begin with:

```text
src/entrystock/
├── product/
│   ├── companies/
│   ├── peer_groups/
│   ├── analyses/
│   └── dashboard/
├── analytics_api/
├── analytics/
│   ├── valuation/
│   ├── forecasts/
│   ├── momentum/
│   ├── scoring/
│   └── explanations/
├── ingestion/
├── jobs/
└── shared/
```

Add `backtesting/`, more provider adapters, and richer historical pipelines after the core recommendation workflow is demonstrable.

## Recommended implementation order

1. Inspect the existing repository and preserve working behavior.
2. Read `_docs/decisions.md` and establish `AGENTS.md` and project conventions.
3. Separate existing Django product code from analytical code.
4. Extract valuation calculations into framework-independent modules.
5. Add FastAPI endpoints around those modules.
6. Introduce provider contracts and deterministic demo data.
7. Add PostgreSQL persistence for normalized data and analysis runs.
8. Add Celery only for operations that are slow, scheduled, or repeatable.
9. Add DuckDB/Parquet when historical datasets require columnar scans.
10. Implement the complete PoC workflow one issue at a time.

Each issue should be implemented, tested, reviewed, merged, and closed before starting the next dependent issue. Avoid unrelated refactors and do not silently reorder the backlog.

## Initial demonstration scenario

Freeze one coherent US-only scenario first:

> Analyze GE Vernova in a user-confirmed nuclear/energy-technology peer context, compare management, analyst, and internal forecasts, calculate DCF plus peer and historical valuation, evaluate company and peer momentum, and produce an explainable entry recommendation.

The system should support user-selected companies, proposed 5–10 peers, user confirmation or editing of that peer group, configurable scoring weights, and hard decision rules.

## Required recommendation output

Each analysis should expose:

- fair value or fair-value range;
- valuation gap;
- expected return;
- entry zone;
- recommendation;
- composite score and component contributions;
- peer ranking;
- management, consensus, and internal-model forecast comparison;
- company, peer, and industry momentum;
- catalysts and risks;
- confidence or uncertainty;
- plain-language explanation;
- assumptions, data sources, freshness, weights, rules, and calculation-run identifier.

The result must not be a black box.

## Practical design rules for the coding agent

- Inspect relevant files before editing.
- Keep changes small and focused.
- Do not delete or rewrite unrelated code.
- Ask before introducing new dependencies when they are not already part of the approved stack.
- Prefer the cheapest relevant tests after each change.
- Run Django checks, API tests, analytical unit tests, and migration checks where relevant.
- Keep provider adapters replaceable.
- Keep weighted scoring separate from hard decision rules.
- Store point-in-time inputs needed to avoid look-ahead bias in future backtesting.
- Return explanations alongside numerical results.
- Associate assumptions and score configurations with each analysis run.
- Use pinned dependency and container versions; do not use `latest` images or unversioned frontend assets.

## Inspiration and interpretation

The inspiration article and repository are reference material only, not the source of the EntryStock architecture. The useful transferable ideas are:

- begin with a clear specification;
- keep frontend/backend integration behind a centralized service boundary;
- define an explicit API contract;
- replace mocked or temporary components incrementally;
- keep each development step runnable and testable.

The EntryStock implementation must retain its own selected stack: Django templates, HTMX, Alpine.js, FastAPI, PostgreSQL, DuckDB/Parquet, Celery, Redis, Polars, NumPy, SciPy, Plotly, Docker, and `uv`.

## Next task for the implementation agent

Inspect the current repository tree and produce a mapping:

| Current path | Target location | Action | Risk | Test needed |
|---|---|---|---|---|
| existing file or folder | recommended destination | keep, move, extract, or defer | low/medium/high | relevant check |

Do not move files yet. First report the mapping and identify which parts of the ideal structure already exist. Then implement the smallest safe boundary change according to the project backlog.

