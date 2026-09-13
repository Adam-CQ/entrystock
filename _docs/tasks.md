# Implementation Backlog

Each task is intentionally scoped to one focused session. A task description includes enough context to be assigned independently; where another component does not yet exist, use a small fixture, stub, or interface rather than implementing unrelated work.

## 1. Create the empty project with a passing test
Goal: Establish a reproducible Python project skeleton that runs one passing test.
Description: Create the `uv`-managed project using the architecture baseline of Python 3.13, Django, FastAPI, and pytest. Add minimal application directories and one smoke test that passes without implementing product behavior; do not add database models, data providers, or dashboard features.

## 2. Add local PostgreSQL and Redis services
Goal: Make the project’s required infrastructure available locally with pinned container versions.
Description: Add Docker Compose configuration for PostgreSQL 18.x and Redis 8.x, including persistent local volumes, credentials supplied through environment configuration, and health checks. Document the commands and expected connection settings without changing application behavior.

## 3. Configure Django application foundations
Goal: Create a minimal Django application configuration suitable for the investor-analysis product.
Description: Configure Django settings, URL routing, installed applications, static files, and environment-based configuration using the selected version baseline. Add a minimal Django test proving the project starts and responds to a basic health page.

## 4. Configure the FastAPI analytical service
Goal: Create a minimal typed FastAPI service that can be run and tested independently.
Description: Add the FastAPI application entry point, versioned service metadata, and a `/health` endpoint. Add an HTTP test for a successful health response; analytical calculations and database access are outside this task.

## 5. Establish the shared analytics package
Goal: Define a framework-independent Python package for reusable analytical domain logic.
Description: Create the package boundaries for data quality, peer analysis, forecasts, valuation, momentum, scoring, explanations, and backtesting. Add a small import or contract test proving the package can be used by both Django/Celery code and FastAPI without importing web-framework internals.

## 6. Define the normalized company and security data model
Goal: Represent US-listed companies and their tradable securities consistently.
Description: Add Django models and migrations for companies, securities, exchanges, sectors, industries, and ticker identifiers. Include uniqueness rules and enough metadata to distinguish a company from a listed security, then cover the constraints with model tests.

## 7. Define financial statement storage
Goal: Store normalized historical and current financial statement data with provenance.
Description: Add models for reporting periods, income statements, balance sheets, cash-flow statements, and filing metadata. Include source, retrieval time, effective date, units, and data-quality fields so a later analysis can identify which data snapshot it used.

## 8. Define market-price and corporate-action storage
Goal: Store price history required for valuation, momentum, and future backtesting.
Description: Add a normalized interface and persistence model for OHLCV data, adjusted prices, and corporate actions. Define how timestamps, trading dates, security identifiers, and adjustment status are represented, and add tests for duplicate and out-of-order records.

## 9. Create a provider adapter contract
Goal: Allow financial-data providers to be replaced without changing analytical code.
Description: Define Python protocols or abstract interfaces for company metadata, financial statements, forecasts, prices, classifications, and corporate actions. Include a deterministic in-memory fixture provider implementing the contract so the interface can be tested without network access or paid credentials.

## 10. Implement fixture-based company data ingestion
Goal: Load a small, reproducible US-company dataset into the application.
Description: Create a management command or job that imports fixture data for the selected case-study company and several peers through the provider adapter contract. Record source and freshness metadata, make repeated imports idempotent, and test the import without contacting an external provider.

## 11. Implement peer proposal scoring
Goal: Propose 5–10 comparable companies with an inspectable similarity explanation.
Description: Implement a baseline rule-based peer selector using available business model, industry, size, growth, profitability, capital-intensity, and thematic attributes. Return ranked candidates with component-level reasons and confidence indicators; use fixtures where provider data is incomplete.

## 12. Implement peer-group confirmation workflow
Goal: Let a user review, add, remove, and confirm proposed peers before analysis.
Description: Add Django forms, persistence, and views for a selected company’s proposed and confirmed peer group. Preserve the proposal explanation and the user’s changes so the final analysis can distinguish algorithmic selections from user overrides.

## 13. Store and compare the three forecast sources
Goal: Display management guidance, analyst consensus, and internal-model forecasts separately.
Description: Define forecast-period and forecast-measure records for revenue, EBITDA, EPS, free cash flow, and other supported metrics. Implement comparison output showing divergence, missing values, and source freshness without averaging the forecasts into one number.

## 14. Implement the focused internal forecast model
Goal: Produce a transparent baseline forecast from historical company financials.
Description: Implement a small configurable model using explicitly documented historical metrics, forecast horizons, growth assumptions, and margin assumptions. Return assumptions and confidence metadata with the forecast, and test it with deterministic financial fixtures including incomplete-history cases.

## 15. Implement DCF valuation
Goal: Calculate intrinsic value using an inspectable discounted cash-flow model.
Description: Implement the DCF engine for revenue growth, operating margin, taxes, reinvestment, free cash flow, discount rate, and terminal growth. Return intermediate forecast cash flows, assumptions, per-share value, and validation errors for invalid or economically inconsistent inputs.

