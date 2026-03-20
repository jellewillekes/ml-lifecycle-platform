from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "verify_hosted_release_fixture.py"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "verify_hosted_release_fixture_script", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pytestmark = pytest.mark.unit


def test_main_returns_2_when_tracking_token_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    monkeypatch.delenv("MLFLOW_TRACKING_TOKEN", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_hosted_release_fixture.py",
            "--tracking-uri",
            "https://mlflow.example.run.app",
            "--model-name",
            "breast_cancer_clf",
            "--model-spec-path",
            "configs/models/breast_cancer_demo.yaml",
        ],
    )

    exit_code = module.main()

    assert exit_code == 2
    assert "MLFLOW_TRACKING_TOKEN must be set" in capsys.readouterr().err


def test_main_returns_0_when_release_fixture_is_ready(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    monkeypatch.setenv("MLFLOW_TRACKING_TOKEN", "token-123")
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_hosted_release_fixture.py",
            "--tracking-uri",
            "https://mlflow.example.run.app",
            "--model-name",
            "breast_cancer_clf",
            "--model-spec-path",
            "configs/models/breast_cancer_demo.yaml",
        ],
    )

    from ml_lifecycle_platform.ci import (
        hosted_release_fixture_verifier as verifier,
    )

    monkeypatch.setattr(
        verifier,
        "verify_release_fixture",
        lambda config: {
            "candidate_version": "4",
            "current_prod_version": "3",
            "rollback_target_version": "2",
            "rollback_resolution_source": "manifest",
            "current_prod_alias_version": "3",
        },
    )

    exit_code = module.main()

    assert exit_code == 0
    assert '"candidate_version": "4"' in capsys.readouterr().out
