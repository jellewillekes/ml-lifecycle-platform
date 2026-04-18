from __future__ import annotations

from types import SimpleNamespace

import pytest
from requests.exceptions import ReadTimeout

from ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier import (
    MlflowStagingVerificationConfig,
    VerificationError,
    verify_http_reachable,
    verify_staging,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.time.sleep",
        lambda _seconds: None,
    )


def test_verify_staging_checks_http_and_mlflow_roundtrip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []

    class _FakeClient:
        def create_experiment(self, name: str) -> str:
            calls.append(("create_experiment", (name,)))
            return "123"

        def list_artifacts(self, run_id: str) -> list[SimpleNamespace]:
            calls.append(("list_artifacts", (run_id,)))
            return [SimpleNamespace(path="smoke.txt")]

    class _RunContext:
        def __enter__(self) -> SimpleNamespace:
            calls.append(("start_run", ("123", "staging-smoke")))
            return SimpleNamespace(info=SimpleNamespace(run_id="run-1"))

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

    class _Response:
        status_code = 200

    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.requests.get",
        lambda *args, **kwargs: _Response(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.mlflow.set_tracking_uri",
        lambda uri: calls.append(("set_tracking_uri", (uri,))),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.mlflow.get_experiment_by_name",
        lambda name: None,
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.MlflowClient",
        lambda: _FakeClient(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.mlflow.start_run",
        lambda experiment_id, run_name: _RunContext(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.mlflow.log_param",
        lambda key, value: calls.append(("log_param", (key, value))),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.mlflow.log_artifact",
        lambda path: calls.append(("log_artifact", (path,))),
    )

    config = MlflowStagingVerificationConfig(
        tracking_uri="https://mlflow.example.run.app",
        tracking_token="token",
        experiment_name="smoke-exp",
    )

    run_id = verify_staging(config)

    assert run_id == "run-1"
    assert ("set_tracking_uri", ("https://mlflow.example.run.app",)) in calls
    assert ("create_experiment", ("smoke-exp",)) in calls
    assert ("log_param", ("smoke_check", "true")) in calls
    assert any(name == "log_artifact" for name, _ in calls)


def test_verify_http_reachable_fails_fast_on_auth_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Response:
        status_code = 403

    calls: list[str] = []

    def _fake_get(url: str, *args: object, **kwargs: object) -> _Response:
        del args, kwargs
        calls.append(url)
        return _Response()

    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.requests.get",
        _fake_get,
    )

    config = MlflowStagingVerificationConfig(
        tracking_uri="https://mlflow.example.run.app",
        tracking_token="token",
        experiment_name="smoke-exp",
    )

    with pytest.raises(VerificationError, match="check tracking token"):
        verify_http_reachable(config)

    assert calls == ["https://mlflow.example.run.app/health"]


def test_verify_http_reachable_retries_on_timeout_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Ok:
        status_code = 200

    responses: list[_Ok | ReadTimeout] = [
        ReadTimeout("cold start"),
        ReadTimeout("cold start"),
        _Ok(),
    ]

    def _fake_get(*args: object, **kwargs: object) -> _Ok:
        del args, kwargs
        item = responses.pop(0)
        if isinstance(item, ReadTimeout):
            raise item
        return item

    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.requests.get",
        _fake_get,
    )

    config = MlflowStagingVerificationConfig(
        tracking_uri="https://mlflow.example.run.app",
        tracking_token="token",
        experiment_name="smoke-exp",
    )

    verify_http_reachable(config)

    assert responses == []


def test_verify_http_reachable_raises_after_retries_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _always_timeout(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise ReadTimeout("cold start")

    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.requests.get",
        _always_timeout,
    )

    config = MlflowStagingVerificationConfig(
        tracking_uri="https://mlflow.example.run.app",
        tracking_token="token",
        experiment_name="smoke-exp",
    )

    with pytest.raises(VerificationError, match="unreachable after"):
        verify_http_reachable(config)


def test_verify_staging_fails_when_artifact_roundtrip_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeClient:
        def create_experiment(self, name: str) -> str:
            del name
            return "123"

        def list_artifacts(self, run_id: str) -> list[SimpleNamespace]:
            del run_id
            return []

    class _RunContext:
        def __enter__(self) -> SimpleNamespace:
            return SimpleNamespace(info=SimpleNamespace(run_id="run-1"))

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

    class _Response:
        status_code = 200

    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.requests.get",
        lambda *args, **kwargs: _Response(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.mlflow.set_tracking_uri",
        lambda uri: None,
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.mlflow.get_experiment_by_name",
        lambda name: None,
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.MlflowClient",
        lambda: _FakeClient(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.mlflow.start_run",
        lambda experiment_id, run_name: _RunContext(),
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.mlflow.log_param",
        lambda key, value: None,
    )
    monkeypatch.setattr(
        "ml_lifecycle_platform.hosted_ci.mlflow_staging_verifier.mlflow.log_artifact",
        lambda path: None,
    )

    config = MlflowStagingVerificationConfig(
        tracking_uri="https://mlflow.example.run.app",
        tracking_token="token",
        experiment_name="smoke-exp",
    )

    with pytest.raises(VerificationError, match="artifact roundtrip"):
        verify_staging(config)
