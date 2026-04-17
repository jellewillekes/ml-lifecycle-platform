from __future__ import annotations

import json
import types

import pytest

from ml_lifecycle_platform.registry.rollback import main

pytestmark = pytest.mark.unit


class _Version:
    def __init__(self, version: str, tags: dict[str, str] | None = None) -> None:
        self.version = version
        self.tags = tags or {}


class _Client:
    def __init__(self, current: _Version, target: _Version) -> None:
        self._current = current
        self._target = target

    def get_model_version_by_alias(self, model_name: str, alias: str) -> _Version:
        assert model_name == "breast_cancer_clf"
        assert alias == "prod"
        return self._current

    def get_model_version(self, model_name: str, version: str) -> _Version:
        assert model_name == "breast_cancer_clf"
        assert version == self._target.version
        return self._target


def _mock_runtime(log_level: str = "INFO") -> object:
    return types.SimpleNamespace(log_level=log_level, model_name="breast_cancer_clf")


def test_rollback_main_dry_run_prints_ready_plan(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    current = _Version("5", tags={"previous_prod_version": "4"})
    target = _Version("4")
    monkeypatch.setattr(
        "ml_lifecycle_platform.registry.rollback.get_runtime_context",
        lambda: _mock_runtime(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.registry.rollback.mlflow_client",
        lambda: _Client(current, target),
    )

    with pytest.raises(SystemExit) as error:
        main(["--model-name", "breast_cancer_clf", "--dry-run", "--format", "json"])

    assert error.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready"
    assert payload["current_prod_version"] == "5"
    assert payload["target_version"] == "4"


def test_rollback_main_dry_run_blocks_without_previous_prod(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    current = _Version("5", tags={})
    target = _Version("4")
    monkeypatch.setattr(
        "ml_lifecycle_platform.registry.rollback.get_runtime_context",
        lambda: _mock_runtime(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.registry.rollback.mlflow_client",
        lambda: _Client(current, target),
    )

    with pytest.raises(SystemExit) as error:
        main(["--model-name", "breast_cancer_clf", "--dry-run", "--format", "json"])

    assert error.value.code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "blocked"
    assert "previous prod recorded" in payload["reason"]
