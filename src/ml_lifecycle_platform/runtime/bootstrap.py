from __future__ import annotations

from ml_lifecycle_platform.core.ports import RuntimeMetadata
from ml_lifecycle_platform.runtime.context import RuntimeContext


def build_runtime_context() -> RuntimeContext:
    """Build a default runtime context.

    This is a non-functional wiring placeholder for UP-02.
    """

    return RuntimeContext(
        metadata=RuntimeMetadata(
            environment="local",
            tracking_uri="http://localhost:5050",
            registry_uri="http://localhost:5050",
            source="up-02-placeholder",
        )
    )
