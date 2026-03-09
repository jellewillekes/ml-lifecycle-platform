from __future__ import annotations

from pathlib import Path

import pytest

from ml_lifecycle_platform.core.model_specs import load_model_spec, model_spec_from_dict

pytestmark = pytest.mark.unit


def test_load_demo_model_spec() -> None:
    spec = load_model_spec("configs/models/breast_cancer_demo.yaml")

    assert spec.model_name == "breast_cancer_clf"
    assert spec.source.kind == "sklearn_demo"
    assert spec.label_column == "target"
    assert spec.evaluation.gate.metric == "roc_auc"


def test_load_csv_model_spec_resolves_relative_data_path() -> None:
    spec = load_model_spec("configs/models/local_csv_binary_classifier.yaml")

    assert spec.source.kind == "csv"
    assert spec.data_source_uri().startswith("file://")


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
