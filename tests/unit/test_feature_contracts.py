from __future__ import annotations

import pytest

from ml_lifecycle_platform.core.feature_contracts import (
    FeatureContractValidationError,
    validate_rows_against_contract,
)
from ml_lifecycle_platform.core.model_spec_types import (
    FeatureContractSpec,
    FeatureFieldSpec,
)

pytestmark = pytest.mark.unit


def _contract(*, allow_unknown_fields: bool = False) -> FeatureContractSpec:
    return FeatureContractSpec(
        version="test.input/v1",
        allow_unknown_fields=allow_unknown_fields,
        features=(
            FeatureFieldSpec(name="feature_a", dtype="float"),
            FeatureFieldSpec(name="feature_b", dtype="string"),
        ),
    )


def test_validate_rows_accepts_valid_rows() -> None:
    rows = [{"feature_a": 1.25, "feature_b": "ok"}]

    validated = validate_rows_against_contract(rows, _contract())

    assert validated == [{"feature_a": 1.25, "feature_b": "ok"}]


def test_validate_rows_rejects_missing_fields_with_stable_error_shape() -> None:
    rows = [{"feature_a": 1.25}]

    with pytest.raises(FeatureContractValidationError) as exc:
        validate_rows_against_contract(rows, _contract())

    assert exc.value.to_dict() == {
        "code": "INVALID_FEATURE_CONTRACT",
        "message": "Prediction request does not match feature contract.",
        "contract_version": "test.input/v1",
        "issues": [
            {
                "row": 0,
                "field": "feature_b",
                "code": "missing_field",
                "message": "Required feature is missing from request row.",
                "expected_type": "string",
            }
        ],
    }


def test_validate_rows_rejects_unknown_fields() -> None:
    rows = [{"feature_a": 1.25, "feature_b": "ok", "extra": 99}]

    with pytest.raises(FeatureContractValidationError) as exc:
        validate_rows_against_contract(rows, _contract())

    assert exc.value.to_dict()["issues"] == [
        {
            "row": 0,
            "field": "extra",
            "code": "unknown_field",
            "message": "Request row contains a field that is not declared in the feature contract.",
        }
    ]


def test_validate_rows_rejects_type_mismatches() -> None:
    rows = [{"feature_a": "bad", "feature_b": "ok"}]

    with pytest.raises(FeatureContractValidationError) as exc:
        validate_rows_against_contract(rows, _contract())

    assert exc.value.to_dict()["issues"] == [
        {
            "row": 0,
            "field": "feature_a",
            "code": "type_mismatch",
            "message": "Feature value does not match the declared contract type.",
            "expected_type": "float",
            "actual_type": "string",
        }
    ]


def test_validate_rows_drops_unknown_fields_when_allowed() -> None:
    rows = [{"feature_a": 1.25, "feature_b": "ok", "extra": 99}]

    validated = validate_rows_against_contract(
        rows, _contract(allow_unknown_fields=True)
    )

    assert validated == [{"feature_a": 1.25, "feature_b": "ok"}]
