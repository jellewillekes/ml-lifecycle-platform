"""Typed dataclass schema for a model spec (task, source, trainer, features,
metrics, policy) — the parsed representation of a `configs/models/*.yaml`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ml_lifecycle_platform.common.constants import (
    ALIAS_CANDIDATE,
    TAG_CONFIG_HASH,
    TAG_DATASET_FINGERPRINT,
    TAG_GIT_SHA,
    TAG_TRAINING_RUN_ID,
)

SUPPORTED_TASK = "binary_classifier"
SUPPORTED_SOURCE_KINDS = {"sklearn_demo", "csv", "binance"}
SUPPORTED_SPLIT_METHODS = {"random", "chronological"}
SUPPORTED_TRAINER_KINDS = {"logistic_regression", "lightgbm"}
SUPPORTED_PREPROCESSOR_KIND = "standard_scaler"
SUPPORTED_METRICS = {"accuracy", "f1", "roc_auc"}
SUPPORTED_FEATURE_TYPES = {"float", "int", "bool", "string"}
DEFAULT_POLICY_REQUIRED_METADATA_TAGS = (
    TAG_DATASET_FINGERPRINT,
    TAG_GIT_SHA,
    TAG_CONFIG_HASH,
    TAG_TRAINING_RUN_ID,
)


@dataclass(frozen=True)
class SklearnDemoSourceSpec:
    kind: str
    dataset_name: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "dataset_name": self.dataset_name}

    def data_source_uri(self) -> str:
        return f"sklearn://{self.dataset_name}"


@dataclass(frozen=True)
class CsvSourceSpec:
    kind: str
    path: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "path": self.path}

    def resolved_path(self, *, spec_path: Path) -> Path:
        csv_path = Path(self.path)
        if csv_path.is_absolute():
            return csv_path
        return (spec_path.parent / csv_path).resolve()

    def data_source_uri(self, *, spec_path: Path) -> str:
        return self.resolved_path(spec_path=spec_path).as_uri()


@dataclass(frozen=True)
class BinanceSourceSpec:
    kind: str
    symbol: str
    interval: str
    limit: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "symbol": self.symbol,
            "interval": self.interval,
            "limit": self.limit,
        }

    def data_source_uri(self) -> str:
        return f"binance://{self.symbol}/{self.interval}?limit={self.limit}"


@dataclass(frozen=True)
class SplitSpec:
    test_size: float
    random_state: int
    stratify: bool
    method: str = "random"

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_size": self.test_size,
            "random_state": self.random_state,
            "stratify": self.stratify,
            "method": self.method,
        }


@dataclass(frozen=True)
class PreprocessorSpec:
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind}


@dataclass(frozen=True)
class LogisticRegressionTrainerSpec:
    kind: str
    max_iter: int
    solver: str
    class_weight: str
    random_state: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "max_iter": self.max_iter,
            "solver": self.solver,
            "class_weight": self.class_weight,
            "random_state": self.random_state,
        }


@dataclass(frozen=True)
class LightGBMTrainerSpec:
    kind: str
    n_estimators: int
    learning_rate: float
    num_leaves: int
    max_depth: int
    min_child_samples: int
    class_weight: str
    random_state: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "min_child_samples": self.min_child_samples,
            "class_weight": self.class_weight,
            "random_state": self.random_state,
        }


TrainerSpec = LogisticRegressionTrainerSpec | LightGBMTrainerSpec


@dataclass(frozen=True)
class EvaluationGateSpec:
    metric: str
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        return {"metric": self.metric, "threshold": self.threshold}


@dataclass(frozen=True)
class EvaluationSpec:
    metrics: tuple[str, ...]
    gate: EvaluationGateSpec

    def to_dict(self) -> dict[str, Any]:
        return {"metrics": list(self.metrics), "gate": self.gate.to_dict()}


@dataclass(frozen=True)
class MetricThresholdSpec:
    metric: str
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        return {"metric": self.metric, "threshold": self.threshold}


@dataclass(frozen=True)
class FeatureRangeSpec:
    name: str
    minimum: float | None
    maximum: float | None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "min": self.minimum, "max": self.maximum}


@dataclass(frozen=True)
class ValidationSpec:
    min_rows: int
    feature_ranges: tuple[FeatureRangeSpec, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_rows": self.min_rows,
            "feature_ranges": [feature.to_dict() for feature in self.feature_ranges],
        }


def default_validation_spec() -> ValidationSpec:
    return ValidationSpec(min_rows=1, feature_ranges=())


@dataclass(frozen=True)
class FeatureFieldSpec:
    name: str
    dtype: str
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "required": self.required,
        }


@dataclass(frozen=True)
class FeatureContractSpec:
    version: str
    allow_unknown_fields: bool
    features: tuple[FeatureFieldSpec, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "allow_unknown_fields": self.allow_unknown_fields,
            "features": [feature.to_dict() for feature in self.features],
        }


def default_feature_contract_spec() -> FeatureContractSpec:
    return FeatureContractSpec(
        version="feature_contract/default",
        allow_unknown_fields=True,
        features=(),
    )


@dataclass(frozen=True)
class PolicySpec:
    required_metadata_tags: tuple[str, ...]
    required_release_status: str
    block_noop_promotion: bool
    require_reproducibility_evidence: bool
    minimum_metric_thresholds: tuple[MetricThresholdSpec, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_metadata_tags": list(self.required_metadata_tags),
            "required_release_status": self.required_release_status,
            "block_noop_promotion": self.block_noop_promotion,
            "require_reproducibility_evidence": self.require_reproducibility_evidence,
            "minimum_metric_thresholds": [
                threshold.to_dict() for threshold in self.minimum_metric_thresholds
            ],
        }


def default_policy_spec() -> PolicySpec:
    return PolicySpec(
        required_metadata_tags=DEFAULT_POLICY_REQUIRED_METADATA_TAGS,
        required_release_status=ALIAS_CANDIDATE,
        block_noop_promotion=True,
        require_reproducibility_evidence=False,
        minimum_metric_thresholds=(),
    )


@dataclass(frozen=True)
class ModelSpec:
    schema_version: str
    model_name: str
    task: str
    label_column: str
    source: SklearnDemoSourceSpec | CsvSourceSpec | BinanceSourceSpec
    split: SplitSpec
    preprocessor: PreprocessorSpec
    trainer: TrainerSpec
    evaluation: EvaluationSpec
    feature_contract: FeatureContractSpec
    validation: ValidationSpec
    policy: PolicySpec
    spec_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "model_name": self.model_name,
            "task": self.task,
            "label_column": self.label_column,
            "source": self.source.to_dict(),
            "split": self.split.to_dict(),
            "preprocessor": self.preprocessor.to_dict(),
            "trainer": self.trainer.to_dict(),
            "evaluation": self.evaluation.to_dict(),
            "feature_contract": self.feature_contract.to_dict(),
            "validation": self.validation.to_dict(),
            "policy": self.policy.to_dict(),
        }

    def data_source_uri(self) -> str:
        if isinstance(self.source, CsvSourceSpec):
            return self.source.data_source_uri(spec_path=self.spec_path)
        return self.source.data_source_uri()


SourceSpec = SklearnDemoSourceSpec | CsvSourceSpec | BinanceSourceSpec
