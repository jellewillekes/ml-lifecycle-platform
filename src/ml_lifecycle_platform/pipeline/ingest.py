"""Load the raw dataset from the model spec's declared source via its
``DataSource`` adapter and persist it to ``data/raw.csv`` with lineage tags on
the MLflow run."""

from __future__ import annotations

import mlflow
import pandas as pd

from ml_lifecycle_platform.backends.common.data_sources.resolver import (
    build_data_source,
)
from ml_lifecycle_platform.common.constants import (
    RAW_CSV,
    STEP_INGEST,
    TAG_MODEL_NAME,
    TAG_STEP,
)
from ml_lifecycle_platform.runtime.mlflow import ensure_experiment
from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context
from ml_lifecycle_platform.core.batch_contracts import validate_labeled_dataset
from ml_lifecycle_platform.core.model_spec_types import ModelSpec
from ml_lifecycle_platform.core.model_specs import load_model_spec


def _load_source_dataframe(spec: ModelSpec) -> pd.DataFrame:
    df = build_data_source(spec).fetch()
    return validate_labeled_dataset(
        df,
        spec=spec,
        stage="ingest",
        dataset_name="source",
    )


def main() -> None:
    ctx = get_runtime_context()
    ensure_experiment(ctx.experiment_name)
    mlflow.set_experiment(ctx.experiment_name)
    spec = load_model_spec(ctx.model_spec_path)

    ctx.data_dir.mkdir(parents=True, exist_ok=True)

    with mlflow.start_run(run_name="ingest") as run:
        mlflow.set_tag(TAG_STEP, STEP_INGEST)
        mlflow.set_tag(TAG_MODEL_NAME, spec.model_name)

        df = _load_source_dataframe(spec)

        raw_path = ctx.data_dir / RAW_CSV
        df.to_csv(raw_path, index=False)

        mlflow.log_params(
            {
                "source_kind": spec.source.kind,
                "data_source_uri": spec.data_source_uri(),
                "rows": int(df.shape[0]),
                "cols": int(df.shape[1]),
            }
        )
        mlflow.log_artifact(str(raw_path))

        print(f"[ingest] run_id={run.info.run_id} wrote={raw_path}")


if __name__ == "__main__":
    main()
