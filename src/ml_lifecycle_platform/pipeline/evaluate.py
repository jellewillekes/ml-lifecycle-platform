"""Load the trained model from MLflow, score it on the held-out test split,
emit evaluation artifacts, and write the gate marker when the gate passes."""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import mlflow
from sklearn.metrics import RocCurveDisplay

from ml_lifecycle_platform.common.constants import (
    ART_EVALUATION_JSON,
    ART_GATE_OK,
    ART_ROC_CURVE_PNG,
    MLFLOW_ARTIFACT_PATH_REPORTS,
    STEP_EVALUATE,
    TAG_STEP,
)
from ml_lifecycle_platform.runtime.mlflow import ensure_experiment
from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context
from ml_lifecycle_platform.core.model_specs import load_model_spec
from ml_lifecycle_platform.pipeline.metrics import compute_binary_metrics
from ml_lifecycle_platform.pipeline.scoring import load_scored_test_split


def main() -> None:
    ctx = get_runtime_context()
    ensure_experiment(ctx.experiment_name)
    mlflow.set_experiment(ctx.experiment_name)
    spec = load_model_spec(ctx.model_spec_path)

    scored = load_scored_test_split(ctx, spec)

    metrics = compute_binary_metrics(
        metric_names=spec.evaluation.metrics,
        y_true=scored.y_true,
        pred=scored.pred,
        proba=scored.proba,
        prefix="eval",
    )

    ctx.artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = ctx.artifacts_dir / ART_EVALUATION_JSON
    report_bytes = json.dumps(metrics, indent=2, sort_keys=True).encode("utf-8")
    ctx.artifact_store.write_bytes(
        report_path.relative_to(ctx.artifacts_dir).as_posix(), report_bytes
    )

    fig_path = ctx.artifacts_dir / ART_ROC_CURVE_PNG
    plt.figure()
    RocCurveDisplay.from_predictions(scored.y_true, scored.proba)
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    with mlflow.start_run(run_name="evaluate") as run:
        mlflow.set_tag(TAG_STEP, STEP_EVALUATE)
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(
            str(report_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPORTS
        )
        mlflow.log_artifact(str(fig_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPORTS)

        gate_metric_key = f"eval_{spec.evaluation.gate.metric}"
        gate_ok = metrics[gate_metric_key] >= spec.evaluation.gate.threshold
        gate_path = ctx.artifacts_dir / ART_GATE_OK
        gate_path.write_text("true" if gate_ok else "false", encoding="utf-8")
        mlflow.log_artifact(str(gate_path), artifact_path=MLFLOW_ARTIFACT_PATH_REPORTS)

        print(f"[evaluate] run_id={run.info.run_id} metrics={metrics}")
        print(f"[evaluate] gate_ok={gate_ok}")


if __name__ == "__main__":
    main()
