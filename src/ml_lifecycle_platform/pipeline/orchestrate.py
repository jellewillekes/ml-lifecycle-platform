from __future__ import annotations

import mlflow

from ml_lifecycle_platform.common.config import get_experiment_name
from ml_lifecycle_platform.common.constants import (
    ART_TRAIN_RUN_ID,
    STEP_TRAIN,
    TAG_STEP,
)
from ml_lifecycle_platform.common.mlflow_utils import ensure_experiment
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


def _latest_train_run_id(experiment_id: str) -> str:
    runs = mlflow.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"tags.{TAG_STEP} = '{STEP_TRAIN}'",
        order_by=["attributes.start_time DESC"],
        max_results=1,
    )

    if hasattr(runs, "empty") and hasattr(runs, "iloc"):
        if runs.empty:  # type: ignore[attr-defined]
            raise RuntimeError("No train run found after training step.")
        return str(runs.iloc[0]["run_id"])  # type: ignore[index]

    if isinstance(runs, list):
        if not runs:
            raise RuntimeError("No train run found after training step.")
        run0 = runs[0]
        run_id = getattr(getattr(run0, "info", None), "run_id", None)
        if not run_id:
            raise RuntimeError("Train run object missing run_id.")
        return str(run_id)

    raise TypeError(f"Unexpected mlflow.search_runs return type: {type(runs)}")


def main() -> None:
    runtime = get_runtime_context()
    configure_mlflow(runtime)
    ensure_experiment(get_experiment_name())
    mlflow.set_experiment(get_experiment_name())
    art_dir = runtime.artifacts_dir
    art_dir.mkdir(parents=True, exist_ok=True)

    _run_step("ingest")
    _run_step("featurize")
    _run_step("train")

    exp = mlflow.get_experiment_by_name(get_experiment_name())
    assert exp is not None

    train_run_id = _latest_train_run_id(exp.experiment_id)
    (art_dir / ART_TRAIN_RUN_ID).write_text(str(train_run_id), encoding="utf-8")
    print(f"[orchestrate] Captured {ART_TRAIN_RUN_ID}={train_run_id}")

    _run_step("evaluate")
    _run_step("register")

    print("[orchestrate] Pipeline complete.")


if __name__ == "__main__":
    main()
