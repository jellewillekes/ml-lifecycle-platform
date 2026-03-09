from __future__ import annotations

import argparse
import json
import logging
import sys

from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.common.config import get_log_level, get_model_name
from ml_lifecycle_platform.common.mlflow_utils import client as mlflow_client
from ml_lifecycle_platform.common.constants import (
    ALIAS_CANDIDATE,
    ALIAS_CHAMPION,
    ALIAS_PROD,
    RELEASE_STATUS_PREVIOUS_PROD,
    TAG_PREVIOUS_PROD_VERSION,
    TAG_PROMOTED_FROM_ALIAS,
    TAG_RELEASE_STATUS,
)
from ml_lifecycle_platform.policy.release_policy import (
    PolicyDecision,
    evaluate_promotion_policy,
)

logger = logging.getLogger(__name__)


def _print_decision(decision: PolicyDecision, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
        return

    print(f"allowed={decision.allowed}")
    for v in decision.errors:
        print(f"ERROR {v.code}: {v.message} {v.details}")
    for v in decision.warnings:
        print(f"WARN  {v.code}: {v.message} {v.details}")
    print(f"context={decision.context}")


def _try_get_prod_version(client: MlflowClient, model_name: str) -> str | None:
    try:
        prod = client.get_model_version_by_alias(model_name, ALIAS_PROD)
    except Exception:
        return None
    return str(prod.version)


def apply_promotion(
    client: MlflowClient, model_name: str, candidate_version: str, from_alias: str
) -> None:
    """Promote one candidate version and record rollback metadata."""

    prev_prod_version = _try_get_prod_version(client, model_name)

    client.set_registered_model_alias(model_name, ALIAS_PROD, candidate_version)
    client.set_registered_model_alias(model_name, ALIAS_CHAMPION, candidate_version)

    client.set_model_version_tag(
        name=model_name,
        version=candidate_version,
        key=TAG_RELEASE_STATUS,
        value=ALIAS_PROD,
    )
    client.set_model_version_tag(
        name=model_name,
        version=candidate_version,
        key=TAG_PROMOTED_FROM_ALIAS,
        value=from_alias,
    )

    if prev_prod_version is not None:
        # Rollback reads this tag instead of inferring state from history.
        client.set_model_version_tag(
            name=model_name,
            version=candidate_version,
            key=TAG_PREVIOUS_PROD_VERSION,
            value=prev_prod_version,
        )

        try:
            client.set_model_version_tag(
                name=model_name,
                version=prev_prod_version,
                key=TAG_RELEASE_STATUS,
                value=RELEASE_STATUS_PREVIOUS_PROD,
            )
        except Exception:
            logger.info(
                "Could not mark old prod version %s as %s",
                prev_prod_version,
                RELEASE_STATUS_PREVIOUS_PROD,
            )

    logger.info(
        "Promoted %s v%s -> alias '%s' and '%s'",
        model_name,
        candidate_version,
        ALIAS_PROD,
        ALIAS_CHAMPION,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Promote candidate model to prod with policy gating."
    )
    p.add_argument("--model-name", default=get_model_name())
    p.add_argument("--from-alias", default=ALIAS_CANDIDATE)
    p.add_argument("--to-alias", default=ALIAS_PROD)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate policy only; do not mutate registry.",
    )
    p.add_argument("--format", choices=["json", "text"], default="json")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=get_log_level())

    args = parse_args(sys.argv[1:] if argv is None else argv)

    client = mlflow_client()
    decision = evaluate_promotion_policy(
        client=client,
        model_name=args.model_name,
        from_alias=args.from_alias,
        to_alias=args.to_alias,
    )

    _print_decision(decision, args.format)

    if args.dry_run:
        raise SystemExit(0 if decision.allowed else 2)

    if not decision.allowed:
        raise SystemExit(2)

    candidate_version = str(decision.context["candidate_version"])
    apply_promotion(
        client=client,
        model_name=args.model_name,
        candidate_version=candidate_version,
        from_alias=args.from_alias,
    )


if __name__ == "__main__":
    main()
