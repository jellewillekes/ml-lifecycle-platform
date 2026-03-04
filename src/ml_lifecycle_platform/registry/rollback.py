from __future__ import annotations

import logging
import os

from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.common.constants import ALIAS_PROD, TAG_PREVIOUS_PROD_VERSION
from ml_lifecycle_platform.common.mlflow_utils import client as mlflow_client

logger = logging.getLogger(__name__)


def rollback_prod(client: MlflowClient, model_name: str) -> None:
    """Roll back prod to the recorded previous prod version."""
    current_prod = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    tags = current_prod.tags or {}
    prev = str(tags.get(TAG_PREVIOUS_PROD_VERSION, "")).strip()

    if not prev:
        raise RuntimeError(
            "Rollback blocked: current prod does not have a previous prod recorded. "
            f"Expected tag '{TAG_PREVIOUS_PROD_VERSION}' on current prod model version."
        )

    client.set_registered_model_alias(model_name, ALIAS_PROD, prev)

    # Allow a one-step undo.
    client.set_model_version_tag(
        name=model_name,
        version=prev,
        key=TAG_PREVIOUS_PROD_VERSION,
        value=str(current_prod.version),
    )

    logger.info(
        "Rolled back %s prod -> v%s (from v%s)", model_name, prev, current_prod.version
    )


def get_model_name() -> str:
    return os.environ.get("MODEL_NAME", "breast_cancer_clf")


def main() -> None:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    rollback_prod(mlflow_client(), get_model_name())


if __name__ == "__main__":
    main()
