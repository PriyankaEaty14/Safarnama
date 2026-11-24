
"""Generate final SAFARNAMA ML handoff documentation."""

from pathlib import Path
import json
import hashlib
import pandas as pd

try:
    from .safarnama_predictor import SafarnamaPredictor
except ImportError:
    from safarnama_predictor import SafarnamaPredictor


BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"

OUT.mkdir(parents=True, exist_ok=True)

CSV = OUT / "demo_route_predictions.csv"


def read_json(name):
    return json.loads(
        (OUT / name).read_text(encoding="utf-8")
    )


def save_json(name, content):
    (OUT / name).write_text(
        json.dumps(
            content,
            indent=2,
            allow_nan=False
        ),
        encoding="utf-8"
    )


def save_text(name, content):
    (OUT / name).write_text(
        content.strip() + "\n",
        encoding="utf-8"
    )


def sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def main():

    print("Generating final SAFARNAMA handoff...")

    coverage = read_json(
        "matching_coverage_audit.json"
    )

    review = read_json(
        "manual_matching_review_summary.json"
    )

    sensitivity = read_json(
        "candidate_run_sensitivity_v2.json"
    )

    occupancy = read_json(
        "multi_run_occupancy_summary_v2.json"
    )

    legacy = read_json(
        "legacy_pattern_comparison_v2.json"
    )

    predictor = SafarnamaPredictor(CSV)

    df = pd.read_csv(CSV)

    v2 = next(
        row for row in coverage["results"]
        if row["matching_version"] == "V2"
    )

    v3 = next(
        row for row in coverage["results"]
        if row["matching_version"] == "V3"
    )

    examples = {
        "available": predictor.predict(
            "717AUP",
            "2026-11-27T08:00:00+05:30"
        ),

        "unknown_route": predictor.predict(
            "UNKNOWN_ROUTE",
            "2026-11-27T08:00:00+05:30"
        ),

        "zero_prediction": predictor.predict(
            "433DOWN",
            "2026-11-30T00:00:00+05:30"
        ),

        "utc_conversion": predictor.predict(
            "717AUP",
            "2026-11-27T02:30:00Z"
        ),

        "stop_context": predictor.predict(
            "717AUP",
            "2026-11-27T08:00:00+05:30",
            boarding_stop_id="123",
            alighting_stop_id="456"
        )
    }

    save_json(
        "safarnama_api_examples.json",
        examples
    )

    manifest = {
        "project": "SAFARNAMA",
        "schema_version": "1.0",
        "dataset": CSV.name,
        "sha256": sha256(CSV),
        "prediction_rows": int(len(df)),
        "routes": int(df["route"].nunique()),
        "model": "route_weekday_hour_mean",
        "training_start": "2026-10-01",
        "training_end": "2026-10-31",
        "timezone": "Asia/Kolkata",
        "prediction_scope": "route_hour",
        "metric": (
            "historical_ticketed_passengers_per_route_hour"
        ),
        "is_live": False,
        "is_actual_occupancy": False,
        "segment_prediction_available": False,
        "coverage_scope": "selected_demo_routes",
        "confidence_calibrated": False
    }

    save_json(
        "safarnama_prediction_manifest.json",
        manifest
    )

    # Formal JSON Schema for the integration response.

    nullable_number = {
        "type": ["number", "null"],
        "minimum": 0
    }

    nullable_string = {
        "type": ["string", "null"]
    }

    properties = {
        "schema_version": {"const": "1.0"},
        "route": {"type": "string", "minLength": 1},

        "direction": {
            "enum": ["UP", "DOWN", None]
        },

        "boarding_stop_id": nullable_string,
        "alighting_stop_id": nullable_string,

        "applicable_datetime": {
            "type": "string",
            "format": "date-time"
        },

        "applicable_hour_start": {
            "type": "string",
            "format": "date-time"
        },

        "timezone": {"const": "Asia/Kolkata"},

        "day_of_week": {
            "type": "integer",
            "minimum": 0,
            "maximum": 6
        },

        "hour": {
            "type": "integer",
            "minimum": 0,
            "maximum": 23
        },

        "metric": {
            "const": (
                "historical_ticketed_passengers_per_route_hour"
            )
        },

        "predicted_value": nullable_number,

        "unit": {
            "const": "ticketed_passengers_per_route_hour"
        },

        "prediction_scope": {
            "const": "route_hour"
        },

        "source": {
            "const": "October_2026_ETM_historical_baseline"
        },

        "training_period": {
            "type": "object",
            "required": ["start", "end"],
            "properties": {
                "start": {"const": "2026-10-01"},
                "end": {"const": "2026-10-31"}
            },
            "additionalProperties": False
        },

        "model": {
            "const": "route_weekday_hour_mean"
        },

        "data_availability": {
            "enum": [
                "available",
                "route_not_in_prediction_dataset",
                "prediction_not_available"
            ]
        },

        "prediction_available": {
            "type": "boolean"
        },

        "stop_context_status": {
            "enum": [
                "not_requested",
                "provided_not_validated"
            ]
        },

        "segment_prediction_available": {
            "const": False
        },

        "uncertainty": {
            "type": "object",

            "required": [
                "status",
                "confidence_score",
                "lower_bound",
                "upper_bound",
                "historical_daily_std",
                "historical_calendar_days",
                "historical_days_note",
                "note"
            ],

            "properties": {
                "status": {
                    "enum": [
                        "not_calibrated",
                        "prediction_unavailable"
                    ]
                },

                "confidence_score": {"type": "null"},
                "lower_bound": {"type": "null"},
                "upper_bound": {"type": "null"},

                "historical_daily_std": nullable_number,

                "historical_calendar_days": {
                    "type": ["integer", "null"],
                    "minimum": 0
                },

                "historical_days_note": {
                    "type": "string"
                },

                "note": {"type": "string"}
            },

            "additionalProperties": False
        },

        "is_live": {"const": False},
        "is_actual_occupancy": {"const": False},
        "physical_trip_verified": {"const": False},

        "actual_occupancy": {"type": "null"},
        "occupancy_percentage": {"type": "null"},
        "remaining_seats": {"type": "null"},
        "crowdedness_category": {"type": "null"},

        "display_label": {"type": "string"},

        "limitations": {
            "type": "array",
            "items": {"type": "string"}
        }
    }

    schema = {
        "$schema": (
            "https://json-schema.org/draft/2020-12/schema"
        ),
        "title": "SAFARNAMA Historical Demand Response",
        "type": "object",
        "required": list(properties.keys()),
        "properties": properties,
        "additionalProperties": False,

        "if": {
            "properties": {
                "prediction_available": {"const": True}
            }
        },

        "then": {
            "properties": {
                "predicted_value": {
                    "type": "number",
                    "minimum": 0
                },
                "data_availability": {
                    "const": "available"
                },
                "uncertainty": {
                    "properties": {
                        "status": {
                            "const": "not_calibrated"
                        }
                    }
                }
            }
        },

        "else": {
            "properties": {
                "predicted_value": {"type": "null"},
                "data_availability": {
                    "enum": [
                        "route_not_in_prediction_dataset",
                        "prediction_not_available"
                    ]
                },
                "uncertainty": {
                    "properties": {
                        "status": {
                            "const": "prediction_unavailable"
                        }
                    }
                }
            }
        }
    }

    save_json(
        "safarnama_prediction_schema.json",
        schema
    )

    # Backend integration documentation.

    guide = f"""
# SAFARNAMA — ML Backend Integration Guide

## Purpose

Expose historical route-hour ticket demand to the
SAFARNAMA journey planner.

The model is not a live bus occupancy model.

## Required files

- src/demand_lookup.py
- src/safarnama_predictor.py
- outputs/demo_route_predictions.csv
- outputs/safarnama_prediction_schema.json
- outputs/safarnama_prediction_manifest.json

## Dataset coverage

- Routes: {manifest['routes']}
- Prediction rows: {manifest['prediction_rows']}
- Training period: October 1–31, 2026
- Timezone: Asia/Kolkata
- Model: route-weekday-hour historical mean

## Python integration

Run from the ml directory, or add the ml directory
to the backend Python module search path.

```python
from src.safarnama_predictor import SafarnamaPredictor

predictor = SafarnamaPredictor()

result = predictor.predict(
    route="717AUP",
    applicable_datetime="2026-11-27T08:00:00+05:30"
)
```

Initialize the predictor once during backend startup.

## Input fields

| Field | Description |
|---|---|
| route | Complete directional ETM route code |
| applicable_datetime | ISO datetime with timezone |
| boarding_stop_id | Optional request context |
| alighting_stop_id | Optional request context |
| direction | Optional UP or DOWN |

The planner must independently validate stop order,
route identity and scheduled service availability.

## Output interpretation

- prediction_available=true: prediction key exists.
- prediction_available=false: prediction unavailable.
- predicted_value=null: missing prediction.
- predicted_value=0: zero-valued historical estimate.
- historical_daily_std: historical variability.
- historical_calendar_days: calendar-day sample count.

Calendar-day samples can include zero-filled
no-transaction hours.

Historical variability is not a calibrated confidence
interval.

## Frontend display rules

Display the metric as Historical ticket demand.

Never present this metric as:

- Number of passengers currently on a bus.
- Remaining seats.
- Live crowdedness.
- Occupancy percentage.
- Segment-level crowding.

For unavailable predictions, display Data unavailable.

Do not substitute missing predictions with zero.

Do not infer a low-crowding bus from a zero estimate.

## Experimental load profiles

The multi-run reconstruction files contain historical
ticket-derived load profiles conditional on candidate
run grouping and GTFS stop patterns.

These are separate from the route-hour forecast API.

They do not establish actual bus occupancy or future
segment-level crowding.

## Response examples

See outputs/safarnama_api_examples.json.

## Formal response schema

See outputs/safarnama_prediction_schema.json.
"""

    save_text(
        "SAFARNAMA_BACKEND_HANDOFF.md",
        guide
    )

    # Final technical report.

    sensitivity_table = pd.DataFrame(
        sensitivity["results"]
    )

    v3_sensitivity = sensitivity_table[
        sensitivity_table["dataset"] == "v3_ordered"
    ]

    table_lines = [
        "| Gap (minutes) | Candidate runs | Singleton % |",
        "|---:|---:|---:|"
    ]

    for row in v3_sensitivity.itertuples():

        table_lines.append(
            f"| {row.gap_minutes} "
            f"| {row.candidate_runs:,} "
            f"| {row.singleton_run_percentage:.2f}% |"
        )

    sensitivity_md = "\n".join(table_lines)

    report = f"""
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
| Cleaned ticket records | {v2['total_cleaned_ticket_records']:,} | {v3['total_cleaned_ticket_records']:,} |
| Both-stop coverage | {v2['both_stop_coverage_pct']:.4f}% | {v3['both_stop_coverage_pct']:.4f}% |
| GTFS-ordered journeys | {v2['gtfs_ordered_journeys']:,} | {v3['gtfs_ordered_journeys']:,} |
| Records with unmatched stops | {v2['records_with_unmatched_stops']:,} | {v3['records_with_unmatched_stops']:,} |
| Invalid order after matching | {v2['both_matched_but_invalid_order']:,} | {v3['both_matched_but_invalid_order']:,} |

Additional GTFS-ordered journeys:
{v3['gtfs_ordered_journeys'] - v2['gtfs_ordered_journeys']:,}.

Coverage is not geographic matching accuracy.

## 3. Matching quality review

- Review sample: {review['total_samples_reviewed']}
- Name-consistent mappings: {review['name_consistent']}
- Substantive name conflicts: {review['name_conflicts']}
- Sample name consistency: {review['sample_name_consistency_pct']}%
- Flagged endpoint occurrences: {review['suspected_conflict_endpoint_occurrences']}

The review was AI-assisted name comparison.

Independent geographic precision remains unmeasured.

The sample was stratified by matching method and its
unweighted consistency rate is not population accuracy.

## 4. Candidate-run sensitivity

{len(sensitivity['results'])} dataset-threshold
combinations were evaluated.

V3 results:

{sensitivity_md}

The original 45-minute threshold is retained for
reproducibility, not because it is physically validated.

Candidate-run counts depend on the grouping threshold
and the ticket records included.

## 5. Experimental load reconstruction

Candidate runs included in the multi-run report:
{len(occupancy['runs'])}.

Repeated-stop ambiguity is represented through
conditional ticket-load bounds rather than forcing
the earliest stop occurrence.

Tied best-supported GTFS patterns are preserved.

The original conflicting scheduled trip identifiers
were compared using canonical ordered stop sequences.

Identical ordered sequences:
{legacy['identical_ordered_stop_sequences']}.

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

- Prediction routes: {manifest['routes']}
- Prediction rows: {manifest['prediction_rows']}
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
"""

    save_text(
        "SAFARNAMA_FINAL_ML_REPORT.md",
        report
    )

    print("\nFINAL HANDOFF GENERATED")
    print("=" * 60)

    print("Prediction routes:", manifest["routes"])
    print("Prediction rows:", manifest["prediction_rows"])

    print("\nGenerated files:")

    for name in [
        "safarnama_api_examples.json",
        "safarnama_prediction_manifest.json",
        "safarnama_prediction_schema.json",
        "SAFARNAMA_BACKEND_HANDOFF.md",
        "SAFARNAMA_FINAL_ML_REPORT.md"
    ]:
        print("-", name)

    print("\nNo existing model files modified.")


if __name__ == "__main__":
    main()
