"""Hot-swappable store of the prod and candidate models loaded from the
MLflow registry by alias, with background refresh and a unit-test stub."""

from __future__ import annotations

import threading
import time
from typing import Any, Literal

import pandas as pd

try:
    import mlflow
    from mlflow.exceptions import MlflowException
except Exception:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]
    MlflowException = Exception  # type: ignore[assignment, misc]

from ml_lifecycle_platform.runtime.mlflow import client as get_mlflow_client
from ml_lifecycle_platform.runtime.bootstrap import configure_mlflow

from .constants import ALIAS_CANDIDATE, ALIAS_PROD
from .settings import Settings


class _UnitTestModel:
    """Deterministic stub used when UNIT_TESTING=1."""

    def predict(self, df: pd.DataFrame) -> list[float]:
        return [1.0] * len(df)


def _load_model_from_registry(settings: Settings, alias: str) -> Any:
    if settings.unit_testing:
        return _UnitTestModel()

    if mlflow is None:
        raise RuntimeError("mlflow not available in serving image")

    pyfunc = getattr(mlflow, "pyfunc", None)
    if pyfunc is None:
        raise RuntimeError("mlflow.pyfunc is missing (mlflow install is broken)")

    configure_mlflow()
    return pyfunc.load_model(f"models:/{settings.model_name}@{alias}")


def _resolve_version(settings: Settings, alias: str) -> str | None:
    if settings.unit_testing or mlflow is None:
        return None
    try:
        client = get_mlflow_client()
        mv = client.get_model_version_by_alias(settings.model_name, alias)
        return str(mv.version)
    except MlflowException:
        return None


class ModelStore:
    """Thread-safe cache for prod and candidate models."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.model_prod: Any | None = None
        self.model_candidate: Any | None = None
        self.prod_version: str | None = None
        self.candidate_version: str | None = None
        self._last_refresh_ts: float = 0.0

    def reset(self) -> None:
        with self._lock:
            self.model_prod = None
            self.model_candidate = None
            self.prod_version = None
            self.candidate_version = None
            self._last_refresh_ts = 0.0

    def refresh_if_needed(
        self,
        settings: Settings,
        *,
        force: bool = False,
        load_candidate: bool = False,
    ) -> None:
        with self._lock:
            now = time.time()
            cache_is_warm = (now - self._last_refresh_ts) < settings.model_cache_ttl_sec
            needs_prod_refresh = self.model_prod is None or self.prod_version is None
            needs_candidate_refresh = load_candidate and (
                self.model_candidate is None or self.candidate_version is None
            )

            if (
                not force
                and cache_is_warm
                and not (needs_prod_refresh or needs_candidate_refresh)
            ):
                return

            if needs_prod_refresh and self.model_prod is None:
                self.model_prod = _load_model_from_registry(
                    settings, settings.prod_alias
                )

            if needs_candidate_refresh and self.model_candidate is None:
                self.model_candidate = _load_model_from_registry(
                    settings, settings.candidate_alias
                )

            if needs_prod_refresh:
                self.prod_version = self.prod_version or _resolve_version(
                    settings, settings.prod_alias
                )
            if needs_candidate_refresh:
                self.candidate_version = self.candidate_version or _resolve_version(
                    settings, settings.candidate_alias
                )

            self._last_refresh_ts = now

    def get_model(
        self,
        settings: Settings,
        alias: Literal["prod", "candidate"],
        required: bool,
    ) -> Any | None:
        self.refresh_if_needed(settings, load_candidate=(alias == ALIAS_CANDIDATE))
        with self._lock:
            model = self.model_prod if alias == ALIAS_PROD else self.model_candidate
        if required and model is None:
            raise RuntimeError(f"model for alias={alias} is not available")
        return model

    def get_version(self, alias: Literal["prod", "candidate"]) -> str | None:
        with self._lock:
            return self.prod_version if alias == ALIAS_PROD else self.candidate_version

    def is_prod_loaded(self) -> bool:
        return self.model_prod is not None


_store = ModelStore()


def get_model_store() -> ModelStore:
    return _store
