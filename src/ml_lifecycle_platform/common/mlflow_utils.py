from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    runtime = get_runtime_context()
    content = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    try:
        relative_path = path.relative_to(runtime.artifacts_dir).as_posix()
    except ValueError:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return

    runtime.artifact_store.write_bytes(relative_path, content)
