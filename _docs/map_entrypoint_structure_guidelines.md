# EntryStock structure reorganization map

This document maps the current repository to the target structure described in
`entrystock_application_structure_guidelines.md`.

The goal is to make the architecture clearer without rewriting working
features unnecessarily. Reorganization should be incremental: every stage
should leave the application importable and the test suite passing.

## 1. Starting point

The current project is a working Django/FastAPI/Celery PoC with these main
areas:

```text
analytics/     Framework-independent analytical calculations
api/            FastAPI application
companies/      Django company and peer-group product features
financials/     Django financial models, services, and Celery tasks
market_data/    Django market-data models
config/         Django settings, URLs, ASGI/WSGI, Celery, package boundary
templates/      Django templates
tests/          Unit, integration, and workflow tests in one directory
```

The target architecture adds clearer application-service, ingestion, storage,
and job boundaries. It does not require changing the product’s behavior or
moving every file immediately.

## 2. Target map

| Current location | Target location | Migration guidance |
| --- | --- | --- |
| `analytics/*.py` | `src/entrystock/analytics/` | Move calculations into domain-oriented packages gradually. Keep compatibility imports during the transition. |
| `api/main.py` | `src/entrystock/analytics_api/main.py` | Keep route registration in the API layer; move request/response schemas and service delegation beside it. |
| `companies/` | `src/entrystock/product/companies/` and `product/peer_groups/` | Keep Django models and views in the product layer. Separate peer workflow from company identity when useful. |
| `financials/models.py` | `src/entrystock/product/analyses/` plus domain-specific models | Keep persistence models in Django; do not move analytical formulas into them. |
| `financials/services.py` | `src/entrystock/product/analyses/services.py` | Make services the orchestration boundary between Django state and analytics. |
| `financials/tasks.py` | `src/entrystock/jobs/tasks/` | Tasks should load IDs and delegate to application services. |
| `market_data/` | `src/entrystock/product/` and `src/entrystock/ingestion/` | Separate Django persistence from provider adapters and normalization. |
| `config/settings.py` | `src/entrystock/config/django/settings/` | Split only when environment-specific settings are needed. Preserve current defaults first. |
| `config/celery.py` | `src/entrystock/config/django/celery.py` or `src/entrystock/jobs/celery.py` | Keep worker setup separate from task implementations. |
| `templates/` | `src/entrystock/product/templates/` or repository-level `templates/` | Either is valid; use one convention consistently. Existing Django template discovery must remain working. |
| `tests/` | `tests/unit/`, `tests/integration/`, `tests/e2e/` | Classify existing tests before moving them. Do not change test meaning while changing paths. |
| `_docs/` | `docs/` eventually | Keep `_docs/` during the migration unless documentation tooling requires a rename. |
| fixture providers and records | `src/entrystock/ingestion/` and `src/entrystock/data/` | Keep provider contracts independent of Django and preserve provenance fields. |
| backtesting code | `src/entrystock/analytics/backtesting/` and `jobs/tasks/run_backtest.py` | Keep calculations in analytics; let jobs coordinate loading and persistence. |

## 3. Recommended destination

The practical destination for this repository is:

```text
entrystock/
├── config/
│   └── ...                         # Django/FastAPI runtime configuration
├── src/
│   └── entrystock/
│       ├── product/                # Django apps and user workflows
│       │   ├── accounts/
│       │   ├── companies/
│       │   ├── peer_groups/
│       │   ├── analyses/
│       │   ├── configurations/
│       │   └── dashboard/
│       ├── analytics_api/          # FastAPI routes, schemas, dependencies
│       ├── analytics/              # Framework-independent calculations
│       ├── ingestion/              # Providers, contracts, normalization
│       ├── jobs/                   # Celery tasks and schedules
│       ├── storage/                # PostgreSQL, DuckDB, and Parquet adapters
│       └── shared/                 # Small cross-cutting utilities only
├── templates/
├── static/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── docs/
```

The destination may retain top-level `manage.py` and a top-level `config/` if
that is simpler for Django. The important property is dependency direction,
not the exact physical location of every configuration file.

## 4. Dependency rules

These rules should be enforced during every migration step:

```text
Django product ───────┐
                      ├──> application services ───> analytics
FastAPI API ──────────┘

Celery jobs ───────────────> application services ───> analytics

Ingestion providers ───> normalization ───> storage
                                             │
                                             └──> analytics
```

Specific rules:

1. `analytics/` must not import Django, FastAPI, Celery, ORM models, HTTP
   request objects, or provider SDKs.
2. FastAPI route handlers validate input and call services; they do not contain
   valuation, momentum, peer-ranking, or scoring formulas.
3. Django views coordinate user workflows and rendering; they do not perform
   analytical calculations.
4. Celery tasks accept stable identifiers and options, load state through a
   service, and delegate work. They should not duplicate formulas.
