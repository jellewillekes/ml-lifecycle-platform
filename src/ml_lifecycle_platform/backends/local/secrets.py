"""Environment-variable-backed `Secrets` adapter for the local runtime
profile; pulls values directly from `os.environ`."""

from __future__ import annotations

import os


class EnvSecrets:
    """Env-var backed secrets adapter for the local runtime."""

    def get(self, name: str, *, default: str | None = None) -> str | None:
        return os.getenv(name, default)
