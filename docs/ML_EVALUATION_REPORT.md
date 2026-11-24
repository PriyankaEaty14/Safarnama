# ML evaluation report

The deployed estimator is Member 1’s mean of ticket counts by directional
route, weekday and hour. It uses the refitted October 1–31, 2026 artifact,
the original predictor, the published response schema and the application’s
explicit GTFS crosswalk. Validation checks both route names, the operator,
unique route-hour keys, finite nonnegative estimates and variability, integer
nonnegative observation counts, and artifact provenance. The runtime returns
historical day counts and standard deviation as descriptive context.

| Artifact check | Result |
|---|---|
| LF file SHA-256 | `16841fff58fc44447f9a66e26242af08460ea87a3c3fa86fdd96227d68a0cf14` |
| Original CRLF SHA-256 in manifest | `a2a8d33e9c75ef983af643cb7f3173284f888bb1897aa3f7bc9d83207472e50e` |
| Matched directional routes | 20 of 2,574 imported |
| Verified bucket keys | 3,360 of 3,360 for the export |
| Observed lookup parity | 717AUP, Friday 08:00 IST, 82.6 estimated tickets |

## Member 1 held-out evidence

Member 1 used 1–24 October for training and 25–31 October for comparing models.
The held-out window was used for model selection. It supports the choice of
baseline within this month. The recovered workspace lacked the raw ETM
observations and full prediction export, so the figures below were transcribed
from Member 1’s report. [Original validation report](../ml/outputs/ML_VALIDATION_REPORT.md)

| Scope and model | MAE | RMSE | WAPE |
|---|---:|---:|---:|
| Full, historical mean | 0.549 | 1.539 | 58.19% |
| Full, CatBoost | 0.672 | 1.978 | 71.30% |
| Top 20, historical mean | 4.243 | 6.900 | 29.52% |
| Top 20, CatBoost | 6.542 | 11.290 | 45.51% |

## Segment occupancy and expanded coverage

The research pipeline reconstructs candidate runs from ticket boarding and
alighting events and checks boarding/alighting arithmetic. Verified trip IDs,
boarding and alighting observations for complete runs, and vehicle assignments
with capacity are needed to evaluate segment loads. Independent ground truth
must cover different routes and times before deploying any crowding bands or
occupancy ratios. The application returns an unavailable status and leaves
segment fields null. Route-hour estimates give no vehicle or seat allocation.

For the larger artifact supply the original authorized export with matching
metadata and independently reviewed directional mapping. The validator reads
the manifest’s named CSV and the deployment can use a custom crosswalk.
Coverage and missing buckets are visible through the API. Routes without an
accepted mapping return an explicit unsupported status.
[Reproducibility instructions](../ml/REPRODUCIBILITY.md)
