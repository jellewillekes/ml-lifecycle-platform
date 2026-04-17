from __future__ import annotations

import json
import logging
import math
import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, Literal, cast

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response

try:
    import mlflow  # type: ignore
    from mlflow.exceptions import MlflowException
except Exception:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]
    MlflowException = Exception  # type: ignore[assignment, misc]

from ml_lifecycle_platform.common.mlflow_utils import client as get_mlflow_client
from ml_lifecycle_platform.core.feature_contracts import (
    FeatureContractValidationError,
    validate_rows_against_contract,
)
from ml_lifecycle_platform.core.model_specs import FeatureContractSpec, load_model_spec
from ml_lifecycle_platform.runtime.bootstrap import configure_mlflow

from .constants import (
    ALIAS_CANDIDATE,
    ALIAS_PROD,
    HEADER_FEATURE_CONTRACT_VERSION,
    HEADER_MODEL_VERSION,
    HEADER_REQUEST_ID,
)
from .metrics import PREDICT_LATENCY_SECONDS, REQUESTS_TOTAL, SHADOW_DIFF_MAE
from .router import (
    BucketContext,
    Mode,
    SeedSource,
    choose_canary_bucket,
    decide_routing,
)
from .settings import Settings, get_settings

logger = logging.getLogger("serving")


# Module-level cache. Tests monkeypatch it.
model_prod: Any | None = None
model_candidate: Any | None = None
prod_version: str | None = None
candidate_version: str | None = None
_last_refresh_ts: float = 0.0


def _configure_logging(settings: Settings) -> None:
    # Safe to call more than once.
    logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    _configure_logging(settings)
    logger.info("serving started")
    yield
    logger.info("serving stopped")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Set or preserve the request ID."""
    incoming = request.headers.get(HEADER_REQUEST_ID)
    if incoming and incoming.strip():
        request.state.request_id = incoming.strip()
        request.state.client_provided_request_id = True
    else:
        request.state.request_id = uuid.uuid4().hex
        request.state.client_provided_request_id = False

    response = await call_next(request)
    response.headers[HEADER_REQUEST_ID] = request.state.request_id
    return response


@app.middleware("http")
async def coarse_metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Count requests with bounded labels."""

    endpoint = request.url.path

    # Skip self-scrape noise.
    if endpoint == "/metrics":
        return await call_next(request)

    mode_label = request.query_params.get("mode", "") if endpoint == "/predict" else ""

    try:
        response = await call_next(request)
    except HTTPException as e:
        REQUESTS_TOTAL.labels(
            endpoint=endpoint, mode=mode_label, status=str(e.status_code)
        ).inc()
        raise
    except Exception:
        REQUESTS_TOTAL.labels(endpoint=endpoint, mode=mode_label, status="500").inc()
        raise

    REQUESTS_TOTAL.labels(
        endpoint=endpoint, mode=mode_label, status=str(response.status_code)
    ).inc()
    return response


PredictionScalar = bool | int | float | str | None


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[dict[str, PredictionScalar]] = Field(
        ..., description="List of feature dicts (one per row)"
    )


class PredictionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_version: str | None
    contract_version: str


class PredictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Mode
    n: int
    proba: list[float]
    chosen: Literal["prod", "candidate"]
    bucket: int | None = None
    canary_pct: int | None = None
    bucket_seed_source: str | None = None
    metadata: PredictionMetadata


class ModelMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str
    prod_alias: str
    candidate_alias: str
    prod_version: str | None
    candidate_version: str | None
    contract_version: str
    allow_unknown_fields: bool


class SchemaFieldResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    dtype: str
    required: bool


class SchemaMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str
    contract_version: str
    allow_unknown_fields: bool
    features: list[SchemaFieldResponse]


class _UnitTestModel:
    """Deterministic stub for unit tests."""

    def predict(self, df: pd.DataFrame) -> list[float]:
        # Return deterministic probabilities in [0, 1].
        n = len(df)
        return [1.0] * n


