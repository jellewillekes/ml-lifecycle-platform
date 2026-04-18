from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, Literal, cast

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

from ml_lifecycle_platform.runtime.mlflow import client as get_mlflow_client
from ml_lifecycle_platform.core.feature_contracts import FeatureContractValidationError
from ml_lifecycle_platform.core.model_spec_types import FeatureContractSpec
from ml_lifecycle_platform.core.model_specs import load_model_spec

from .constants import (
    ALIAS_CANDIDATE,
    ALIAS_PROD,
    HEADER_FEATURE_CONTRACT_VERSION,
    HEADER_MODEL_VERSION,
    HEADER_REQUEST_ID,
)
from .metrics import PREDICT_LATENCY_SECONDS, REQUESTS_TOTAL
from .model_store import get_model_store
from .prediction import run_prediction
from .router import (
    BucketContext,
    Mode,
    SeedSource,
    choose_canary_bucket,
    decide_routing,
)
from .settings import Settings, get_settings

logger = logging.getLogger("serving")


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
    except (ValueError, RuntimeError):
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


def _prod_model_loadable(settings: Settings) -> tuple[bool, str | None]:
    """Return whether the prod model is loadable."""
    store = get_model_store()
    try:
        _ = store.get_model(settings, ALIAS_PROD, required=True)
        return True, None
    except MlflowException as e:
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

    store = get_model_store()
    reg_ok, reg_detail = _registry_resolves_prod_alias(settings)
    model_ok = False
    model_detail: str | None = None
    if reg_ok:
        model_ok, model_detail = _prod_model_loadable(settings)

    ready = bool(reg_ok and model_ok)

    return {
        "status": "ok",
        "ready": ready,
        "model_name": settings.model_name,
        "prod_alias": settings.prod_alias,
        "candidate_alias": settings.candidate_alias,
        "prod_version": store.get_version(ALIAS_PROD),
        "candidate_version": store.get_version(ALIAS_CANDIDATE),
        "registry_ok": reg_ok,
        "registry_detail": reg_detail,
        "prod_model_ok": model_ok,
        "prod_model_detail": model_detail,
        "prod_model_loaded": store.is_prod_loaded(),
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
    store = get_model_store()
    try:
        contract = _feature_contract(settings)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return ModelMetadataResponse(
        model_name=settings.model_name,
        prod_alias=settings.prod_alias,
        candidate_alias=settings.candidate_alias,
        prod_version=store.get_version(ALIAS_PROD),
        candidate_version=store.get_version(ALIAS_CANDIDATE),
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

    try:
        contract = _feature_contract(settings)
        store = get_model_store()

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

        store.refresh_if_needed(
            settings,
            load_candidate=(primary_alias == ALIAS_CANDIDATE or decision.run_shadow),
        )

        result = run_prediction(
            store,
            settings,
            primary_alias=primary_alias,
            shadow_alias=shadow_alias,
            run_shadow=decision.run_shadow,
            contract=contract,
            rows=payload.rows,
            mode=mode,
        )

        latency_s = time.perf_counter() - t0

        if result.chosen_version:
            response.headers[HEADER_MODEL_VERSION] = result.chosen_version
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
            "shadow_mae": result.shadow_mae,
            "prod_version": store.get_version(ALIAS_PROD),
            "candidate_version": store.get_version(ALIAS_CANDIDATE),
        }
        logger.info(json.dumps(log, separators=(",", ":")))

        return PredictResponse(
            mode=mode,
            n=len(payload.rows),
            proba=result.y_primary,
            chosen=primary_alias,
            bucket=bucket,
            canary_pct=settings.canary_pct if mode == "canary" else None,
            bucket_seed_source=str(bucket_seed_source) if bucket_seed_source else None,
            metadata=PredictionMetadata(
                model_version=result.chosen_version,
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
        logger.exception("predict failed: %s", e)
        raise HTTPException(status_code=500, detail="internal error") from e

    finally:
        latency_s = time.perf_counter() - t0
        PREDICT_LATENCY_SECONDS.labels(
            mode=str(mode),
            status=str(status_code),
            chosen=chosen_label,
        ).observe(latency_s)
