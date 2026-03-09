from __future__ import annotations

from typing import Any

import pandas as pd
import pandera.pandas as pa
from pandera import Check
from pandera.errors import SchemaError, SchemaErrors

from ml_lifecycle_platform.core.model_specs import FeatureFieldSpec, ModelSpec


class BatchContractValidationError(ValueError):
    pass


def _pandera_dtype(feature: FeatureFieldSpec) -> Any:
    if feature.dtype == "float":
        return float
    if feature.dtype == "int":
        return int
    if feature.dtype == "bool":
        return bool
    if feature.dtype == "string":
        return str
    raise ValueError(f"Unsupported feature dtype: {feature.dtype}")


def _labeled_dataset_schema(spec: ModelSpec) -> pa.DataFrameSchema:
    columns: dict[str, pa.Column] = {
        feature.name: pa.Column(
            _pandera_dtype(feature),
            required=feature.required,
            nullable=not feature.required,
            coerce=False,
        )
        for feature in spec.feature_contract.features
    }
    columns[spec.label_column] = pa.Column(
        int,
        required=True,
        nullable=False,
        coerce=False,
        checks=Check.isin([0, 1]),
    )
    return pa.DataFrameSchema(
        columns=columns,
        strict=not spec.feature_contract.allow_unknown_fields,
        coerce=False,
    )


def _format_schema_error(error: SchemaError | SchemaErrors) -> str:
    failure_cases = getattr(error, "failure_cases", None)
    if failure_cases is None or getattr(failure_cases, "empty", True):
        return str(error)

    parts: list[str] = []
    records = failure_cases.head(5).to_dict(orient="records")
    for record in records:
        column = record.get("column")
        check = record.get("check")
        failure_case = record.get("failure_case")
        index = record.get("index")

        detail = []
        if column not in (None, "None", ""):
            detail.append(f"column={column}")
        if check not in (None, "None", ""):
            detail.append(f"check={check}")
        if failure_case not in (None, "None", ""):
            detail.append(f"failure_case={failure_case}")
        if index not in (None, "None", ""):
            detail.append(f"row={index}")

        if detail:
            parts.append(", ".join(str(item) for item in detail))

    if not parts:
        return str(error)
    return "; ".join(parts)


def validate_labeled_dataset(
    df: pd.DataFrame,
    *,
    spec: ModelSpec,
    stage: str,
    dataset_name: str,
) -> pd.DataFrame:
    schema = _labeled_dataset_schema(spec)
    try:
        return schema.validate(df, lazy=True)
    except (SchemaError, SchemaErrors) as error:
        message = _format_schema_error(error)
        raise BatchContractValidationError(
            f"{stage} dataset {dataset_name!r} failed contract validation: {message}"
        ) from error
