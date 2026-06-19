"""Serving-local constants: alias string literals, environment variable
names, and HTTP header keys. Kept separate from `common.constants` because
the serving image ships without the rest of the package."""

from __future__ import annotations

from typing import Literal

# Serving builds as a separate image. Keep local constants here.

DEFAULT_MODEL_NAME = "breast_cancer_clf"

ALIAS_PROD: Literal["prod"] = "prod"
ALIAS_CANDIDATE: Literal["candidate"] = "candidate"

ENV_MODEL_NAME = "MODEL_NAME"
ENV_PROD_ALIAS = "PROD_ALIAS"
ENV_CANDIDATE_ALIAS = "CANDIDATE_ALIAS"
ENV_CANARY_PCT = "CANARY_PCT"
ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_UNIT_TESTING = "UNIT_TESTING"
ENV_MODEL_CACHE_TTL_SEC = "MODEL_CACHE_TTL_SEC"
ENV_MODEL_SPEC_PATH = "MLP_MODEL_SPEC_PATH"

# Prediction event-plane (cold sink) selection and envelope metadata.
ENV_EVENT_SINK = "MLP_EVENT_SINK"
ENV_EVENT_JSONL_PATH = "MLP_EVENT_JSONL_PATH"
ENV_EVENT_BQ_TABLE = "MLP_EVENT_BQ_TABLE"
ENV_EVENT_SAMPLE_PCT = "MLP_EVENT_SAMPLE_PCT"
ENV_EVENT_QUEUE_MAX = "MLP_EVENT_QUEUE_MAX"
ENV_EVENT_FSYNC = "MLP_EVENT_FSYNC"
ENV_SERVICE_ENV = "MLP_ENV"
ENV_GIT_SHA = "GIT_SHA"

DEFAULT_EVENT_JSONL_PATH = "artifacts/prediction-events.jsonl"

# HTTP headers
HEADER_REQUEST_ID = "X-Request-Id"
HEADER_MODEL_VERSION = "X-Model-Version"
HEADER_FEATURE_CONTRACT_VERSION = "X-Feature-Contract-Version"
