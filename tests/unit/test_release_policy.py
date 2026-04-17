from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from ml_lifecycle_platform.common.constants import (
    ALIAS_CANDIDATE,
    ALIAS_PROD,
    GATE_PASSED,
    TAG_CONFIG_HASH,
    TAG_DATASET_FINGERPRINT,
    TAG_DETERMINISTIC_SEED,
    TAG_ENV_LOCK_HASH,
    TAG_GATE,
    TAG_GIT_SHA,
    TAG_RELEASE_STATUS,
    TAG_REPRO_SCHEMA_VERSION,
    TAG_SOURCE_RUN_ID,
    TAG_TRAINING_RUN_ID,
)
from ml_lifecycle_platform.core.model_specs import (
    MetricThresholdSpec,
    PolicySpec,
    default_policy_spec,
)
from ml_lifecycle_platform.core.policy_engine import (
    evaluate_gate_rule,
    evaluate_metric_thresholds_rule,
    evaluate_noop_promotion_rule,
    evaluate_release_status_rule,
    evaluate_reproducibility_rule,
    evaluate_required_metadata_rule,
)
from ml_lifecycle_platform.core.policy_engine import evaluate_promotion_policy
from ml_lifecycle_platform.registry.promote import main as promote_main

pytestmark = pytest.mark.unit


@dataclass
class _ModelVersion:
    version: str
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class _RunData:
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class _Run:
    data: _RunData


class MlflowClientStub:
    def __init__(self) -> None:
        self._aliases: dict[tuple[str, str], str] = {}
        self._versions: dict[tuple[str, str], _ModelVersion] = {}
        self._runs: dict[str, _Run] = {}
        self.set_registered_model_alias_calls: list[
            tuple[tuple[Any, ...], dict[str, Any]]
        ] = []
        self.set_model_version_tag_calls: list[
            tuple[tuple[Any, ...], dict[str, Any]]
        ] = []

    def put_version(self, model_name: str, version: str, tags: dict[str, str]) -> None:
        self._versions[(model_name, version)] = _ModelVersion(
            version=version, tags=tags
        )

    def put_run(self, run_id: str, *, metrics: dict[str, float] | None = None) -> None:
        self._runs[run_id] = _Run(
            data=_RunData(metrics={} if metrics is None else metrics)
        )

    def set_alias(self, model_name: str, alias: str, version: str) -> None:
        self._aliases[(model_name, alias)] = version

    def get_model_version_by_alias(self, model_name: str, alias: str) -> _ModelVersion:
        version = self._aliases[(model_name, alias)]
        return self._versions[(model_name, version)]

    def get_model_version(self, model_name: str, version: str) -> _ModelVersion:
        return self._versions[(model_name, version)]

    def get_run(self, run_id: str) -> _Run:
        return self._runs[run_id]

    def set_registered_model_alias(self, *args: Any, **kwargs: Any) -> None:
        self.set_registered_model_alias_calls.append((args, kwargs))

    def set_model_version_tag(self, *args: Any, **kwargs: Any) -> None:
        self.set_model_version_tag_calls.append((args, kwargs))


def _valid_candidate_tags(*, include_repro: bool = False) -> dict[str, str]:
    tags = {
        TAG_DATASET_FINGERPRINT: "abc",
        TAG_GIT_SHA: "deadbeef",
        TAG_CONFIG_HASH: "cfg123",
        TAG_TRAINING_RUN_ID: "trainrun123",
        TAG_GATE: GATE_PASSED,
        TAG_RELEASE_STATUS: ALIAS_CANDIDATE,
        TAG_SOURCE_RUN_ID: "run-123",
    }
    if include_repro:
        tags[TAG_ENV_LOCK_HASH] = "lock-123"
        tags[TAG_DETERMINISTIC_SEED] = "42"
        tags[TAG_REPRO_SCHEMA_VERSION] = "repro_contract/v1"
    return tags


