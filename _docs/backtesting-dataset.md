# Point-in-time backtesting fixture

`analytics.backtesting.build_fixture_backtesting_dataset()` provides a small,
deterministic, network-free dataset for `fixture-company` and
`fixture-security`. It contains USD/share prices, USD income-statement
fundamentals, revenue forecasts, direct/thematic peer memberships, and sector
/ industry classifications. The fixture spans 2025-01-01 through 2026-07-02
and intentionally includes a missing pre-availability window and a later
classification/peer revision.

Each record keeps its observation or effective date separate from the date it
became available. `PointInTimeDataset.snapshot(as_of)` includes a record only
when both dates are no later than `as_of`; future prices, fundamentals,
forecasts, memberships, and classifications are therefore unavailable to an
earlier analysis. Empty windows return empty tuples. Values retain their
provider-contract units and `fixture-backtest` provenance.

This is a small PoC fixture, not a production historical database. It does not
represent a tradable universe, survivorship-bias correction, corporate-action
research, or evidence of predictive performance.

## Minimum recommendation backtest

`analytics.backtesting.run_recommendation_backtest(dataset)` runs the scoring
and recommendation engines against each requested point-in-time snapshot. It
reports forward adjusted-close returns, an optional benchmark comparison,
entry hit rate, compounded return, maximum drawdown, a Sharpe-like descriptive
ratio, component-conditioned results, and sensitivity to weight presets and
lookback windows. Signal inputs are restricted to records visible at the
analysis date; future prices are used only to measure outcomes.

The output is deliberately labeled as a small fixture-based PoC. It is not a
tradable-universe study and must not be used to make predictive or investment
claims.
