# Shared analytics package

The `analytics` package contains framework-independent contracts used by the
Django/Celery application side and the FastAPI analytical service. It does not
import either web framework, Celery, databases, providers, or network clients.

The initial public boundaries are:

- `analytics.data_quality.DataQualityReport`
- `analytics.peer_analysis.PeerCandidate`
- `analytics.forecasts.ForecastValue`
- `analytics.valuation.ValuationResult`
- `analytics.momentum.MomentumSignal`
- `analytics.scoring.ScoreContribution`
- `analytics.explanations.Explanation`
- `analytics.backtesting.BacktestObservation`

These are typed value objects only. Calculation engines and provider adapters
are introduced by later issues behind these domain boundaries.
