from __future__ import annotations

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import RocCurveDisplay

from ml_lifecycle_platform.common.constants import (
    ART_EVALUATION_JSON,
    ART_GATE_OK,
    ART_ROC_CURVE_PNG,
    ART_TRAIN_RUN_ID,
    MLFLOW_ARTIFACT_PATH_MODEL,
    MLFLOW_ARTIFACT_PATH_REPORTS,
    STEP_EVALUATE,
    TAG_STEP,
    TEST_CSV,
)
from ml_lifecycle_platform.common.mlflow_utils import ensure_experiment, write_json
from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context
from ml_lifecycle_platform.core.batch_contracts import validate_labeled_dataset
from ml_lifecycle_platform.core.model_specs import load_model_spec
from ml_lifecycle_platform.pipeline.metrics import compute_binary_metrics


def main() -> None:
    ctx = get_runtime_context()
    ensure_experiment(ctx.experiment_name)
    mlflow.set_experiment(ctx.experiment_name)
    spec = load_model_spec(ctx.model_spec_path)

    test_df = pd.read_csv(ctx.data_dir / TEST_CSV)
    test_df = validate_labeled_dataset(
        test_df,
        spec=spec,
        stage="evaluate",
        dataset_name="test",
    )
    X_test = test_df.drop(columns=[spec.label_column])
    y_test = test_df[spec.label_column].astype(int)

    train_run_id = (
        (ctx.artifacts_dir / ART_TRAIN_RUN_ID).read_text(encoding="utf-8").strip()
    )

    model_uri = f"runs:/{train_run_id}/{MLFLOW_ARTIFACT_PATH_MODEL}"
    model = mlflow.pyfunc.load_model(model_uri)

    proba = model.predict(X_test)
    pred = (np.array(proba) >= 0.5).astype(int)

    metrics = compute_binary_metrics(
        metric_names=spec.evaluation.metrics,
        y_true=y_test,
        pred=pred,
        proba=proba,
        prefix="eval",
    )

    ctx.artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = ctx.artifacts_dir / ART_EVALUATION_JSON
    write_json(report_path, metrics)

    fig_path = ctx.artifacts_dir / ART_ROC_CURVE_PNG
    plt.figure()
    RocCurveDisplay.from_predictions(y_test, proba)
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

        print(
            f"[evaluate] run_id={run.info.run_id} train_run_id={train_run_id} metrics={metrics}"
        )
        print(f"[evaluate] gate_ok={gate_ok}")


if __name__ == "__main__":
    main()
