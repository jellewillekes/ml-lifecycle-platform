from __future__ import annotations

from pathlib import Path

import pytest

from ml_lifecycle_platform.common.constants import (
    MODEL_SPEC_SCHEMA_VERSION,
    TAG_CONFIG_HASH,
)
from ml_lifecycle_platform.core.model_spec_types import (
    LightGBMTrainerSpec,
    default_policy_spec,
)
from ml_lifecycle_platform.core.model_specs import load_model_spec, model_spec_from_dict

pytestmark = pytest.mark.unit


def test_load_demo_model_spec() -> None:
    spec = load_model_spec("configs/models/breast_cancer_demo.yaml")

    assert spec.model_name == "breast_cancer_clf"
    assert spec.source.kind == "sklearn_demo"
    assert spec.label_column == "target"
    assert spec.evaluation.gate.metric == "roc_auc"
    assert spec.feature_contract.version == "breast_cancer_clf.input/v1"
    assert spec.policy.required_release_status == "candidate"


def test_load_csv_model_spec_resolves_relative_data_path() -> None:
    spec = load_model_spec("configs/models/local_csv_binary_classifier.yaml")

    assert spec.source.kind == "csv"
    assert spec.data_source_uri().startswith("file://")
    assert spec.feature_contract.version == "local_csv_binary_clf.input/v1"
    assert spec.data_source_uri().endswith(
        "/examples/csv/local_csv_binary_classifier.csv"
    )


def test_load_binance_model_spec() -> None:
    spec = load_model_spec("configs/models/binance_btc_1m.yaml")

    assert spec.model_name == "binance_btc_1m"
    assert spec.source.kind == "binance"
    assert spec.data_source_uri() == "binance://BTCUSDT/1m?limit=1000"
    assert spec.split.method == "chronological"
    assert spec.split.stratify is False
    feature_names = {feature.name for feature in spec.feature_contract.features}
    assert "ret_1" in feature_names and "rsi_14" in feature_names


def test_binance_spec_uses_lightgbm_trainer() -> None:
    spec = load_model_spec("configs/models/binance_btc_1m.yaml")

    assert isinstance(spec.trainer, LightGBMTrainerSpec)
    assert spec.trainer.kind == "lightgbm"
    assert spec.trainer.n_estimators == 200
    assert spec.trainer.num_leaves == 15
    assert spec.trainer.class_weight == "balanced"


def test_lightgbm_trainer_rejects_unsupported_fields() -> None:
    payload = {
        "schema_version": "model_spec/v1",
        "model_name": "bad_lgbm",
        "task": "binary_classifier",
        "label_column": "target",
        "source": {"kind": "sklearn_demo", "dataset_name": "breast_cancer"},
        "split": {"test_size": 0.2, "random_state": 42, "stratify": True},
        "preprocessor": {"kind": "standard_scaler"},
        "trainer": {
            "kind": "lightgbm",
            "n_estimators": 100,
            "learning_rate": 0.1,
            "num_leaves": 31,
            "max_depth": -1,
            "min_child_samples": 20,
            "class_weight": "balanced",
            "random_state": 42,
            "max_iter": 2000,
        },
        "evaluation": {
            "metrics": ["accuracy", "f1", "roc_auc"],
            "gate": {"metric": "roc_auc", "threshold": 0.5},
        },
    }

    with pytest.raises(ValueError, match="unsupported fields"):
        model_spec_from_dict(
            payload,
            spec_path=Path("configs/models/binance_btc_1m.yaml"),
        )


