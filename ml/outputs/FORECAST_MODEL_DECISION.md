# CrowdWise AI — Forecast Model Decision

## Selected model

**Historical route × weekday × hour mean baseline**

The original historical baseline is retained for the hackathon demonstration because it is simple, reproducible, and provides predictions across the configured route-hour grid.

## Evaluation

Training period: October 1–24, 2026
Test period: October 25–31, 2026

On 76,882 test route-hours with recorded ticket activity:

| Model | MAE | RMSE | WAPE |
|---|---:|---:|---:|
| Historical baseline | 1.998 | 3.161 | 45.91% |
| Hybrid (3-day threshold) | 2.002 | 3.156 | 46.00% |

The activity-conditioned baseline achieved 42.59% WAPE on 68,215 comparable test route-hours, but did not cover all observed test hours.

The hybrid achieved full prediction coverage but did not improve MAE or WAPE over the original baseline.

## Decision

Retain the original historical baseline for backend integration. Preserve the activity-conditioned and hybrid approaches as documented experiments.

## Limitations

- Predictions estimate historical **ticketed passenger demand per route-hour**, not physical bus occupancy or live crowdedness.
- Route-hours without recorded transactions cannot be independently classified as zero demand, non-operating service, or missing ETM data.
- Model comparisons used the October 25–31 holdout. It should not be described as an untouched final evaluation set after these experiments.
- Ticketed passenger demand is not equivalent to the number of passengers simultaneously aboard a bus.
- Predictions do not account for unticketed passengers or verified bus capacity.

## Future improvements

Validate operating hours against service schedules, obtain more months of ETM records, assess missing-data completeness, and evaluate on a new untouched chronological test period.
