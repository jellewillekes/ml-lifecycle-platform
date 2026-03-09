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

# HTTP headers
HEADER_REQUEST_ID = "X-Request-Id"
HEADER_MODEL_VERSION = "X-Model-Version"
HEADER_FEATURE_CONTRACT_VERSION = "X-Feature-Contract-Version"