5. Provider adapters return provider-neutral contracts. Normalization converts
   provider data into those contracts before analytics consumes it.
6. Storage adapters hide database-specific queries from analytics and product
   workflows where practical.
7. Shared utilities must remain small. Do not create a catch-all `shared`
   package for domain logic.

## 5. Migration sequence

### Phase 0: Establish a safety baseline

Before moving files:

- Confirm `uv run pytest` passes.
- Record the current package imports and HTTP health endpoints.
- Keep the existing `analytics`, `api`, `companies`, `financials`, and
  `market_data` imports working temporarily.
- Add or verify smoke tests for Django startup, FastAPI startup, Celery task
  imports, and analytics imports without web frameworks.
- Check `git status` and keep unrelated work out of the migration commits.

Do not combine this phase with dependency upgrades or a database redesign.

### Phase 1: Define application-service boundaries

Create explicit services before moving packages:

```text
application services
├── company_service.py
├── peer_group_service.py
├── analysis_service.py
├── recommendation_service.py
└── backtest_service.py
```

Services should accept plain inputs or typed contracts, call analytics, and
return plain result objects. Django views, FastAPI routes, and Celery tasks
should call these services instead of calling many lower-level modules
directly.

At this stage, the services may import the existing top-level analytics
modules. This creates the boundary before physical movement.

### Phase 2: Normalize the analytics package

Move analytical modules one domain at a time:

```text
analytics/
├── data_quality/
├── explanations/
├── forecasts/
├── momentum/
├── peer_analysis/
├── scoring/
├── valuation/
│   ├── dcf.py
│   ├── relative.py
│   └── historical.py
└── backtesting/
```

Suggested mapping:

| Current module | Destination |
| --- | --- |
| `analytics/data_quality.py` | `analytics/data_quality/` |
| `analytics/explanations.py` | `analytics/explanations/` |
| `analytics/forecasts.py` | `analytics/forecasts/` |
| `analytics/momentum.py` | `analytics/momentum/` |
| `analytics/peer_analysis.py` | `analytics/peer_analysis/` |
| `analytics/scoring.py` and `analytics/hard_rules.py` | `analytics/scoring/` |
| `analytics/valuation.py` | `analytics/valuation/` with focused modules |
| `analytics/backtesting.py` | `analytics/backtesting/` |
| `analytics/recommendations.py` | `analytics/explanations/` or a top-level recommendation domain module |
| `analytics/provider_contracts.py` | `ingestion/contracts/` if the contracts are ingestion-owned |
| `analytics/fixture_provider.py` | `ingestion/providers/fixture.py` |
| `analytics/dashboard.py` | application/presentation service, not analytics core |
| `analytics/visualizations.py` | presentation or analytics API response layer |

For each move:

1. Create the destination package and public `__init__.py` exports.
2. Move or copy the implementation with the smallest possible change.
3. Add compatibility imports from the old module path.
4. Update direct imports gradually.
5. Run the focused tests, then the complete suite.
6. Remove compatibility imports only after repository-wide searches show no
   remaining callers.

Do not turn every existing file into a package solely to match the diagram.
Split modules when the domain has multiple stable responsibilities or when
the current module is difficult to test and navigate.

### Phase 3: Separate the analytical API

Refactor `api/main.py` into an API package:

```text
analytics_api/
├── main.py
├── dependencies.py
├── services.py
├── routers/
│   ├── health.py
│   ├── peers.py
│   ├── valuation.py
│   ├── forecasts.py
│   ├── momentum.py
│   └── scoring.py
└── schemas/
```

Keep `/health` behavior stable. Add versioned analytical routes behind
`/api/v1/`. Each router should be thin and delegate to an application service
or directly to a clearly defined analytical service where no persistence is
needed.

The API schemas should not become the analytical domain models. Convert
request schemas into domain inputs at the service boundary and domain results
back into response schemas there.

### Phase 4: Separate Django product applications

Gradually organize the existing Django apps by product responsibility:

```text
product/
├── companies/
├── peer_groups/
├── analyses/
├── configurations/
├── dashboard/
└── accounts/
```

Recommended ownership:

- `companies`: company identity, securities, search, and selection;
- `peer_groups`: proposals, confirmed peers, membership changes, and reasons;
- `analyses`: analysis-run state, saved inputs, outputs, and status;
- `configurations`: score weights, hard rules, and user-editable assumptions;
- `dashboard`: views, forms, HTMX endpoints, and presentation helpers;
- `accounts`: authentication, permissions, and user preferences.

Initially, existing Django apps may remain separate if migrations and imports
would become risky. The boundary can be introduced through services first and
physical app consolidation can follow later.

### Phase 5: Extract ingestion and normalization

Move provider concerns out of Django apps:

```text
ingestion/
├── contracts/
├── providers/
│   ├── market_data/
│   ├── financial_statements/
│   ├── estimates/
│   └── classifications/
├── normalization/
└── freshness.py
```

