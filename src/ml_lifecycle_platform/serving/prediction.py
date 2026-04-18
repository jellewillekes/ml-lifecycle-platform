"""Build prediction payloads by running the primary model and, optionally,
the shadow model for diff observability."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
from mlflow.exceptions import MlflowException

from ml_lifecycle_platform.core.feature_contracts import (
    validate_rows_against_contract,
)
from ml_lifecycle_platform.core.model_spec_types import FeatureContractSpec

from .metrics import SHADOW_DIFF_MAE
from .model_store import ModelStore
from .router import Mode
from .settings import Settings

logger = logging.getLogger("serving")


@dataclass
class PredictionResult:
    y_primary: list[float]
    shadow_mae: float | None
    chosen_version: str | None


def run_prediction(
    store: ModelStore,
    settings: Settings,
    *,
    primary_alias: Literal["prod", "candidate"],
    shadow_alias: Literal["prod", "candidate"],
    run_shadow: bool,
    contract: FeatureContractSpec,
    rows: list[dict[str, Any]],
    mode: Mode,
) -> PredictionResult:
    validated_rows = validate_rows_against_contract(rows, contract)
    df = pd.DataFrame(validated_rows)

    model_primary = store.get_model(settings, primary_alias, required=True)
    if model_primary is None:
        raise RuntimeError(f"model not available: {primary_alias}")

    y_primary = [float(x) for x in model_primary.predict(df)]

    shadow_mae: float | None = None
    if run_shadow:
        model_shadow = store.get_model(settings, shadow_alias, required=False)
        if model_shadow is not None:
            try:
                y_shadow = [float(x) for x in model_shadow.predict(df)]
                diffs = [abs(a - b) for a, b in zip(y_primary, y_shadow)]
                shadow_mae = sum(diffs) / max(len(diffs), 1)
            except (MlflowException, ValueError) as e:
                logger.warning("shadow prediction failed: %s", e)

    if shadow_mae is not None and math.isfinite(shadow_mae):
        SHADOW_DIFF_MAE.labels(mode=str(mode)).observe(shadow_mae)

    return PredictionResult(
        y_primary=y_primary,
        shadow_mae=shadow_mae,
        chosen_version=store.get_version(primary_alias),
    )
