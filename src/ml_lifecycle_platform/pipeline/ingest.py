from __future__ import annotations

from pathlib import Path

import mlflow
import pandas as pd
from sklearn.datasets import load_breast_cancer

from ml_lifecycle_platform.common.config import get_experiment_name, get_model_spec_path
from ml_lifecycle_platform.common.constants import (
    RAW_CSV,
    STEP_INGEST,
    TAG_MODEL_NAME,
    TAG_STEP,
)
from ml_lifecycle_platform.common.mlflow_utils import ensure_experiment
from ml_lifecycle_platform.core.batch_contracts import validate_labeled_dataset
from ml_lifecycle_platform.core.model_specs import (
    CsvSourceSpec,
    ModelSpec,
    load_model_spec,
)

DATA_DIR = Path("/app/data")


def _load_source_dataframe(spec: ModelSpec) -> pd.DataFrame:
    if isinstance(spec.source, CsvSourceSpec):
        csv_path = spec.source.resolved_path(spec_path=spec.spec_path)
        df = pd.read_csv(csv_path)
    else:
        dataset = load_breast_cancer(as_frame=True)
        df = dataset.frame.copy()

    return validate_labeled_dataset(
        df,
        spec=spec,
        stage="ingest",
        dataset_name="source",
    )


def main() -> None:
    ensure_experiment(get_experiment_name())
    mlflow.set_experiment(get_experiment_name())
    spec = load_model_spec(get_model_spec_path())

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with mlflow.start_run(run_name="ingest") as run:
        mlflow.set_tag(TAG_STEP, STEP_INGEST)
        mlflow.set_tag(TAG_MODEL_NAME, spec.model_name)

        df = _load_source_dataframe(spec)

        raw_path = DATA_DIR / RAW_CSV
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
