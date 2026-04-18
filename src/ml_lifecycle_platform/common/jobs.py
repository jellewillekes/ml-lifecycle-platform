"""Entrypoint helper shared by pipeline, promote, rollback, reproduce, and
maintenance jobs. Configures JSON logging, initialises OTel, binds a run_id,
opens the root span, and emits a ``job.start`` log line."""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace

from ml_lifecycle_platform.common.logging import (
    bind_log_context,
    clear_log_context,
    configure_logging,
)
from ml_lifecycle_platform.common.telemetry import init_telemetry


@contextmanager
def start_job(name: str, *, level: int | str = logging.INFO) -> Iterator[str]:
    """Open the root span for job ``name`` and yield its run_id.

    ``MLP_RUN_ID`` overrides the generated ID so Cloud Run Jobs can carry
    their execution ID through.
    """

    run_id = os.getenv("MLP_RUN_ID", "").strip() or uuid.uuid4().hex

    configure_logging(name, level=level)
    init_telemetry(name)
    bind_log_context(job_name=name, run_id=run_id)

    tracer = trace.get_tracer(name)
    logger = logging.getLogger(name)
    with tracer.start_as_current_span(f"{name}.main") as span:
        span.set_attribute("job_name", name)
        span.set_attribute("run_id", run_id)
        logger.info(
            "job.start",
            extra={"event": "job.start", "job_name": name, "run_id": run_id},
        )
        try:
            yield run_id
        finally:
            clear_log_context()