def _models_uri(settings: Settings, alias: str) -> str:
    return f"models:/{settings.model_name}@{alias}"


@lru_cache(maxsize=8)
def _load_feature_contract(
    model_name: str, model_spec_path: str
) -> FeatureContractSpec:
    spec = load_model_spec(model_spec_path)
    if spec.model_name != model_name:
        raise RuntimeError(
            f"Active model spec {spec.spec_path} targets {spec.model_name}, not {model_name}."
        )
    return spec.feature_contract


def _feature_contract(settings: Settings) -> FeatureContractSpec:
    return _load_feature_contract(settings.model_name, settings.model_spec_path)


def _registry_resolves_prod_alias(settings: Settings) -> tuple[bool, str | None]:
    """Return whether the prod alias resolves."""
    if settings.unit_testing:
        return True, None
    if mlflow is None:
        return False, "mlflow not available in serving image"

    try:
        client = get_mlflow_client()
        _ = client.get_model_version_by_alias(settings.model_name, settings.prod_alias)
        return True, None
    except MlflowException as e:
        return False, f"registry check failed: {e}"


def _get_version(settings: Settings, alias: str) -> str | None:
    if settings.unit_testing or mlflow is None:
        return None
    try:
        client = get_mlflow_client()
        mv = client.get_model_version_by_alias(settings.model_name, alias)
        return str(mv.version)
    except MlflowException:
        return None


def _load_model(settings: Settings, alias: str) -> Any:
    # Unit tests always use a deterministic stub.
    if settings.unit_testing:
        return _UnitTestModel()

    if mlflow is None:
        raise RuntimeError("mlflow not available in serving image")

    # Guard against broken or stub MLflow installs.
    pyfunc = getattr(mlflow, "pyfunc", None)
    if pyfunc is None:
        raise RuntimeError("mlflow.pyfunc is missing (mlflow install is broken)")

    configure_mlflow()
    return pyfunc.load_model(_models_uri(settings, alias))


def _refresh_models_if_needed(
    settings: Settings,
    *,
    force: bool = False,
    load_candidate: bool = False,
) -> None:
    """Refresh cached models and versions."""
    global \
        model_prod, \
        model_candidate, \
        prod_version, \
        candidate_version, \
        _last_refresh_ts

    now = time.time()
    cache_is_warm = (now - _last_refresh_ts) < settings.model_cache_ttl_sec
    needs_prod_refresh = model_prod is None or prod_version is None
    needs_candidate_refresh = load_candidate and (
        model_candidate is None or candidate_version is None
    )

    if (
        not force
        and cache_is_warm
        and not (needs_prod_refresh or needs_candidate_refresh)
    ):
        return

    if needs_prod_refresh and model_prod is None:
        model_prod = _load_model(settings, settings.prod_alias)

    if needs_candidate_refresh and model_candidate is None:
        model_candidate = _load_model(settings, settings.candidate_alias)

    if needs_prod_refresh:
        prod_version = prod_version or _get_version(settings, settings.prod_alias)
    if needs_candidate_refresh:
        candidate_version = candidate_version or _get_version(
            settings, settings.candidate_alias
        )

    _last_refresh_ts = now


def _get_model(
    settings: Settings, alias: Literal["prod", "candidate"], required: bool
) -> Any | None:
    _refresh_models_if_needed(settings, load_candidate=(alias == ALIAS_CANDIDATE))
    model = model_prod if alias == ALIAS_PROD else model_candidate
    if required and model is None:
        raise RuntimeError(f"model for alias={alias} is not available")
    return model


def _prod_model_loadable(settings: Settings) -> tuple[bool, str | None]:
    """Return whether the prod model is loadable."""
    try:
        _ = _get_model(settings, ALIAS_PROD, required=True)
        return True, None
    except Exception as e:
        return False, f"prod model not loadable: {e}"


@app.get("/livez")
def livez() -> dict[str, str]:
    # No dependencies.
    return {"status": "alive"}


