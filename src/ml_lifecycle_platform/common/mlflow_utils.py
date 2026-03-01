from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.common.config import get_registry_uri, get_tracking_uri


def ensure_experiment(name: str) -> str:
    exp = mlflow.get_experiment_by_name(name)
    if exp is None:
        return mlflow.create_experiment(name)
    return exp.experiment_id


def client() -> MlflowClient:
    return MlflowClient(
        tracking_uri=get_tracking_uri(),
        registry_uri=get_registry_uri(),
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