def _policy_with(
    *,
    required_metadata_tags: tuple[str, ...] | None = None,
    required_release_status: str | None = None,
    block_noop_promotion: bool | None = None,
    require_reproducibility_evidence: bool | None = None,
    minimum_metric_thresholds: tuple[MetricThresholdSpec, ...] | None = None,
) -> PolicySpec:
    base = default_policy_spec()
    return PolicySpec(
        required_metadata_tags=(
            base.required_metadata_tags
            if required_metadata_tags is None
            else required_metadata_tags
        ),
        required_release_status=(
            base.required_release_status
            if required_release_status is None
            else required_release_status
        ),
        block_noop_promotion=(
            base.block_noop_promotion
            if block_noop_promotion is None
            else block_noop_promotion
        ),
        require_reproducibility_evidence=(
            base.require_reproducibility_evidence
            if require_reproducibility_evidence is None
            else require_reproducibility_evidence
        ),
        minimum_metric_thresholds=(
            base.minimum_metric_thresholds
            if minimum_metric_thresholds is None
            else minimum_metric_thresholds
        ),
    )


def test_required_metadata_rule_reports_missing_tags() -> None:
    violation = evaluate_required_metadata_rule(
        {TAG_GIT_SHA: "deadbeef"},
        _policy_with(required_metadata_tags=(TAG_GIT_SHA, TAG_CONFIG_HASH)),
    )

    assert violation is not None
    assert violation.code == "MISSING_REQUIRED_TAGS"
    assert violation.details["missing"] == [TAG_CONFIG_HASH]


def test_gate_rule_blocks_non_passed_candidates() -> None:
    violation = evaluate_gate_rule({TAG_GATE: "failed"})

    assert violation is not None
    assert violation.code == "GATE_NOT_PASSED"


def test_release_status_rule_uses_policy_override() -> None:
    violation = evaluate_release_status_rule(
        {TAG_RELEASE_STATUS: ALIAS_CANDIDATE},
        _policy_with(required_release_status="staging"),
    )

    assert violation is not None
    assert violation.code == "INVALID_RELEASE_STATUS"
    assert violation.details["expected"] == "staging"


def test_noop_rule_can_be_disabled() -> None:
    assert (
        evaluate_noop_promotion_rule(
            candidate_version="3",
            current_prod_version="3",
            policy=_policy_with(block_noop_promotion=False),
        )
        is None
    )


def test_reproducibility_rule_blocks_when_enabled_and_evidence_missing() -> None:
    violations = evaluate_reproducibility_rule(
        candidate_tags=_valid_candidate_tags(include_repro=False),
        policy=_policy_with(require_reproducibility_evidence=True),
        source_run_lookup_ok=True,
    )

    assert len(violations) == 1
    assert violations[0].code == "MISSING_REPRODUCIBILITY_EVIDENCE"


def test_metric_threshold_rule_blocks_below_threshold() -> None:
    violations = evaluate_metric_thresholds_rule(
        source_run=_Run(data=_RunData(metrics={"test_roc_auc": 0.91})),
        source_run_id="run-123",
        policy=_policy_with(
            minimum_metric_thresholds=(MetricThresholdSpec("roc_auc", 0.95),)
        ),
    )

    assert len(violations) == 1
    assert violations[0].code == "METRIC_BELOW_THRESHOLD"


def test_policy_blocks_when_candidate_alias_missing() -> None:
    client = MlflowClientStub()

    decision = evaluate_promotion_policy(
        client, model_name="m", from_alias=ALIAS_CANDIDATE, to_alias=ALIAS_PROD
    )

    assert decision.allowed is False
    assert any(v.code == "MISSING_ALIAS" for v in decision.errors)


@pytest.mark.parametrize(
    "missing_key",
    [TAG_DATASET_FINGERPRINT, TAG_GIT_SHA, TAG_CONFIG_HASH, TAG_TRAINING_RUN_ID],
)
def test_policy_blocks_when_required_tag_missing(missing_key: str) -> None:
    client = MlflowClientStub()
    tags = _valid_candidate_tags()
    tags[missing_key] = ""
    client.put_version("m", "1", tags)
    client.set_alias("m", ALIAS_CANDIDATE, "1")
    client.put_run("run-123")

    decision = evaluate_promotion_policy(client, model_name="m")

    assert decision.allowed is False
    assert any(v.code == "MISSING_REQUIRED_TAGS" for v in decision.errors)


