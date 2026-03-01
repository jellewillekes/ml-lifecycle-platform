from __future__ import annotations

import hashlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    return sha256_bytes(payload.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def get_uv_lock_path() -> Path:
    path = REPO_ROOT / "uv.lock"
    if not path.exists():
        raise RuntimeError(f"uv.lock not found at expected repo root path: {path}")
    return path


def get_uv_lock_hash() -> str:
    return sha256_file(get_uv_lock_path())
