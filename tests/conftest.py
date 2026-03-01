from __future__ import annotations

import random
from collections.abc import Iterator
from pathlib import Path

import mlflow
import numpy as np
import pytest

TEST_TIER_MARKERS = ("unit", "integration", "e2e")


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    violations: list[str] = []

    for item in items:
        tiers = [
            marker for marker in TEST_TIER_MARKERS if item.get_closest_marker(marker)
        ]
        if len(tiers) != 1:
            declared = ", ".join(tiers) if tiers else "none"
            violations.append(f"- {item.nodeid}: declared {declared}")

    if violations:
        lines = [
            "Each collected test must declare exactly one test-tier marker:",
            "`unit`, `integration`, or `e2e`.",
            "",
            *violations,
        ]
        raise pytest.UsageError("\n".join(lines))


@pytest.fixture(autouse=True)
def deterministic_test_state() -> None:
    random.seed(0)
    np.random.seed(0)


@pytest.fixture()
def mlflow_sqlite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[str]:
    """Provide an isolated sqlite-backed MLflow registry for local tests."""
    db_path = tmp_path / "mlflow.db"
    uri = f"sqlite:///{db_path}"

    previous_tracking_uri = mlflow.get_tracking_uri()
    previous_registry_uri = mlflow.get_registry_uri()

    mlflow.set_tracking_uri(uri)
    mlflow.set_registry_uri(uri)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.setenv("MLFLOW_REGISTRY_URI", uri)

    try:
        yield uri
    finally:
        mlflow.set_tracking_uri(previous_tracking_uri)
        mlflow.set_registry_uri(previous_registry_uri)
