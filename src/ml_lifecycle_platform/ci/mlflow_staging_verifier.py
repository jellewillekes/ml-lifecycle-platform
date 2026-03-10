from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile

import mlflow
from mlflow import MlflowClient
import requests


class VerificationError(RuntimeError):
    """Raised when hosted MLflow staging verification fails."""


@dataclass(frozen=True)
class MlflowStagingVerificationConfig:
    tracking_uri: str
    tracking_token: str
    experiment_name: str
    run_name: str = "staging-smoke"
    artifact_name: str = "smoke.txt"
    artifact_body: str = "mlflow staging smoke\n"


def verify_http_reachable(config: MlflowStagingVerificationConfig) -> None:
    response = requests.get(
        config.tracking_uri.rstrip("/") + "/",
        headers={"Authorization": f"Bearer {config.tracking_token}"},
        timeout=15,
    )
    if response.status_code != 200:
        raise VerificationError(
            f"expected authenticated GET / to return 200, got {response.status_code}."
        )


def verify_mlflow_roundtrip(config: MlflowStagingVerificationConfig) -> str:
    mlflow.set_tracking_uri(config.tracking_uri)
    client = MlflowClient()

    experiment = mlflow.get_experiment_by_name(config.experiment_name)
    if experiment is None:
        experiment_id = client.create_experiment(config.experiment_name)
    else:
        experiment_id = experiment.experiment_id

    with tempfile.TemporaryDirectory(prefix="mlflow-staging-smoke-") as tmpdir:
        artifact_path = Path(tmpdir) / config.artifact_name
        artifact_path.write_text(config.artifact_body, encoding="utf-8")

        with mlflow.start_run(
            experiment_id=experiment_id, run_name=config.run_name
        ) as run:
            mlflow.log_param("smoke_check", "true")
            mlflow.log_artifact(str(artifact_path))
            run_id = run.info.run_id

    artifacts = client.list_artifacts(run_id)
    artifact_names = {entry.path for entry in artifacts}
    if config.artifact_name not in artifact_names:
        raise VerificationError(
            "expected staged MLflow artifact roundtrip to expose "
            f"{config.artifact_name!r}, got {sorted(artifact_names)!r}."
        )

    return run_id


def verify_staging(config: MlflowStagingVerificationConfig) -> str:
    verify_http_reachable(config)
    return verify_mlflow_roundtrip(config)
