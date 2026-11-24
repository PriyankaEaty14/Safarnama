# SAFARNAMA — Final ML Technical Validation Report

## 1. Project scope

SAFARNAMA addresses crowdedness-aware journey planning
using October 2026 Delhi ETM ticket records and
static GTFS schedules.

The implemented forecasting output is historical
route-hour ticket demand.

Experimental ticket-derived load reconstruction
is maintained separately.

## 2. Stop matching

| Metric | V2 | V3 |
|---|---:|---:|
| Cleaned ticket records | 1,317,730 | 1,317,730 |
| Both-stop coverage | 55.3409% | 62.8224% |
| GTFS-ordered journeys | 728,657 | 826,960 |
| Records with unmatched stops | 588,486 | 489,900 |
| Invalid order after matching | 587 | 870 |

Additional GTFS-ordered journeys:
98,303.

Coverage is not geographic matching accuracy.

## 3. Matching quality review

- Review sample: 45
- Name-consistent mappings: 42
- Substantive name conflicts: 3
- Sample name consistency: 93.3333%
- Flagged endpoint occurrences: 692

The review was AI-assisted name comparison.

Independent geographic precision remains unmeasured.

The sample was stratified by matching method and its
unweighted consistency rate is not population accuracy.

## 4. Candidate-run sensitivity

15 dataset-threshold
combinations were evaluated.

V3 results:

| Gap (minutes) | Candidate runs | Singleton % |
|---:|---:|---:|
| 15 | 550,579 | 73.66% |
| 30 | 485,444 | 67.39% |
| 45 | 457,031 | 64.11% |
| 60 | 443,266 | 62.25% |
| 90 | 432,637 | 60.59% |

The original 45-minute threshold is retained for
reproducibility, not because it is physically validated.

Candidate-run counts depend on the grouping threshold
and the ticket records included.

## 5. Experimental load reconstruction

Candidate runs included in the multi-run report:
20.

Repeated-stop ambiguity is represented through
conditional ticket-load bounds rather than forcing
the earliest stop occurrence.

Tied best-supported GTFS patterns are preserved.

The original conflicting scheduled trip identifiers
were compared using canonical ordered stop sequences.

Identical ordered sequences:
True.

Mathematical consistency does not establish physical
trip identity or actual onboard occupancy.

See the multi-run report and profile CSV for details.

## 6. Historical demand forecasting

The route-weekday-hour historical mean is retained.

Previous chronological evaluation used October 1–24
for training and October 25–31 for evaluation.

The baseline outperformed the tested CatBoost model
on the selected top-20-route evaluation.

See FORECAST_MODEL_DECISION.md and the earlier
ML validation reports for the recorded comparisons.

The evaluation period was reused for model comparisons;
it is not an untouched final test set.

The deployment prediction table is refitted using
the full October dataset.

## 7. Backend integration

- Prediction routes: 20
- Prediction rows: 3360
- Response schema version: 1.0
- Missing predictions: null
- Timezone: Asia/Kolkata
- Prediction scope: route-hour

The interface exposes historical variability and
sample counts without fabricated confidence scores.

## 8. Automated validation

Run the current test suite using:

```powershell
python -m compileall -q src
python -m pytest -q
```

Test results must be taken from actual execution.

## 9. Limitations

- Physical bus trips are not independently verified.
- Ticket issue times may differ from boarding times.
- Ticket destinations may differ from actual exits.
- Pass holders and other riders may be absent.
- Stop matching remains geographically unverified.
- Candidate grouping is threshold-sensitive.
- No-transaction hours may be zero-filled.
- Vehicle capacity and seated passenger counts
  are unavailable.
- Live passenger counts are unavailable.
- Prediction intervals are not calibrated.
- Future segment-level forecasts are not implemented.

## 10. Conclusion

SAFARNAMA provides a reproducible historical ticket
demand baseline and experimental ticket-derived
load reconstruction.

The route-hour forecast is ready for backend
integration under the documented metric contract.

Actual occupancy, seat availability and live
crowdedness remain unverified and are not claimed.