def test_trainer_rejects_unknown_kind() -> None:
    payload = {
        "schema_version": "model_spec/v1",
        "model_name": "bad_kind",
        "task": "binary_classifier",
        "label_column": "target",
        "source": {"kind": "sklearn_demo", "dataset_name": "breast_cancer"},
        "split": {"test_size": 0.2, "random_state": 42, "stratify": True},
        "preprocessor": {"kind": "standard_scaler"},
        "trainer": {"kind": "xgboost", "random_state": 42},
        "evaluation": {
            "metrics": ["accuracy", "f1", "roc_auc"],
            "gate": {"metric": "roc_auc", "threshold": 0.5},
        },
    }

    with pytest.raises(ValueError, match="kind must be one of"):
        model_spec_from_dict(
            payload,
            spec_path=Path("configs/models/breast_cancer_demo.yaml"),
        )


def test_chronological_split_rejects_stratify() -> None:
    payload = {
        "schema_version": "model_spec/v1",
        "model_name": "bad_split",
        "task": "binary_classifier",
        "label_column": "target",
        "source": {"kind": "sklearn_demo", "dataset_name": "breast_cancer"},
        "split": {
            "method": "chronological",
            "test_size": 0.2,
            "random_state": 42,
            "stratify": True,
        },
        "preprocessor": {"kind": "standard_scaler"},
        "trainer": {
            "kind": "logistic_regression",
            "max_iter": 2000,
            "solver": "lbfgs",
            "class_weight": "balanced",
            "random_state": 42,
        },
        "evaluation": {
            "metrics": ["accuracy", "f1", "roc_auc"],
            "gate": {"metric": "roc_auc", "threshold": 0.5},
        },
    }

    with pytest.raises(ValueError, match="stratify must be false"):
        model_spec_from_dict(
            payload,
            spec_path=Path("configs/models/breast_cancer_demo.yaml"),
        )


def test_all_committed_model_specs_load() -> None:
    spec_paths = sorted(Path("configs/models").glob("*.yaml"))

    assert spec_paths

    for spec_path in spec_paths:
        spec = load_model_spec(spec_path)
        assert spec.model_name
        assert spec.schema_version == MODEL_SPEC_SCHEMA_VERSION


def test_model_spec_rejects_unsupported_fields(tmp_path: Path) -> None:
    spec_path = tmp_path / "invalid.yaml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version: model_spec/v1",
                "model_name: bad",
                "task: binary_classifier",
                "label_column: target",
                "extra_field: nope",
                "source:",
                "  kind: sklearn_demo",
                "  dataset_name: breast_cancer",
                "split:",
                "  test_size: 0.2",
                "  random_state: 42",
                "  stratify: true",
                "preprocessor:",
                "  kind: standard_scaler",
                "trainer:",
                "  kind: logistic_regression",
                "  max_iter: 2000",
                "  solver: lbfgs",
                "  class_weight: balanced",
                "  random_state: 42",
                "evaluation:",
                "  metrics: [accuracy, f1, roc_auc]",
                "  gate:",
                "    metric: roc_auc",
                "    threshold: 0.95",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported fields"):
        load_model_spec(spec_path)


def test_model_spec_requires_gate_metric_to_be_declared() -> None:
    payload = {
        "schema_version": "model_spec/v1",
        "model_name": "bad",
        "task": "binary_classifier",
        "label_column": "target",
        "source": {"kind": "sklearn_demo", "dataset_name": "breast_cancer"},
        "split": {"test_size": 0.2, "random_state": 42, "stratify": True},
        "preprocessor": {"kind": "standard_scaler"},
        "trainer": {
            "kind": "logistic_regression",
            "max_iter": 2000,
            "solver": "lbfgs",
            "class_weight": "balanced",
            "random_state": 42,
        },
        "evaluation": {
            "metrics": ["accuracy", "f1"],
            "gate": {"metric": "roc_auc", "threshold": 0.95},
        },
    }

    with pytest.raises(ValueError, match="gate.metric"):
        model_spec_from_dict(
            payload,
            spec_path=Path("configs/models/breast_cancer_demo.yaml"),
        )


