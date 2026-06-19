"""Pydantic `Settings` for the serving container — read straight from env
vars, independent of the runtime profile loader used by the CLI."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import (
    ALIAS_CANDIDATE,
    ALIAS_PROD,
    DEFAULT_EVENT_JSONL_PATH,
    DEFAULT_MODEL_NAME,
    ENV_CANARY_PCT,
    ENV_CANDIDATE_ALIAS,
    ENV_EVENT_BQ_TABLE,
    ENV_EVENT_FSYNC,
    ENV_EVENT_JSONL_PATH,
    ENV_EVENT_QUEUE_MAX,
    ENV_EVENT_SAMPLE_PCT,
    ENV_EVENT_SINK,
    ENV_GIT_SHA,
    ENV_LOG_LEVEL,
    ENV_MODEL_CACHE_TTL_SEC,
    ENV_MODEL_NAME,
    ENV_MODEL_SPEC_PATH,
    ENV_PROD_ALIAS,
    ENV_SERVICE_ENV,
    ENV_UNIT_TESTING,
)


class Settings(BaseSettings):
    """Serving app configuration — reads directly from env vars.

    Intentionally separate from RuntimeProfile: the serving container runs
    standalone without the local bootstrap, so it cannot use get_runtime_context().
    """

    model_config = SettingsConfigDict(extra="ignore")

    model_name: str = Field(default=DEFAULT_MODEL_NAME, validation_alias=ENV_MODEL_NAME)
    model_spec_path: str = Field(
        default="configs/models/breast_cancer_demo.yaml",
        validation_alias=ENV_MODEL_SPEC_PATH,
    )
    prod_alias: str = Field(default=ALIAS_PROD, validation_alias=ENV_PROD_ALIAS)
    candidate_alias: str = Field(
        default=ALIAS_CANDIDATE, validation_alias=ENV_CANDIDATE_ALIAS
    )

    canary_pct: int = Field(default=10, validation_alias=ENV_CANARY_PCT)
    model_cache_ttl_sec: float = Field(
        default=60.0, validation_alias=ENV_MODEL_CACHE_TTL_SEC
    )

    log_level: str = Field(default="INFO", validation_alias=ENV_LOG_LEVEL)

    # Prediction event-plane (cold sink). "none" disables emission entirely.
    event_sink: str = Field(default="none", validation_alias=ENV_EVENT_SINK)
    event_jsonl_path: str = Field(
        default=DEFAULT_EVENT_JSONL_PATH, validation_alias=ENV_EVENT_JSONL_PATH
    )
    event_bq_table: str = Field(default="", validation_alias=ENV_EVENT_BQ_TABLE)
    event_sample_pct: int = Field(
        default=100, ge=0, le=100, validation_alias=ENV_EVENT_SAMPLE_PCT
    )
    event_queue_max: int = Field(
        default=10000, ge=1, validation_alias=ENV_EVENT_QUEUE_MAX
    )
    event_fsync: bool = Field(default=False, validation_alias=ENV_EVENT_FSYNC)

    # Envelope metadata (reuses MLP_ENV / GIT_SHA already set on containers).
    service_env: str = Field(default="local", validation_alias=ENV_SERVICE_ENV)
    git_sha: str = Field(default="dev", validation_alias=ENV_GIT_SHA)

    # Disable real MLflow loads in unit tests.
    unit_testing: bool = Field(default=False, validation_alias=ENV_UNIT_TESTING)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Avoid reparsing env vars on every request.
    return Settings()