Provider adapters should be replaceable and testable without Django. They
should return contracts containing identifiers, observation/effective dates,
retrieval time, source, units, and quality metadata. Django management
commands may trigger ingestion, but they should call ingestion services rather
than implement provider parsing.

The existing fixture provider should become the first provider implementation
and remain available for deterministic tests.

### Phase 6: Establish storage adapters

Keep PostgreSQL as the application-facing source of truth. Introduce storage
interfaces before adding multiple database technologies:

```text
storage/
├── postgres/
├── duckdb/
└── parquet/
```

Use PostgreSQL for users, configurations, companies, normalized records, and
analysis-run metadata. Use DuckDB/Parquet for large historical analytical
datasets and backtest feature data when the project actually needs that scale.

Do not make analytics depend directly on Django ORM querysets or DuckDB
relations. Convert storage results into provider/domain contracts.

### Phase 7: Move Celery coordination

Create a jobs package:

```text
jobs/
├── tasks/
│   ├── ingest_market_data.py
│   ├── ingest_financials.py
│   ├── run_analysis.py
│   └── run_backtest.py
└── schedules.py
```

Each task should:

1. accept an ID or serializable request;
2. load the required application state;
3. call an application service;
4. persist status, outputs, and errors;
5. return a small serializable summary.

Tasks must not receive ORM objects, open database connections, or contain
analytical formulas in their serialized arguments.

### Phase 8: Reorganize tests

Classify tests by boundary:

```text
tests/
├── unit/
│   ├── analytics/
│   ├── ingestion/
│   └── shared/
├── integration/
│   ├── django/
│   ├── fastapi/
│   ├── jobs/
│   └── database/
└── e2e/
```

Suggested classification:

- analytical calculations, scoring, valuation, momentum, and backtesting:
  `unit/analytics/`;
- provider contracts, fixture ingestion, and normalization:
  `unit/ingestion/`;
- Django model, service, and workflow tests: `integration/django/`;
- FastAPI health and endpoint tests: `integration/fastapi/`;
- Celery task tests: `integration/jobs/`;
- dashboard/browser workflow tests: `e2e/` when browser automation exists.

Test moves should be mechanical first. Change assertions only when the
architecture change intentionally changes behavior.

## 6. Packaging strategy

The preferred long-term layout is a `src/` package, but it should be adopted
only after the application-service boundaries are stable.

When ready:

1. Create `src/entrystock/` and move one boundary at a time.
2. Update Hatch package discovery in `pyproject.toml`.
3. Update Django settings, `manage.py`, ASGI/WSGI, Celery, and test imports.
4. Install the project with `uv` and verify imports from an unrelated working
   directory.
5. Remove old top-level compatibility packages only after deployment and test
   entrypoints use the new paths.

Do not mix the `src/` migration with a major dependency upgrade.

## 7. Compatibility and deprecation policy

During migration, old import paths may be retained as small compatibility
modules:

```python
# Temporary compatibility module
from entrystock.analytics.scoring import *
```

Compatibility modules should:

- contain no business logic;
- be covered by import tests;
- include a removal note or issue reference;
- be removed only after all callers migrate.

Avoid broad wildcard exports in new code. They are acceptable only as a short
transition mechanism when preserving an existing public import path.

## 8. Verification gates

Every reorganization phase should pass:

```bash
uv run pytest
uv run python manage.py check
```

Also verify, as applicable:

- analytics imports without Django, FastAPI, or Celery loaded;
- FastAPI health and analytical endpoint tests;
- Django startup and dashboard rendering;
- Celery task discovery and task unit tests;
- fixture ingestion and point-in-time backtest tests;
- `git diff --check`;
- package installation from a clean environment before the `src/` migration
  is declared complete.

## 9. What not to do

- Do not perform a single large rename of the entire repository.
- Do not move analytical formulas into Django models, FastAPI routers, or
  Celery tasks.
- Do not introduce PostgreSQL, DuckDB, Parquet, Polars, NumPy, or SciPy merely
  to make the directory tree look complete; add them when a feature requires
  them and update dependency documentation at the same time.
- Do not change public behavior while only reorganizing files.
- Do not delete compatibility imports until repository-wide import searches and
  the full test suite confirm they are unused.
- Do not commit generated files, local data, secrets, or `.env` changes as
  part of the reorganization.

## 10. Definition of done

The reorganization is complete when:

- Django, FastAPI, Celery, and analytics have explicit boundaries;
- analytics can be imported and tested without web frameworks;
- routes, views, and tasks delegate rather than calculate domain formulas;
- provider adapters are separated from normalized contracts and storage;
- application services coordinate workflows and are independently testable;
- tests are organized by architectural boundary;
- package installation and all runtime entrypoints work from a clean
  environment;
- the dependency direction is documented and has no reverse framework imports;
- all existing supported behavior remains covered by passing tests.
