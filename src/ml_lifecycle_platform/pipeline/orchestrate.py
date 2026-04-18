"""Drive the local pipeline end-to-end by running ingest, featurize, train,
evaluate, and register as child MLflow runs under a single parent run."""

from __future__ import annotations

import mlflow
import pandas as pd

from ml_lifecycle_platform.common.constants import (
    ART_TRAIN_RUN_ID,
    STEP_TRAIN,
    TAG_STEP,
)
from ml_lifecycle_platform.common.jobs import start_job
from ml_lifecycle_platform.runtime.mlflow import ensure_experiment
from ml_lifecycle_platform.runtime.bootstrap import (
    configure_mlflow,
    get_runtime_context,
)

STEP_MODULES = {
    "ingest": "ml_lifecycle_platform.pipeline.ingest",
    "featurize": "ml_lifecycle_platform.pipeline.featurize",
    "train": "ml_lifecycle_platform.pipeline.train",
    "evaluate": "ml_lifecycle_platform.pipeline.evaluate",
    "register": "ml_lifecycle_platform.registry.register",
}


def _run_step(module: str) -> None:
    print(f"[orchestrate] Running step: {module}")
    module_path = STEP_MODULES[module]
    runtime = get_runtime_context()
    return_code = runtime.job_runner.run_module(module_path)
    if return_code != 0:
        raise RuntimeError(f"Step {module} failed with exit code {return_code}.")


def _search_train_runs(experiment_id: str) -> pd.DataFrame:
    result = mlflow.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"tags.{TAG_STEP} = '{STEP_TRAIN}'",
        order_by=["attributes.start_time DESC"],
        max_results=1,
    )
    if not isinstance(result, pd.DataFrame):
        raise TypeError(f"mlflow.search_runs returned unexpected type: {type(result)}")
    return result


def _latest_train_run_id(experiment_id: str) -> str:
    runs = _search_train_runs(experiment_id)
    if runs.empty:
        raise RuntimeError("No train run found after training step.")
    return str(runs.iloc[0]["run_id"])


def main() -> None:
    runtime = get_runtime_context()
    with start_job("pipeline", level=runtime.log_level):
        configure_mlflow(runtime)
        ensure_experiment(runtime.experiment_name)
        mlflow.set_experiment(runtime.experiment_name)
        art_dir = runtime.artifacts_dir
        art_dir.mkdir(parents=True, exist_ok=True)

        _run_step("ingest")
        _run_step("featurize")
        _run_step("train")

        exp = mlflow.get_experiment_by_name(runtime.experiment_name)
        assert exp is not None

        train_run_id = _latest_train_run_id(exp.experiment_id)
        (art_dir / ART_TRAIN_RUN_ID).write_text(str(train_run_id), encoding="utf-8")
        print(f"[orchestrate] Captured {ART_TRAIN_RUN_ID}={train_run_id}")

        _run_step("evaluate")
        _run_step("register")

        print("[orchestrate] Pipeline complete.")


if __name__ == "__main__":
    main()
