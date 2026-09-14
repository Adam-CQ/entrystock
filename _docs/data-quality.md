# Data freshness and quality thresholds

Quality rules are versioned as `v1` in `analytics.data_quality`. Ages are
calendar days from the analysis date to the effective date (or retrieval date
when no effective date exists). The boundary itself is acceptable; a warning
starts above the warning age and blocking starts above the blocking age.

| Source | Warning age | Blocking age | Minimum coverage |
| --- | ---: | ---: | ---: |
| Prices | 3 days | 10 days | 1 observation |
| Fundamentals | 120 days | 365 days | 1 statement; revenue, operating income, and net income required |
| Forecasts | 90 days | 365 days | 1 source |
| Classifications | 365 days | 365 days | 1 record with provenance |
| Peers | 90 days | 365 days | 3 confirmed peers |

Zero coverage, future-dated records, invalid provider quality, or missing
required provenance is blocked or not-evaluable. Warnings remain visible and
can be used by the recommendation explanation; blocked and not-evaluable
inputs are never represented as valid calculated values.
