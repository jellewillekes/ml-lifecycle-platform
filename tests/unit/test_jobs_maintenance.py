from __future__ import annotations

import json
import types

import pytest

from ml_lifecycle_platform.jobs.maintenance import (
    MaintenanceReport,
    main,
    run_maintenance_check,
)

pytestmark = pytest.mark.unit


def _record_alias_call(calls: list[str], tracking_uri: str, alias: str) -> str:
    calls.append(f"alias:{tracking_uri}:{alias}")
    return "7"


def _mock_runtime(
    *,
    tracking_uri: str = "https://mlflow.example",
    model_name: str = "breast_cancer_clf",
    log_level: str = "INFO",
) -> object:
    return types.SimpleNamespace(
        metadata=types.SimpleNamespace(tracking_uri=tracking_uri),
        model_name=model_name,
        log_level=log_level,
    )


def test_run_maintenance_check_verifies_prod_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    runtime = _mock_runtime()

    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.get_runtime_context",
        lambda: runtime,
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.configure_mlflow",
        lambda r: calls.append(f"configure:{type(r).__name__}"),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.verify_model_alias",
        lambda config: _record_alias_call(calls, config.tracking_uri, config.alias),
    )

    report = run_maintenance_check(alias="prod")

    assert report.tracking_uri == "https://mlflow.example"
    assert report.model_name == "breast_cancer_clf"
    assert report.alias == "prod"
    assert report.resolved_version == "7"
    assert report.alias_reachable is True
    assert calls == [
        "configure:SimpleNamespace",
        "alias:https://mlflow.example:prod",
    ]


def test_maintenance_main_prints_json(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.get_runtime_context",
        lambda: _mock_runtime(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.run_maintenance_check",
        lambda alias="prod": MaintenanceReport(
            tracking_uri="https://mlflow.example",
            model_name="breast_cancer_clf",
            alias=alias,
            resolved_version="9",
            alias_reachable=True,
        ),
    )

    main(["--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["alias"] == "prod"
    assert payload["resolved_version"] == "9"
