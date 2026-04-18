from __future__ import annotations

import mlflow
from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.runtime.bootstrap import (
    configure_mlflow,
    get_runtime_context,
)


def ensure_experiment(name: str) -> str:
    configure_mlflow()
    exp = mlflow.get_experiment_by_name(name)
    if exp is None:
        return mlflow.create_experiment(name)
    return exp.experiment_id


def client() -> MlflowClient:
    configure_mlflow()
    runtime = get_runtime_context()
    return MlflowClient(
        tracking_uri=runtime.metadata.tracking_uri,
        registry_uri=runtime.metadata.registry_uri,
    )
