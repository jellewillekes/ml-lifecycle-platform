"""Drive the local pipeline end-to-end by running ingest, featurize, train,
evaluate, and register as child MLflow runs under a single parent run.

Without flags it trains the model selected by the active profile/env (the
hosted jobs rely on this). ``--model <name>`` trains one discovered spec and
``--all`` trains every spec in ``configs/models/``; both isolate each model in
its own MLflow experiment and continue past a single model's failure."""

from __future__ import annotations

import argparse
import os

import mlflow
import pandas as pd

from ml_lifecycle_platform.common.constants import (
    ART_TRAIN_RUN_ID,
    STEP_TRAIN,
    TAG_STEP,
)
from ml_lifecycle_platform.common.jobs import start_job
from ml_lifecycle_platform.core.model_spec_types import ModelSpec
from ml_lifecycle_platform.core.model_specs import (
    discover_model_specs,
    resolve_spec_by_model_name,
)
from ml_lifecycle_platform.runtime.mlflow import ensure_experiment
from ml_lifecycle_platform.runtime.bootstrap import (
    configure_mlflow,
    get_runtime_context,
    reset_runtime_context,
)

STEP_MODULES = {
    "ingest": "ml_lifecycle_platform.pipeline.ingest",
    "validate_data": "ml_lifecycle_platform.pipeline.validate_data",
    "featurize": "ml_lifecycle_platform.pipeline.featurize",
    "train": "ml_lifecycle_platform.pipeline.train",
    "evaluate": "ml_lifecycle_platform.pipeline.evaluate",
    "validate_model": "ml_lifecycle_platform.pipeline.validate_model",
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


def _run_one_model() -> None:
    """Run the full pipeline for the model the active runtime points at.

    Each model runs its complete ingest-through-register sequence before the
    next one starts, so the shared artifacts dir is consumed before reuse.
    """
    runtime = get_runtime_context()
    configure_mlflow(runtime)
    ensure_experiment(runtime.experiment_name)
    mlflow.set_experiment(runtime.experiment_name)
    art_dir = runtime.artifacts_dir
    art_dir.mkdir(parents=True, exist_ok=True)

    _run_step("ingest")
    _run_step("validate_data")
    _run_step("featurize")
    _run_step("train")

    exp = mlflow.get_experiment_by_name(runtime.experiment_name)
    assert exp is not None

    train_run_id = _latest_train_run_id(exp.experiment_id)
    (art_dir / ART_TRAIN_RUN_ID).write_text(str(train_run_id), encoding="utf-8")
    print(f"[orchestrate] Captured {ART_TRAIN_RUN_ID}={train_run_id}")

    _run_step("evaluate")
    _run_step("validate_model")
    _run_step("register")


def _select_model(spec: ModelSpec) -> None:
    """Point the runtime (and the step subprocesses) at one model spec.

    The experiment is keyed on ``model_name`` so each model gets its own clean
    run history and the train-run lookup stays scoped to that model.
    """
    os.environ["MLP_MODEL_SPEC_PATH"] = str(spec.spec_path)
    os.environ["MODEL_NAME"] = spec.model_name
    os.environ["EXPERIMENT_NAME"] = spec.model_name
    reset_runtime_context()


def _resolve_specs(args: argparse.Namespace) -> list[ModelSpec] | None:
    """Return the specs to train, or ``None`` for the profile-selected model."""
    if args.all:
        specs = discover_model_specs()
        if not specs:
            raise SystemExit("No model specs found under configs/models/.")
        return specs
    if args.model:
        return [resolve_spec_by_model_name(args.model)]
    return None


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="orchestrate")
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--model", help="Train one model by its model_name")
    selector.add_argument(
        "--all",
        action="store_true",
        help="Train every spec in configs/models/",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    specs = _resolve_specs(args)
    runtime = get_runtime_context()
    with start_job("pipeline", level=runtime.log_level):
        if specs is None:
            _run_one_model()
            print("[orchestrate] Pipeline complete.")
            return

        failures: list[str] = []
        for spec in specs:
            print(f"[orchestrate] === model {spec.model_name} ===")
            _select_model(spec)
            try:
                _run_one_model()
            except Exception as error:  # isolate one model's failure
                print(f"[orchestrate] model {spec.model_name} FAILED: {error}")
                failures.append(spec.model_name)
        if failures:
            raise SystemExit("Pipeline failed for: " + ", ".join(failures))
        print(f"[orchestrate] Pipeline complete for {len(specs)} model(s).")


if __name__ == "__main__":
    main()
