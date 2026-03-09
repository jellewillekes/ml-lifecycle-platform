from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from ml_lifecycle_platform.common.constants import MODEL_SPEC_SCHEMA_VERSION

REPO_ROOT = Path(__file__).resolve().parents[3]
SUPPORTED_TASK = "binary_classifier"
SUPPORTED_SOURCE_KINDS = {"sklearn_demo", "csv"}
SUPPORTED_TRAINER_KIND = "logistic_regression"
SUPPORTED_PREPROCESSOR_KIND = "standard_scaler"
SUPPORTED_METRICS = {"accuracy", "f1", "roc_auc"}


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
class SplitSpec:
    test_size: float
    random_state: int
    stratify: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_size": self.test_size,
            "random_state": self.random_state,
            "stratify": self.stratify,
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
class ModelSpec:
    schema_version: str
    model_name: str
    task: str
    label_column: str
    source: SklearnDemoSourceSpec | CsvSourceSpec
    split: SplitSpec
    preprocessor: PreprocessorSpec
    trainer: LogisticRegressionTrainerSpec
    evaluation: EvaluationSpec
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
        }

    def data_source_uri(self) -> str:
        if isinstance(self.source, CsvSourceSpec):
            return self.source.data_source_uri(spec_path=self.spec_path)
        return self.source.data_source_uri()


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

    return ModelSpec(
        schema_version=schema_version,
        model_name=_require_str(raw, "model_name", context="model_spec"),
        task=task,
        label_column=_require_str(raw, "label_column", context="model_spec"),
        source=_parse_source(raw.get("source"), context="model_spec.source"),
        split=_parse_split(raw.get("split"), context="model_spec.split"),
        preprocessor=_parse_preprocessor(
            raw.get("preprocessor"), context="model_spec.preprocessor"
        ),
        trainer=_parse_trainer(raw.get("trainer"), context="model_spec.trainer"),
        evaluation=_parse_evaluation(
            raw.get("evaluation"), context="model_spec.evaluation"
        ),
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
