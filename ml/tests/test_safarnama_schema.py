
from pathlib import Path
import json

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"


@pytest.fixture
def schema():
    return json.loads(
        (
            OUT / "safarnama_prediction_schema.json"
        ).read_text(encoding="utf-8")
    )


@pytest.fixture
def examples():
    return json.loads(
        (
            OUT / "safarnama_api_examples.json"
        ).read_text(encoding="utf-8")
    )


def test_schema_definition(schema):

    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize(
    "scenario",
    [
        "available",
        "unknown_route",
        "zero_prediction",
        "utc_conversion",
        "stop_context"
    ]
)
def test_response_schema(schema, examples, scenario):

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker()
    )

    validator.validate(examples[scenario])


def test_missing_prediction_cannot_be_zero(
    schema, examples
):

    response = examples["unknown_route"].copy()

    response["predicted_value"] = 0

    with pytest.raises(ValidationError):

        Draft202012Validator(schema).validate(
            response
        )


def test_occupancy_claim_rejected(schema, examples):

    response = examples["available"].copy()

    response["is_actual_occupancy"] = True

    with pytest.raises(ValidationError):

        Draft202012Validator(schema).validate(
            response
        )


def test_fabricated_seats_rejected(schema, examples):

    response = examples["available"].copy()

    response["remaining_seats"] = 20

    with pytest.raises(ValidationError):

        Draft202012Validator(schema).validate(
            response
        )
