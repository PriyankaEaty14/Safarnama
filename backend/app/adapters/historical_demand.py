"""Validate and connect the Member 1 historical-demand export to GTFS."""

import csv
from collections import Counter, defaultdict
from datetime import date, datetime
from hashlib import sha256
import importlib
import json
import logging
import re
from math import isfinite
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import select

from app.db.models import Route

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAPPING = Path(__file__).with_name("delhi_route_mapping.json")
METRIC = "historical_ticketed_passengers_per_route_hour"
MODEL = "route_weekday_hour_mean"


def validate_route_mapping(rows, routes, prediction_codes, *, require_all=True):
    """Use only explicit one-to-one matches corroborated by installed GTFS."""
    mapping = {}
    seen_codes = set()
    routes_by_id = {route.id: route for route in routes}
    by_code = defaultdict(set)
    for route in routes:
        for name in {route.short_name, route.long_name} - {None}:
            by_code[name.strip().upper()].add(route.id)
    for row in rows:
        route_id, code, agency = (row[key] for key in ("gtfs_route_id", "etm_route_code", "agency_id"))
        if route_id in mapping or code in seen_codes or code not in prediction_codes:
            raise ValueError("Duplicate or unknown GTFS-to-ETM mapping")
        seen_codes.add(code)
        route = routes_by_id.get(route_id)
        candidates = by_code[code]
        if not route or route.agency_id != agency or candidates != {route_id} or any(
            (name or "").strip().upper() != code for name in (route.short_name, route.long_name)
        ):
            raise ValueError(f"GTFS mapping is missing, ambiguous or changed for {code}")
        mapping[route_id] = code
    if not mapping or (require_all and seen_codes != prediction_codes):
        raise ValueError("GTFS mapping must explicitly account for every prediction route")
    return mapping


class HistoricalDemandAdapter:
    def __init__(self, directory: Path, database, mapping_path: Path = MAPPING):
        manifest = json.loads((directory / "safarnama_prediction_manifest.json").read_text())
        schema = json.loads((directory / "safarnama_prediction_schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())
        expected = {
            "schema_version": "1.0", "timezone": "Asia/Kolkata",
            "prediction_scope": "route_hour", "metric": METRIC, "model": MODEL,
            "is_live": False, "is_actual_occupancy": False, "confidence_calibrated": False,
            "segment_prediction_available": False,
        }
        if any(manifest.get(key) != value for key, value in expected.items()):
            raise ValueError("Unsupported historical demand manifest")
        scope = manifest.get("coverage_scope", "selected_demo_routes")
        if scope not in {"selected_demo_routes", "full_network"}:
            raise ValueError("Unsupported historical coverage scope")
        filename = manifest["dataset"]
        if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,96}\.csv", filename):
            raise ValueError("Invalid prediction export filename")
        data_path = directory / filename
        if data_path.resolve().parent != directory.resolve():
            raise ValueError("Prediction export must remain inside the artifact directory")
        with data_path.open("rb") as data:
            limit = 32 * 1024 * 1024
            payload = data.read(limit + 1)
        if len(payload) > limit:
            raise ValueError("Historical export exceeds supported size")
        if sha256(payload).hexdigest() != manifest["sha256"]:
            # The delivered Git snapshot contains LF, while the export manifest
            # was produced with CRLF. Verify that exact conversion only.
            if b"\r" in payload or sha256(payload.replace(b"\n", b"\r\n")).hexdigest() != manifest["sha256"]:
                raise ValueError("Prediction export checksum mismatch")
            logger.info("Historical export checksum verified with CRLF line endings")
        self.training_period = {"start": manifest["training_start"], "end": manifest["training_end"]}
        training_start, training_end = (date.fromisoformat(self.training_period[key])
                                       for key in ("start", "end"))
        if training_start > training_end:
            raise ValueError("Invalid training period")
        codes, keys = set(), set()
        with data_path.open(encoding="utf-8-sig", newline="") as data:
            for row in csv.DictReader(data):
                code = row["route"]
                weekday, hour = int(row["day_of_week"]), int(row["hour"])
                estimate = float(row["predicted_passengers"])
                if not code or code != code.strip().upper() or weekday not in range(7) or hour not in range(24):
                    raise ValueError("Invalid route, weekday or hour")
                if not isfinite(estimate) or estimate < 0:
                    raise ValueError("Invalid historical estimate")
                std, days = row.get("daily_std"), row.get("observed_days")
                if std and (not isfinite(float(std)) or float(std) < 0):
                    raise ValueError("Invalid historical standard deviation")
                if days and (not float(days).is_integer() or float(days) < 0):
                    raise ValueError("Invalid historical day count")
                key = (code, weekday, hour)
                if key in keys:
                    raise ValueError("Duplicate historical demand key")
                codes.add(code)
                keys.add(key)
        if not keys or len(keys) != manifest["prediction_rows"] or len(codes) != manifest["routes"]:
            raise ValueError("Historical prediction counts do not match manifest")
        mapping_rows = json.loads(mapping_path.read_text())["routes"]
        routes = database.execute(select(Route.id, Route.short_name, Route.long_name, Route.agency_id)).all()
        self.routes = validate_route_mapping(
            mapping_rows, routes, codes, require_all=scope == "selected_demo_routes",
        )
        self.bucket_counts = Counter(code for code, _, _ in keys)
        self.prediction_rows = len(keys)
        self.gtfs_route_count = len(routes)
        self.artifact_sha256 = sha256(payload).hexdigest()

        # The original Member 1 package is shipped next to the backend.
        for source in (PROJECT_ROOT, Path(__file__).resolve().parents[2]):
            if str(source) not in sys.path:
                sys.path.append(str(source))
        predictor = importlib.import_module("ml.src.safarnama_predictor")
        self.predictor = predictor.SafarnamaPredictor(data_path)
        # Exercise the delivered interface during initialization.
        route_id = next(iter(self.routes))
        self.lookup(route_id, datetime.fromisoformat("2026-11-27T08:00:00+05:30"))

    def lookup(self, route_id: str, local_time: datetime) -> dict | None:
        if route_id not in self.routes:
            return None
        code = self.routes[route_id]
        result = self.predictor.predict(route=code, applicable_datetime=local_time)
        self.validator.validate(result)
        count = result["predicted_value"]
        variability = result["uncertainty"]["historical_daily_std"]
        if (
            result["route"] != code or result["day_of_week"] != local_time.weekday()
            or result["hour"] != local_time.hour or result["training_period"] != self.training_period
            or result["metric"] != METRIC or result["prediction_scope"] != "route_hour"
            or result["is_live"] is not False or result["is_actual_occupancy"] is not False
            or result["segment_prediction_available"] is not False
            or result["prediction_available"] != (count is not None)
            or any(value is not None and (not isfinite(value) or value < 0) for value in (count, variability))
        ):
            raise ValueError("Invalid historical prediction response")
        return result


def load_historical_demand(directory, engine, mapping_path=None):
    if directory is None:
        return None
    try:
        with engine.connect() as database:
            result = HistoricalDemandAdapter(directory, database, mapping_path or MAPPING)
    except Exception as error:
        logger.warning("Historical demand unavailable: %s", type(error).__name__)
        return None
    logger.info("Historical demand loaded for %d mapped routes", len(result.routes))
    return result
