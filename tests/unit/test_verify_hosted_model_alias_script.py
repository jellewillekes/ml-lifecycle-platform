from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "verify_hosted_model_alias.py"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "verify_hosted_model_alias_script", SCRIPT_PATH
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
            "verify_hosted_model_alias.py",
            "--tracking-uri",
            "https://mlflow.example.run.app",
            "--model-name",
            "breast_cancer_clf",
        ],
    )

    exit_code = module.main()

    assert exit_code == 2
    assert "MLFLOW_TRACKING_TOKEN must be set" in capsys.readouterr().err


def test_main_returns_0_when_alias_verification_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    monkeypatch.setenv("MLFLOW_TRACKING_TOKEN", "token-123")
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_hosted_model_alias.py",
            "--tracking-uri",
            "https://mlflow.example.run.app",
            "--model-name",
            "breast_cancer_clf",
        ],
    )
    monkeypatch.setattr(module, "main", module.main)

    from ml_lifecycle_platform.ci import hosted_model_alias_verifier as verifier

    monkeypatch.setattr(
        verifier,
        "verify_model_alias",
        lambda config: "7",
    )

    exit_code = module.main()

    assert exit_code == 0
    assert "breast_cancer_clf@prod -> version=7" in capsys.readouterr().out
