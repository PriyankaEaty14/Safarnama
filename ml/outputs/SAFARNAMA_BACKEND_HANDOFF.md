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

- Routes: 20
- Prediction rows: 3360
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
