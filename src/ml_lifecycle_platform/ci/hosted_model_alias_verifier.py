from __future__ import annotations

from dataclasses import dataclass

import mlflow
from mlflow import MlflowClient


class VerificationError(RuntimeError):
    """Raised when hosted MLflow model alias verification fails."""


@dataclass(frozen=True)
class HostedModelAliasVerificationConfig:
    tracking_uri: str
    tracking_token: str
    model_name: str
    alias: str = "prod"


def verify_model_alias(config: HostedModelAliasVerificationConfig) -> str:
    mlflow.set_tracking_uri(config.tracking_uri)
    client = MlflowClient()

    try:
        version = client.get_model_version_by_alias(config.model_name, config.alias)
    except Exception as error:
        raise VerificationError(
            "hosted MLflow is missing required model alias "
            f"'{config.model_name}@{config.alias}': {error}"
        ) from error

    resolved_version = str(getattr(version, "version", "")).strip()
    if not resolved_version:
        raise VerificationError(
            f"hosted MLflow alias '{config.model_name}@{config.alias}' returned an empty version."
        )

    return resolved_version
