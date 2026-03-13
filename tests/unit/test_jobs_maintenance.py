from __future__ import annotations

import json

import pytest
import requests

from ml_lifecycle_platform.jobs.maintenance import (
    MaintenanceReport,
    main,
    run_maintenance_check,
)

pytestmark = pytest.mark.unit


def test_run_maintenance_check_verifies_http_and_prod_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.get_runtime_context",
        lambda: object(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.configure_mlflow",
        lambda runtime: calls.append(f"configure:{type(runtime).__name__}"),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.get_tracking_uri",
        lambda: "https://mlflow.example",
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.get_model_name",
        lambda: "breast_cancer_clf",
    )
    monkeypatch.setenv("MLFLOW_TRACKING_TOKEN", "token")
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.verify_http_reachable",
        lambda config: calls.append(f"http:{config.tracking_uri}"),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.verify_model_alias",
        lambda config: "7",
    )

    report = run_maintenance_check(alias="prod")

    assert report.tracking_uri == "https://mlflow.example"
    assert report.model_name == "breast_cancer_clf"
    assert report.alias == "prod"
    assert report.resolved_version == "7"
    assert report.http_reachable is True
    assert calls == ["configure:object", "http:https://mlflow.example"]


def test_run_maintenance_check_tolerates_http_probe_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.get_runtime_context",
        lambda: object(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.configure_mlflow",
        lambda runtime: None,
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.get_tracking_uri",
        lambda: "https://mlflow.example",
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.get_model_name",
        lambda: "breast_cancer_clf",
    )
    monkeypatch.setenv("MLFLOW_TRACKING_TOKEN", "token")
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.verify_http_reachable",
        lambda config: (_ for _ in ()).throw(requests.ReadTimeout("slow root")),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.verify_model_alias",
        lambda config: "7",
    )

    report = run_maintenance_check(alias="prod")

    assert report.resolved_version == "7"
    assert report.http_reachable is False


def test_maintenance_main_prints_json(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.get_log_level",
        lambda: "INFO",
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.jobs.maintenance.run_maintenance_check",
        lambda alias="prod": MaintenanceReport(
            tracking_uri="https://mlflow.example",
            model_name="breast_cancer_clf",
            alias=alias,
            resolved_version="9",
            http_reachable=True,
        ),
    )

    main(["--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["alias"] == "prod"
    assert payload["resolved_version"] == "9"
