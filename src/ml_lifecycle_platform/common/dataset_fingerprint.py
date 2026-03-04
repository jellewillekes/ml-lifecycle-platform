from __future__ import annotations

# Backward-compatible import path.
# Canonical location: ml_lifecycle_platform.contracts.dataset_fingerprint
from ml_lifecycle_platform.contracts.dataset_fingerprint import (  # noqa: F401
    DatasetFingerprint,
    compute_fingerprint,
    content_hash,
    get_git_sha,
    read_fingerprint_json,
    schema_hash,
    write_fingerprint_json,
)
