"""Parse model-spec YAML payloads into strongly-typed ``ModelSpec``
dataclasses, enforcing the model-spec schema version."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from ml_lifecycle_platform.common.constants import MODEL_SPEC_SCHEMA_VERSION
from ml_lifecycle_platform.core.model_spec_types import (
    CsvSourceSpec,
    EvaluationGateSpec,
    EvaluationSpec,
    FeatureContractSpec,
    FeatureFieldSpec,
    LogisticRegressionTrainerSpec,
    MetricThresholdSpec,
    ModelSpec,
    PolicySpec,
    PreprocessorSpec,
    SklearnDemoSourceSpec,
    SplitSpec,
    SUPPORTED_FEATURE_TYPES,
    SUPPORTED_METRICS,
    SUPPORTED_PREPROCESSOR_KIND,
    SUPPORTED_SOURCE_KINDS,
    SUPPORTED_TASK,
    SUPPORTED_TRAINER_KIND,
    default_feature_contract_spec,
    default_policy_spec,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _require_mapping(payload: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{context} must be a YAML mapping.")
    return dict(payload)


def _reject_extra_keys(
    payload: Mapping[str, Any], *, allowed: set[str], context: str
) -> None:
    extras = sorted(set(payload) - allowed)
    if extras:
        raise ValueError(f"{context} contains unsupported fields: {', '.join(extras)}")


def _require_str(payload: Mapping[str, Any], key: str, *, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}.{key} must be a non-empty string.")
    return value.strip()


def _require_float(payload: Mapping[str, Any], key: str, *, context: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{context}.{key} must be numeric.")
    return float(value)


def _require_int(payload: Mapping[str, Any], key: str, *, context: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{context}.{key} must be an integer.")
    return value


def _require_bool(payload: Mapping[str, Any], key: str, *, context: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{context}.{key} must be a boolean.")
    return value


def _parse_source(
    payload: Any, *, context: str
) -> SklearnDemoSourceSpec | CsvSourceSpec:
    raw = _require_mapping(payload, context=context)
    kind = _require_str(raw, "kind", context=context)
    if kind not in SUPPORTED_SOURCE_KINDS:
        raise ValueError(
            f"{context}.kind must be one of {sorted(SUPPORTED_SOURCE_KINDS)}."
        )

    if kind == "sklearn_demo":
        _reject_extra_keys(raw, allowed={"kind", "dataset_name"}, context=context)
        dataset_name = _require_str(raw, "dataset_name", context=context)
        if dataset_name != "breast_cancer":
            raise ValueError(f"{context}.dataset_name must be 'breast_cancer'.")
        return SklearnDemoSourceSpec(kind=kind, dataset_name=dataset_name)

    _reject_extra_keys(raw, allowed={"kind", "path"}, context=context)
    return CsvSourceSpec(kind=kind, path=_require_str(raw, "path", context=context))


def _parse_split(payload: Any, *, context: str) -> SplitSpec:
    raw = _require_mapping(payload, context=context)
    _reject_extra_keys(
        raw,
        allowed={"test_size", "random_state", "stratify"},
        context=context,
    )
    test_size = _require_float(raw, "test_size", context=context)
    if not 0.0 < test_size < 1.0:
        raise ValueError(f"{context}.test_size must be between 0 and 1.")
    return SplitSpec(
        test_size=test_size,
        random_state=_require_int(raw, "random_state", context=context),
        stratify=_require_bool(raw, "stratify", context=context),
    )


def _parse_preprocessor(payload: Any, *, context: str) -> PreprocessorSpec:
    raw = _require_mapping(payload, context=context)
    _reject_extra_keys(raw, allowed={"kind"}, context=context)
    kind = _require_str(raw, "kind", context=context)
    if kind != SUPPORTED_PREPROCESSOR_KIND:
        raise ValueError(f"{context}.kind must be {SUPPORTED_PREPROCESSOR_KIND!r}.")
    return PreprocessorSpec(kind=kind)


def _parse_trainer(payload: Any, *, context: str) -> LogisticRegressionTrainerSpec:
    raw = _require_mapping(payload, context=context)
    _reject_extra_keys(
        raw,
        allowed={"kind", "max_iter", "solver", "class_weight", "random_state"},
        context=context,
    )
    kind = _require_str(raw, "kind", context=context)
    if kind != SUPPORTED_TRAINER_KIND:
        raise ValueError(f"{context}.kind must be {SUPPORTED_TRAINER_KIND!r}.")
    return LogisticRegressionTrainerSpec(
        kind=kind,
        max_iter=_require_int(raw, "max_iter", context=context),
        solver=_require_str(raw, "solver", context=context),
        class_weight=_require_str(raw, "class_weight", context=context),
        random_state=_require_int(raw, "random_state", context=context),
    )


def _parse_evaluation(payload: Any, *, context: str) -> EvaluationSpec:
    raw = _require_mapping(payload, context=context)
    _reject_extra_keys(raw, allowed={"metrics", "gate"}, context=context)
    metrics = raw.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise ValueError(f"{context}.metrics must be a non-empty list.")
    parsed_metrics: list[str] = []
    for metric in metrics:
        if not isinstance(metric, str) or metric not in SUPPORTED_METRICS:
            raise ValueError(
                f"{context}.metrics entries must be one of {sorted(SUPPORTED_METRICS)}."
            )
        parsed_metrics.append(metric)

    gate_raw = _require_mapping(raw.get("gate"), context=f"{context}.gate")
    _reject_extra_keys(
        gate_raw, allowed={"metric", "threshold"}, context=f"{context}.gate"
    )
    gate_metric = _require_str(gate_raw, "metric", context=f"{context}.gate")
    if gate_metric not in parsed_metrics:
        raise ValueError(f"{context}.gate.metric must be listed in {context}.metrics.")
    gate = EvaluationGateSpec(
        metric=gate_metric,
        threshold=_require_float(gate_raw, "threshold", context=f"{context}.gate"),
    )
    return EvaluationSpec(metrics=tuple(parsed_metrics), gate=gate)


def _parse_metric_threshold(payload: Any, *, context: str) -> MetricThresholdSpec:
    raw = _require_mapping(payload, context=context)
    _reject_extra_keys(raw, allowed={"metric", "threshold"}, context=context)
    metric = _require_str(raw, "metric", context=context)
    if metric not in SUPPORTED_METRICS:
        raise ValueError(
            f"{context}.metric must be one of {sorted(SUPPORTED_METRICS)}."
        )
    threshold = _require_float(raw, "threshold", context=context)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"{context}.threshold must be between 0 and 1.")
    return MetricThresholdSpec(metric=metric, threshold=threshold)


def _parse_feature_field(payload: Any, *, context: str) -> FeatureFieldSpec:
    raw = _require_mapping(payload, context=context)
    _reject_extra_keys(raw, allowed={"name", "dtype", "required"}, context=context)
    name = _require_str(raw, "name", context=context)
    dtype = _require_str(raw, "dtype", context=context)
    if dtype not in SUPPORTED_FEATURE_TYPES:
        raise ValueError(
            f"{context}.dtype must be one of {sorted(SUPPORTED_FEATURE_TYPES)}."
        )
    required = raw.get("required", True)
    if not isinstance(required, bool):
        raise ValueError(f"{context}.required must be a boolean.")
    return FeatureFieldSpec(name=name, dtype=dtype, required=required)


def _parse_feature_contract(payload: Any, *, context: str) -> FeatureContractSpec:
    if payload is None:
        return default_feature_contract_spec()

    raw = _require_mapping(payload, context=context)
    _reject_extra_keys(
        raw,
        allowed={"version", "allow_unknown_fields", "features"},
        context=context,
    )
    features = raw.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError(f"{context}.features must be a non-empty list.")

    parsed_features = tuple(
        _parse_feature_field(item, context=f"{context}.features[{idx}]")
        for idx, item in enumerate(features)
    )
    if len({feature.name for feature in parsed_features}) != len(parsed_features):
        raise ValueError(f"{context}.features cannot repeat feature names.")

    return FeatureContractSpec(
        version=_require_str(raw, "version", context=context),
        allow_unknown_fields=_require_bool(
            raw, "allow_unknown_fields", context=context
        ),
        features=parsed_features,
    )


def _parse_policy(payload: Any, *, context: str) -> PolicySpec:
    if payload is None:
        return default_policy_spec()

    raw = _require_mapping(payload, context=context)
    _reject_extra_keys(
        raw,
        allowed={
            "required_metadata_tags",
            "required_release_status",
            "block_noop_promotion",
            "require_reproducibility_evidence",
            "minimum_metric_thresholds",
        },
        context=context,
    )

    required_metadata_tags = raw.get("required_metadata_tags")
    if not isinstance(required_metadata_tags, list) or not required_metadata_tags:
        raise ValueError(f"{context}.required_metadata_tags must be a non-empty list.")

    parsed_required_metadata_tags: list[str] = []
    for tag_name in required_metadata_tags:
        if not isinstance(tag_name, str) or not tag_name.strip():
            raise ValueError(
                f"{context}.required_metadata_tags entries must be non-empty strings."
            )
        parsed_required_metadata_tags.append(tag_name.strip())

    minimum_metric_thresholds = raw.get("minimum_metric_thresholds")
    if not isinstance(minimum_metric_thresholds, list):
        raise ValueError(f"{context}.minimum_metric_thresholds must be a list.")

    parsed_thresholds = tuple(
        _parse_metric_threshold(
            item, context=f"{context}.minimum_metric_thresholds[{idx}]"
        )
        for idx, item in enumerate(minimum_metric_thresholds)
    )
    if len({threshold.metric for threshold in parsed_thresholds}) != len(
        parsed_thresholds
    ):
        raise ValueError(f"{context}.minimum_metric_thresholds cannot repeat metrics.")

    return PolicySpec(
        required_metadata_tags=tuple(parsed_required_metadata_tags),
        required_release_status=_require_str(
            raw, "required_release_status", context=context
        ),
        block_noop_promotion=_require_bool(
            raw, "block_noop_promotion", context=context
        ),
        require_reproducibility_evidence=_require_bool(
            raw, "require_reproducibility_evidence", context=context
        ),
        minimum_metric_thresholds=parsed_thresholds,
    )


def model_spec_from_dict(
    payload: Mapping[str, Any], *, spec_path: str | Path
) -> ModelSpec:
    raw = _require_mapping(payload, context="model_spec")
    _reject_extra_keys(
        raw,
        allowed={
            "schema_version",
            "model_name",
            "task",
            "label_column",
            "source",
            "split",
            "preprocessor",
            "trainer",
            "evaluation",
            "feature_contract",
            "policy",
        },
        context="model_spec",
    )
    schema_version = _require_str(raw, "schema_version", context="model_spec")
    if schema_version != MODEL_SPEC_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported model spec schema_version={schema_version!r} "
            f"(expected {MODEL_SPEC_SCHEMA_VERSION!r})"
        )
    task = _require_str(raw, "task", context="model_spec")
    if task != SUPPORTED_TASK:
        raise ValueError(f"model_spec.task must be {SUPPORTED_TASK!r}.")

    label_column = _require_str(raw, "label_column", context="model_spec")
    feature_contract = _parse_feature_contract(
        raw.get("feature_contract"), context="model_spec.feature_contract"
    )
    if any(feature.name == label_column for feature in feature_contract.features):
        raise ValueError(
            "model_spec.feature_contract.features must exclude label_column."
        )

    return ModelSpec(
        schema_version=schema_version,
        model_name=_require_str(raw, "model_name", context="model_spec"),
        task=task,
        label_column=label_column,
        source=_parse_source(raw.get("source"), context="model_spec.source"),
        split=_parse_split(raw.get("split"), context="model_spec.split"),
        preprocessor=_parse_preprocessor(
            raw.get("preprocessor"), context="model_spec.preprocessor"
        ),
        trainer=_parse_trainer(raw.get("trainer"), context="model_spec.trainer"),
        evaluation=_parse_evaluation(
            raw.get("evaluation"), context="model_spec.evaluation"
        ),
        feature_contract=feature_contract,
        policy=_parse_policy(raw.get("policy"), context="model_spec.policy"),
        spec_path=resolve_model_spec_path(spec_path),
    )


def resolve_model_spec_path(path: str | Path) -> Path:
    spec_path = Path(path)
    if spec_path.is_absolute():
        return spec_path.resolve()
    return (REPO_ROOT / spec_path).resolve()


def load_model_spec(path: str | Path) -> ModelSpec:
    spec_path = resolve_model_spec_path(path)
    payload = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    return model_spec_from_dict(payload, spec_path=spec_path)
