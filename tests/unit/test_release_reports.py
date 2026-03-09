from __future__ import annotations

import json

import pytest

from ml_lifecycle_platform.contracts.release_reports import (
    OperationResult,
    PolicyOutcome,
    PromotionDecisionReport,
    ReleaseManifest,
    ReleaseReportBundle,
    RollbackTargetReport,
    render_model_card,
)
from ml_lifecycle_platform.registry.release_evidence import artifact_root

pytestmark = pytest.mark.unit


def _bundle() -> ReleaseReportBundle:
    policy_outcome = PolicyOutcome.not_evaluated(reason="unit-test")
    result = OperationResult(status="succeeded", code="ok", message="all good")
    bundle = ReleaseReportBundle(
        decision=PromotionDecisionReport(
            generated_at="2026-03-09T00:00:00+00:00",
            operation="promote",
            model_name="demo_model",
            model_version="7",
            source_run_id="run-123",
            policy_outcome=policy_outcome,
            result=result,
        ),
        manifest=ReleaseManifest(
            generated_at="2026-03-09T00:00:00+00:00",
            operation="promote",
            model_name="demo_model",
            model_version="7",
            source_run_id="run-123",
            dataset_fingerprint="fp-123",
            config_hash="cfg-123",
            git_sha="deadbeef",
            current_prod_version="7",
            previous_prod_version="6",
            policy_outcome=policy_outcome,
            result=result,
            metrics={"test_accuracy": 0.91},
        ),
        rollback_target=RollbackTargetReport(
            generated_at="2026-03-09T00:00:00+00:00",
            operation="promote",
            model_name="demo_model",
            model_version="7",
            source_run_id="run-123",
            current_prod_version="7",
            previous_prod_version="6",
            target_version="6",
            target_source_run_id="run-122",
            result=result,
        ),
        model_card="",
    )
    return ReleaseReportBundle(
        decision=bundle.decision,
        manifest=bundle.manifest,
        rollback_target=bundle.rollback_target,
        model_card=render_model_card(bundle),
    )


def test_release_manifest_round_trips_from_json() -> None:
    bundle = _bundle()

    manifest = ReleaseManifest.from_json(json.dumps(bundle.manifest.to_dict()))

    assert manifest.model_name == "demo_model"
    assert manifest.previous_prod_version == "6"
    assert manifest.policy_outcome.reason == "unit-test"
    assert manifest.metrics["test_accuracy"] == pytest.approx(0.91)


def test_release_bundle_writes_expected_artifact_names() -> None:
    files = _bundle().file_contents()

    assert sorted(files) == [
        "model_card.md",
        "promotion_decision.json",
        "release_manifest.json",
        "rollback_target.json",
    ]


def test_model_card_contains_operator_facing_fields() -> None:
    model_card = _bundle().model_card

    assert "# Model Card: demo_model v7" in model_card
    assert "- Current prod: `7`" in model_card
    assert "- Previous prod: `6`" in model_card
    assert "- Dataset fingerprint: `fp-123`" in model_card


def test_artifact_root_is_stable() -> None:
    assert artifact_root(
        operation="promote", model_name="demo_model", model_version="7"
    ) == ("reports/releases/promote/demo_model/v7")