@app.get("/readyz")
def readyz() -> Response:
    settings = get_settings()
    _configure_logging(settings)

    reg_ok, reg_detail = _registry_resolves_prod_alias(settings)
    if not reg_ok:
        return Response(
            content=reg_detail or "not ready", status_code=503, media_type="text/plain"
        )

    model_ok, model_detail = _prod_model_loadable(settings)
    if not model_ok:
        return Response(
            content=model_detail or "not ready",
            status_code=503,
            media_type="text/plain",
        )

    return Response(content="ready", status_code=200, media_type="text/plain")


@app.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    _configure_logging(settings)

    reg_ok, reg_detail = _registry_resolves_prod_alias(settings)
    model_ok = False
    model_detail: str | None = None
    if reg_ok:
        model_ok, model_detail = _prod_model_loadable(settings)

    model_loaded = bool(model_prod is not None and model_ok)
    ready = bool(reg_ok and model_ok)

    return {
        "status": "ok",
        "ready": ready,
        "model_name": settings.model_name,
        "prod_alias": settings.prod_alias,
        "candidate_alias": settings.candidate_alias,
        "prod_version": prod_version,
        "candidate_version": candidate_version,
        "registry_ok": reg_ok,
        "registry_detail": reg_detail,
        "prod_model_ok": model_ok,
        "prod_model_detail": model_detail,
        "prod_model_loaded": model_loaded,
        "cache_ttl_sec": settings.model_cache_ttl_sec,
    }


@app.get("/metrics")
def metrics() -> Response:
    payload = generate_latest()
    return Response(payload, media_type=CONTENT_TYPE_LATEST)


@app.get("/metadata/model", response_model=ModelMetadataResponse)
def metadata_model() -> ModelMetadataResponse:
    settings = get_settings()
    _configure_logging(settings)
    try:
        contract = _feature_contract(settings)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return ModelMetadataResponse(
        model_name=settings.model_name,
        prod_alias=settings.prod_alias,
        candidate_alias=settings.candidate_alias,
        prod_version=_get_version(settings, settings.prod_alias),
        candidate_version=_get_version(settings, settings.candidate_alias),
        contract_version=contract.version,
        allow_unknown_fields=contract.allow_unknown_fields,
    )


@app.get("/metadata/schema", response_model=SchemaMetadataResponse)
def metadata_schema() -> SchemaMetadataResponse:
    settings = get_settings()
    _configure_logging(settings)
    try:
        contract = _feature_contract(settings)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return SchemaMetadataResponse(
        model_name=settings.model_name,
        contract_version=contract.version,
        allow_unknown_fields=contract.allow_unknown_fields,
        features=[
            SchemaFieldResponse(
                name=feature.name,
                dtype=feature.dtype,
                required=feature.required,
            )
            for feature in contract.features
        ],
    )