## 16. Add DCF sensitivity analysis
Goal: Show how intrinsic value changes when key DCF assumptions vary.
Description: Add a sensitivity calculation over at least discount rate and terminal-growth assumptions, using the existing DCF engine rather than duplicating formulas. Return a labeled table suitable for a dashboard and test boundary values and invalid combinations.

## 17. Implement peer-relative valuation
Goal: Estimate relative value against a confirmed peer group using appropriate multiples.
Description: Calculate a focused set of EV/EBITDA, P/E, EV/Sales, and free-cash-flow-yield comparisons when the required metrics are available. Select or suppress multiples according to company maturity and profitability, and return peer medians, outliers, data coverage, and an explanation of the selected multiples.

## 18. Implement historical valuation analysis
Goal: Compare current valuation with the company’s own three-to-five-year history.
Description: Calculate approximately three core historical multiples, current value versus historical median, percentile, and optional valuation bands from point-in-time data. Handle missing periods and negative denominators explicitly, and include the dates and data coverage used in the result.

## 19. Implement company and peer momentum indicators
Goal: Evaluate price trends for the selected company, its peers, and the broader industry.
Description: Implement a focused initial set of return windows, moving-average relationships, relative strength, volatility, volume confirmation, and peer breadth. Return signal values, lookback dates, data coverage, and a statement that peer-leadership results are probabilistic rather than predictive guarantees.

## 20. Implement peer-leader and laggard analysis
Goal: Identify whether peer movement may provide a catch-up signal for the selected company.
Description: Compare momentum changes across the confirmed peer group and industry, identify leaders and laggards, and calculate a cautious lead-lag feature using only information available at each observation date. Include safeguards against look-ahead bias and insufficient sample sizes.

## 21. Implement configurable composite scoring
Goal: Combine valuation, forecasts, momentum, quality, catalysts, and risk into an explainable score.
Description: Create versioned score configurations with user-editable weights, component contributions, normalization rules, and recommended default presets. Keep hard decision rules separate from the weighted score and return enough detail to explain every contribution.

## 22. Implement hard decision rules
Goal: Allow critical investment constraints to override a favorable weighted score.
Description: Define a small rule representation and evaluator, including the example that prevents an ENTRY recommendation when price is more than 20% above fair value. Return passed, failed, and not-evaluable states with reasons, and test precedence between hard rules and weighted recommendations.

## 23. Build recommendation and explanation output
Goal: Produce a plain-language recommendation from valuation, forecast, momentum, score, rules, and risk results.
Description: Define the supported rating scale, fair-value range, valuation gap, expected return, entry zone, confidence indicator, catalysts, and risks. Generate a structured explanation that cites the main drivers, assumptions, data freshness, uncertainty, and any hard-rule override without presenting the result as financial advice.

## 24. Implement an analysis-run workflow
Goal: Make every recommendation reproducible from a saved input and configuration snapshot.
Description: Add an analysis-run record containing the selected security, confirmed peers, data snapshot identifiers, assumptions, score configuration, hard rules, status, errors, and outputs. Implement a service that coordinates the FastAPI analytical operations or shared engines and stores a complete result for later display.

## 25. Add Celery analysis jobs
Goal: Run data ingestion and full company analyses without blocking web requests.
Description: Configure Celery with Redis and add a task for a complete analysis run using the existing analysis-run workflow. Store queued, running, successful, and failed states, and add a test using an eager or mocked worker configuration so the test suite does not require a live broker.

## 26. Build the recommendation dashboard
Goal: Present the complete PoC analysis workflow in a Django interface.
Description: Create Django template pages with HTMX interactions for company selection, peer confirmation, headline recommendation, fair value, entry zone, peer ranking, forecast comparison, valuation views, momentum, and score breakdown. Use fixture data and existing services, and keep charts and explanations visibly tied to their assumptions and dates.

## 27. Add valuation and momentum visualizations
Goal: Make the key analytical relationships understandable in the dashboard.
Description: Add version-pinned Plotly or ECharts visualizations for DCF sensitivity, historical valuation bands, peer multiples, forecast divergence, and company-versus-peer momentum. Ensure every chart includes units, dates, legends, and empty or insufficient-data states.

## 28. Add data freshness and quality reporting
Goal: Prevent stale or incomplete data from appearing trustworthy.
Description: Add a dashboard summary of each data source’s retrieval time, effective date, coverage, missing fields, and quality status. Define warning and blocking thresholds for calculations and ensure the recommendation explanation reports when confidence is reduced by weak data.

## 29. Create a point-in-time backtesting dataset
Goal: Prepare historical data that can support unbiased validation of recommendations.
Description: Define and generate a fixture-based point-in-time dataset containing prices, fundamentals, forecasts, peer membership, and classifications as they were known on each historical date. Add checks preventing future information from being available to an earlier analysis date.

## 30. Implement a minimum recommendation backtest
Goal: Test whether high composite scores and peer-leadership signals add useful forward-return information.
Description: Run the recommendation engine over the point-in-time dataset and calculate forward returns, benchmark comparison, hit rates, drawdown or risk-adjusted summaries, and results by signal component. Report sensitivity to weights and lookback windows while clearly labeling the small PoC sample and avoiding predictive claims unsupported by the test.