def test_model_spec_uses_default_policy_when_section_is_missing() -> None:
    payload = {
        "schema_version": "model_spec/v1",
        "model_name": "no_policy_model",
        "task": "binary_classifier",
        "label_column": "target",
        "source": {"kind": "sklearn_demo", "dataset_name": "breast_cancer"},
        "split": {"test_size": 0.2, "random_state": 42, "stratify": True},
        "preprocessor": {"kind": "standard_scaler"},
        "trainer": {
            "kind": "logistic_regression",
            "max_iter": 2000,
            "solver": "lbfgs",
            "class_weight": "balanced",
            "random_state": 42,
        },
        "evaluation": {
            "metrics": ["accuracy", "f1", "roc_auc"],
            "gate": {"metric": "roc_auc", "threshold": 0.95},
        },
    }

    spec = model_spec_from_dict(
        payload,
        spec_path=Path("configs/models/breast_cancer_demo.yaml"),
    )

    assert spec.policy == default_policy_spec()


def test_model_spec_loads_policy_overrides() -> None:
    payload = {
        "schema_version": "model_spec/v1",
        "model_name": "policy_override_model",
        "task": "binary_classifier",
        "label_column": "target",
        "source": {"kind": "sklearn_demo", "dataset_name": "breast_cancer"},
        "split": {"test_size": 0.2, "random_state": 42, "stratify": True},
        "preprocessor": {"kind": "standard_scaler"},
        "trainer": {
            "kind": "logistic_regression",
            "max_iter": 2000,
            "solver": "lbfgs",
            "class_weight": "balanced",
            "random_state": 42,
        },
        "evaluation": {
            "metrics": ["accuracy", "f1", "roc_auc"],
            "gate": {"metric": "roc_auc", "threshold": 0.95},
        },
        "policy": {
            "required_metadata_tags": [TAG_CONFIG_HASH],
            "required_release_status": "shadow",
            "block_noop_promotion": False,
            "require_reproducibility_evidence": True,
            "minimum_metric_thresholds": [{"metric": "accuracy", "threshold": 0.9}],
        },
    }

    spec = model_spec_from_dict(
        payload,
        spec_path=Path("configs/models/breast_cancer_demo.yaml"),
    )

    assert spec.policy.required_metadata_tags == (TAG_CONFIG_HASH,)
    assert spec.policy.required_release_status == "shadow"
    assert spec.policy.block_noop_promotion is False
    assert spec.policy.require_reproducibility_evidence is True
    assert spec.policy.minimum_metric_thresholds[0].metric == "accuracy"


def test_model_spec_loads_feature_contract_overrides() -> None:
    payload = {
        "schema_version": "model_spec/v1",
        "model_name": "feature_contract_override_model",
        "task": "binary_classifier",
        "label_column": "target",
        "source": {"kind": "sklearn_demo", "dataset_name": "breast_cancer"},
        "split": {"test_size": 0.2, "random_state": 42, "stratify": True},
        "preprocessor": {"kind": "standard_scaler"},
        "trainer": {
            "kind": "logistic_regression",
            "max_iter": 2000,
            "solver": "lbfgs",
            "class_weight": "balanced",
            "random_state": 42,
        },
        "evaluation": {
            "metrics": ["accuracy", "f1", "roc_auc"],
            "gate": {"metric": "roc_auc", "threshold": 0.95},
        },
        "feature_contract": {
            "version": "feature_contract_override_model.input/v1",
            "allow_unknown_fields": False,
            "features": [
                {"name": "feature_a", "dtype": "float"},
                {"name": "feature_b", "dtype": "string", "required": False},
            ],
        },
    }

    spec = model_spec_from_dict(
        payload,
        spec_path=Path("configs/models/breast_cancer_demo.yaml"),
    )

    assert spec.feature_contract.version == "feature_contract_override_model.input/v1"
    assert spec.feature_contract.allow_unknown_fields is False
    assert spec.feature_contract.features[0].name == "feature_a"
    assert spec.feature_contract.features[1].required is False
