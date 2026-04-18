"""HTTP reachability and round-trip smoke test for hosted MLflow staging —
retries through Cloud Run cold starts, then logs and reads back a tiny
artifact to prove tracking + artifact storage are both healthy."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
import tempfile

import mlflow
from mlflow import MlflowClient
import requests
from requests.exceptions import RequestException


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


# Cloud Run scale-to-zero: absorb MLflow cold starts, fail fast on auth errors.
_RETRY_DELAYS_SECONDS = (0, 5, 15, 45)
_REQUEST_TIMEOUT_SECONDS = 30


def verify_http_reachable(config: MlflowStagingVerificationConfig) -> None:
    url = config.tracking_uri.rstrip("/") + "/health"
    headers = {"Authorization": f"Bearer {config.tracking_token}"}

    last_error: Exception | None = None
    last_status: int | None = None

    for delay in _RETRY_DELAYS_SECONDS:
        if delay:
            time.sleep(delay)
        try:
            response = requests.get(
                url, headers=headers, timeout=_REQUEST_TIMEOUT_SECONDS
            )
        except RequestException as error:
            last_error = error
            continue
        if response.status_code == 200:
            return
        if response.status_code in (401, 403):
            raise VerificationError(
                f"MLflow staging at {url} returned {response.status_code}; "
                "check tracking token."
            )
        last_status = response.status_code
        last_error = None

    if last_error is not None:
        raise VerificationError(
            f"MLflow staging at {url} unreachable after "
            f"{len(_RETRY_DELAYS_SECONDS)} attempts: {last_error}"
        ) from last_error
    raise VerificationError(
        f"MLflow staging at {url} returned {last_status} after "
        f"{len(_RETRY_DELAYS_SECONDS)} attempts."
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