@app.post("/predict", response_model=PredictResponse)
async def predict(
    request: Request,
    payload: PredictRequest,
    response: Response,
    mode: Mode = Query(default="prod", description="prod|candidate|shadow|canary"),
) -> PredictResponse:
    settings = get_settings()
    _configure_logging(settings)

    t0 = time.perf_counter()
    status_code: int = 200
    chosen_label: Literal["prod", "candidate", "unknown"] = "unknown"

    bucket: int | None = None
    bucket_seed_source: SeedSource | None = None
    shadow_mae: float | None = None

    try:
        contract = _feature_contract(settings)

        # Bucket only matters in canary mode.
        if mode == "canary":
            bd = choose_canary_bucket(
                BucketContext(
                    request_id=getattr(request.state, "request_id", None),
                    client_provided_request_id=bool(
                        getattr(request.state, "client_provided_request_id", False)
                    ),
                    rows=payload.rows,
                )
            )
            bucket = bd.bucket
            bucket_seed_source = bd.seed_source
            decision = decide_routing(
                mode=mode,
                canary_pct=settings.canary_pct,
                bucket=bucket,
            )
        else:
            decision = decide_routing(
                mode=mode,
                canary_pct=settings.canary_pct,
                bucket=0,
            )

        primary_alias: Literal["prod", "candidate"] = decision.chosen
        chosen_label = primary_alias

        shadow_alias = cast(
            Literal["prod", "candidate"],
            ALIAS_CANDIDATE if primary_alias == ALIAS_PROD else ALIAS_PROD,
        )

        # Load candidate only when needed.
        _refresh_models_if_needed(
            settings,
            load_candidate=(primary_alias == ALIAS_CANDIDATE or decision.run_shadow),
        )

        # Primary model must exist.
        model_primary = _get_model(settings, primary_alias, required=True)
        if model_primary is None:
            status_code = 503
            raise HTTPException(
                status_code=503, detail=f"model not available: {primary_alias}"
            )

        validated_rows = validate_rows_against_contract(payload.rows, contract)
        df = pd.DataFrame(validated_rows)
        y_primary = model_primary.predict(df)  # type: ignore[union-attr]
        y_primary_list = [float(x) for x in list(y_primary)]

        # Shadow prediction is best-effort.
        if decision.run_shadow:
            model_shadow = _get_model(settings, shadow_alias, required=False)
            if model_shadow is not None:
                try:
                    y_shadow = model_shadow.predict(df)  # type: ignore[union-attr]
                    y_shadow_list = [float(x) for x in list(y_shadow)]
                    diffs = [abs(a - b) for a, b in zip(y_primary_list, y_shadow_list)]
                    shadow_mae = sum(diffs) / max(len(diffs), 1)
                except Exception as e:
                    logger.warning("shadow prediction failed: %s", e)

        latency_s = time.perf_counter() - t0

        if shadow_mae is not None and math.isfinite(shadow_mae):
            SHADOW_DIFF_MAE.labels(mode=str(mode)).observe(shadow_mae)

        selected_model_version = (
            prod_version if primary_alias == ALIAS_PROD else candidate_version
        )
        if selected_model_version:
            response.headers[HEADER_MODEL_VERSION] = selected_model_version
        response.headers[HEADER_FEATURE_CONTRACT_VERSION] = contract.version

        log: dict[str, Any] = {
            "event": "predict",
            "request_id": getattr(request.state, "request_id", None),
            "mode": mode,
            "chosen": primary_alias,
            "status": status_code,
            "latency_ms": int(latency_s * 1000),
            "bucket": bucket,
            "bucket_seed_source": str(bucket_seed_source)
            if bucket_seed_source
            else None,
            "canary_pct": settings.canary_pct if mode == "canary" else None,
            "shadow_mae": shadow_mae,
            "prod_version": prod_version,
            "candidate_version": candidate_version,
        }
        logger.info(json.dumps(log, separators=(",", ":")))

        return PredictResponse(
            mode=mode,
            n=len(payload.rows),
            proba=y_primary_list,
            chosen=primary_alias,
            bucket=bucket,
            canary_pct=settings.canary_pct if mode == "canary" else None,
            bucket_seed_source=str(bucket_seed_source) if bucket_seed_source else None,
            metadata=PredictionMetadata(
                model_version=selected_model_version,
                contract_version=contract.version,
            ),
        )

    except FeatureContractValidationError as e:
        status_code = 422
        raise HTTPException(status_code=422, detail=e.to_dict()) from e

    except HTTPException as e:
        status_code = e.status_code
        raise

    except RuntimeError as e:
        status_code = 503
        raise HTTPException(status_code=503, detail=str(e)) from e

    except Exception as e:
        status_code = 500
        raise HTTPException(status_code=500, detail="internal error") from e

    finally:
        latency_s = time.perf_counter() - t0
        PREDICT_LATENCY_SECONDS.labels(
            mode=str(mode),
            status=str(status_code),
            chosen=chosen_label,
        ).observe(latency_s)