def test_policy_blocks_when_gate_not_passed() -> None:
    client = MlflowClientStub()
    tags = _valid_candidate_tags()
    tags[TAG_GATE] = "failed"
    client.put_version("m", "1", tags)
    client.set_alias("m", ALIAS_CANDIDATE, "1")
    client.put_run("run-123")

    decision = evaluate_promotion_policy(client, model_name="m")

    assert decision.allowed is False
    assert any(v.code == "GATE_NOT_PASSED" for v in decision.errors)


def test_policy_blocks_when_release_status_not_allowed_by_policy() -> None:
    client = MlflowClientStub()
    tags = _valid_candidate_tags()
    client.put_version("m", "1", tags)
    client.set_alias("m", ALIAS_CANDIDATE, "1")
    client.put_run("run-123")

    decision = evaluate_promotion_policy(
        client,
        model_name="m",
        policy=_policy_with(required_release_status="shadow"),
    )

    assert decision.allowed is False
    assert any(v.code == "INVALID_RELEASE_STATUS" for v in decision.errors)


def test_policy_blocks_noop_promotion_when_enabled() -> None:
    client = MlflowClientStub()
    tags = _valid_candidate_tags()
    client.put_version("m", "1", tags)
    client.set_alias("m", ALIAS_CANDIDATE, "1")
    client.set_alias("m", ALIAS_PROD, "1")
    client.put_run("run-123")

    decision = evaluate_promotion_policy(client, model_name="m")

    assert decision.allowed is False
    assert any(v.code == "NOOP_PROMOTION" for v in decision.errors)


def test_policy_blocks_when_reproducibility_evidence_is_required() -> None:
    client = MlflowClientStub()
    tags = _valid_candidate_tags(include_repro=False)
    client.put_version("m", "1", tags)
    client.set_alias("m", ALIAS_CANDIDATE, "1")
    client.put_run("run-123")

    decision = evaluate_promotion_policy(
        client,
        model_name="m",
        policy=_policy_with(require_reproducibility_evidence=True),
    )

    assert decision.allowed is False
    assert any(v.code == "MISSING_REPRODUCIBILITY_EVIDENCE" for v in decision.errors)


def test_policy_blocks_when_metric_threshold_override_is_not_met() -> None:
    client = MlflowClientStub()
    tags = _valid_candidate_tags(include_repro=True)
    client.put_version("m", "1", tags)
    client.set_alias("m", ALIAS_CANDIDATE, "1")
    client.put_run("run-123", metrics={"test_roc_auc": 0.91})

    decision = evaluate_promotion_policy(
        client,
        model_name="m",
        policy=_policy_with(
            minimum_metric_thresholds=(MetricThresholdSpec("roc_auc", 0.95),)
        ),
    )

    assert decision.allowed is False
    assert any(v.code == "METRIC_BELOW_THRESHOLD" for v in decision.errors)


def test_policy_allows_when_metric_threshold_override_is_met() -> None:
    client = MlflowClientStub()
    tags = _valid_candidate_tags(include_repro=True)
    client.put_version("m", "1", tags)
    client.set_alias("m", ALIAS_CANDIDATE, "1")
    client.put_run("run-123", metrics={"test_roc_auc": 0.97})

    decision = evaluate_promotion_policy(
        client,
        model_name="m",
        policy=_policy_with(
            require_reproducibility_evidence=True,
            minimum_metric_thresholds=(MetricThresholdSpec("roc_auc", 0.95),),
        ),
    )

    assert decision.allowed is True
    assert decision.errors == ()


def test_dry_run_mode_has_zero_mutations(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MlflowClientStub()
    tags = _valid_candidate_tags()
    client.put_version("m", "1", tags)
    client.set_alias("m", ALIAS_CANDIDATE, "1")
    client.put_run("run-123")

    import ml_lifecycle_platform.registry.promote as promote_mod

    monkeypatch.setattr(promote_mod, "mlflow_client", lambda: client)

    with pytest.raises(SystemExit) as e:
        promote_main(["--model-name", "m", "--dry-run", "--format", "json"])
    assert e.value.code == 0

    assert client.set_registered_model_alias_calls == []
    assert client.set_model_version_tag_calls == []
