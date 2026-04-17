from __future__ import annotations

import joblib
import mlflow
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ml_lifecycle_platform.common.constants import (
    ART_PREPROCESSOR,
    RAW_CSV,
    STEP_FEATURIZE,
    TAG_MODEL_NAME,
    TAG_STEP,
    TEST_CSV,
    TRAIN_CSV,
)
from ml_lifecycle_platform.common.mlflow_utils import ensure_experiment
from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context
from ml_lifecycle_platform.core.batch_contracts import validate_labeled_dataset
from ml_lifecycle_platform.core.model_specs import load_model_spec


def main() -> None:
    ctx = get_runtime_context()
    ensure_experiment(ctx.experiment_name)
    mlflow.set_experiment(ctx.experiment_name)
    spec = load_model_spec(ctx.model_spec_path)

    ctx.data_dir.mkdir(parents=True, exist_ok=True)
    ctx.artifacts_dir.mkdir(parents=True, exist_ok=True)

    raw_path = ctx.data_dir / RAW_CSV
    if not raw_path.exists():
        raise RuntimeError(f"Missing raw dataset: {raw_path}. Run ingest first.")

    df = pd.read_csv(raw_path)
    df = validate_labeled_dataset(
        df,
        spec=spec,
        stage="featurize",
        dataset_name="raw",
    )
    if spec.label_column not in df.columns:
        raise RuntimeError(f"Expected column {spec.label_column!r} in {RAW_CSV}")

    X = df.drop(columns=[spec.label_column])
    y = df[spec.label_column].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=spec.split.test_size,
        random_state=spec.split.random_state,
        stratify=y if spec.split.stratify else None,
    )

    train_df = X_train.copy()
    test_df = X_test.copy()

    train_df[spec.label_column] = y_train.values
    test_df[spec.label_column] = y_test.values
    train_df = validate_labeled_dataset(
        train_df,
        spec=spec,
        stage="featurize",
        dataset_name="train",
    )
    test_df = validate_labeled_dataset(
        test_df,
        spec=spec,
        stage="featurize",
        dataset_name="test",
    )

    train_path = ctx.data_dir / TRAIN_CSV
    test_path = ctx.data_dir / TEST_CSV
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    preprocessor = StandardScaler(with_mean=True, with_std=True)
    preprocessor_path = ctx.artifacts_dir / ART_PREPROCESSOR
    joblib.dump(preprocessor, preprocessor_path)

    with mlflow.start_run(run_name="featurize") as run:
        mlflow.set_tag(TAG_STEP, STEP_FEATURIZE)
        mlflow.set_tag(TAG_MODEL_NAME, spec.model_name)

        mlflow.log_params(
            {
                "test_size": spec.split.test_size,
                "random_state": spec.split.random_state,
                "stratify": spec.split.stratify,
                "preprocessor": spec.preprocessor.kind,
            }
        )

        mlflow.log_artifact(str(train_path))
        mlflow.log_artifact(str(test_path))
        mlflow.log_artifact(str(preprocessor_path))

        print(
            f"[featurize] run_id={run.info.run_id} wrote={train_path} {test_path} {preprocessor_path}"
        )


if __name__ == "__main__":
    main()
