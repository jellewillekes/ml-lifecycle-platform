from __future__ import annotations

# Shared constants.

# Contracts schema versions
DATASET_FINGERPRINT_SCHEMA_VERSION = "dataset_fingerprint/v1"
MODEL_REF_SCHEMA_VERSION = "model_ref/v1"
FEATURE_STATS_SCHEMA_VERSION = "feature_stats/v1"
REPRO_CONTRACT_SCHEMA_VERSION = "repro_contract/v1"
MODEL_SPEC_SCHEMA_VERSION = "model_spec/v1"

# MLflow tag keys
TAG_STEP = "step"
TAG_MODEL_NAME = "model_name"

TAG_GIT_SHA = "git_sha"
TAG_DATASET_CONTENT_HASH = "dataset_content_hash"
TAG_DATASET_SCHEMA_HASH = "dataset_schema_hash"
TAG_ROW_COUNT = "row_count"
TAG_DATA_SOURCE_URI = "data_source_uri"

# Promotion guardrail tags
# Dataset lineage already exists as several tags. Promotion also uses one stable
# fingerprint hash.
TAG_DATASET_FINGERPRINT = "dataset_fingerprint"
TAG_CONFIG_HASH = "config_hash"
TAG_TRAINING_RUN_ID = "training_run_id"
TAG_ENV_LOCK_HASH = "env_lock_hash"
TAG_DETERMINISTIC_SEED = "deterministic_seed"
TAG_REPRO_SCHEMA_VERSION = "repro_schema_version"

TAG_SOURCE_RUN_ID = "source_run_id"
TAG_GATE = "gate"
TAG_RELEASE_STATUS = "release_status"
TAG_PROMOTED_FROM_ALIAS = "promoted_from_alias"
TAG_PREVIOUS_PROD_VERSION = "previous_prod_version"

# MLflow tag values
GATE_PASSED = "passed"
GATE_FAILED = "failed"  # Used in tests.
RELEASE_STATUS_PREVIOUS_PROD = "previous_prod"

# Steps
STEP_INGEST = "ingest"
STEP_FEATURIZE = "featurize"
STEP_TRAIN = "train"
STEP_EVALUATE = "evaluate"
STEP_REGISTER = "register"
STEP_PROMOTE = "promote"

# Artifact file names
ART_TRAIN_RUN_ID = "TRAIN_RUN_ID"
ART_GATE_OK = "gate_ok.txt"
ART_REGISTERED_VERSION = "REGISTERED_VERSION"
ART_DATASET_FINGERPRINT_JSON = "dataset_fingerprint.json"
ART_EVALUATION_JSON = "evaluation.json"
ART_ROC_CURVE_PNG = "roc_curve.png"
ART_TRAIN_SUMMARY_JSON = "train_summary.json"
ART_REPRO_CONTRACT_JSON = "repro_contract.json"
ART_REPRO_PROBE_INPUTS_CSV = "probe_inputs.csv"
ART_REPRO_EXPECTED_PREDICTIONS_JSON = "expected_predictions.json"
ART_REPRO_REPORT_JSON = "reproduce_report.json"
ART_UV_LOCK = "uv.lock"

# Artifact paths inside MLflow
MLFLOW_ARTIFACT_PATH_REPORTS = "reports"
MLFLOW_ARTIFACT_PATH_MODEL = "model"
MLFLOW_ARTIFACT_PATH_REPRO = "repro"

# Aliases
ALIAS_CANDIDATE = "candidate"
ALIAS_PROD = "prod"
ALIAS_CHAMPION = "champion"

# Dataset file names
LABEL_COL = "target"
RAW_CSV = "raw.csv"
TRAIN_CSV = "train.csv"
TEST_CSV = "test.csv"
ART_PREPROCESSOR = "preprocessor.joblib"
