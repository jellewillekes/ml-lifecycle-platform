"""Row-level feature-contract validation used by the serving layer to
reject malformed ``/predict`` inputs and by the pipeline for dataset checks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ml_lifecycle_platform.core.model_spec_types import (
    FeatureContractSpec,
    FeatureFieldSpec,
)


@dataclass(frozen=True)
class FeatureContractIssue:
    row: int
    code: str
    message: str
    field: str | None = None
    expected_type: str | None = None
    actual_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "row": self.row,
            "code": self.code,
            "message": self.message,
        }
        if self.field is not None:
            payload["field"] = self.field
        if self.expected_type is not None:
            payload["expected_type"] = self.expected_type
        if self.actual_type is not None:
            payload["actual_type"] = self.actual_type
        return payload


class FeatureContractValidationError(ValueError):
    def __init__(
        self,
        *,
        contract: FeatureContractSpec,
        issues: Sequence[FeatureContractIssue],
    ) -> None:
        super().__init__("Prediction request does not match feature contract.")
        self.contract = contract
        self.issues = tuple(issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": "INVALID_FEATURE_CONTRACT",
            "message": "Prediction request does not match feature contract.",
            "contract_version": self.contract.version,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _actual_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def _validate_value(value: Any, feature: FeatureFieldSpec) -> tuple[bool, Any]:
    if feature.dtype == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, value
        if not math.isfinite(float(value)):
            return False, value
        return True, float(value)
    if feature.dtype == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            return False, value
        return True, value
    if feature.dtype == "bool":
        if not isinstance(value, bool):
            return False, value
        return True, value
    if feature.dtype == "string":
        if not isinstance(value, str):
            return False, value
        return True, value
    return False, value


def _validate_row(
    row_idx: int,
    row: Mapping[str, Any],
    contract: FeatureContractSpec,
    allowed_names: set[str],
) -> tuple[dict[str, Any], list[FeatureContractIssue]]:
    row_payload = dict(row)
    validated_row: dict[str, Any] = {}
    issues: list[FeatureContractIssue] = []

    for feature in contract.features:
        if feature.name not in row_payload:
            if feature.required:
                issues.append(
                    FeatureContractIssue(
                        row=row_idx,
                        field=feature.name,
                        code="missing_field",
                        message="Required feature is missing from request row.",
                        expected_type=feature.dtype,
                    )
                )
            continue

        ok, normalized_value = _validate_value(row_payload[feature.name], feature)
        if not ok:
            issues.append(
                FeatureContractIssue(
                    row=row_idx,
                    field=feature.name,
                    code="type_mismatch",
                    message="Feature value does not match the declared contract type.",
                    expected_type=feature.dtype,
                    actual_type=_actual_type(row_payload[feature.name]),
                )
            )
            continue
        validated_row[feature.name] = normalized_value

    if not contract.allow_unknown_fields:
        for field_name in sorted(set(row_payload) - allowed_names):
            issues.append(
                FeatureContractIssue(
                    row=row_idx,
                    field=field_name,
                    code="unknown_field",
                    message="Request row contains a field that is not declared in the feature contract.",
                )
            )

    return validated_row, issues


def validate_rows_against_contract(
    rows: Sequence[Mapping[str, Any]],
    contract: FeatureContractSpec,
) -> list[dict[str, Any]]:
    if not contract.features:
        return [dict(row) for row in rows]

    allowed_names = {feature.name for feature in contract.features}
    all_issues: list[FeatureContractIssue] = []
    validated_rows: list[dict[str, Any]] = []

    for row_idx, row in enumerate(rows):
        validated_row, row_issues = _validate_row(row_idx, row, contract, allowed_names)
        all_issues.extend(row_issues)
        validated_rows.append(validated_row)

    if all_issues:
        raise FeatureContractValidationError(contract=contract, issues=all_issues)

    return validated_rows
