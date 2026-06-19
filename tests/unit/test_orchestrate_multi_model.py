from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from ml_lifecycle_platform.core.model_specs import (
    discover_model_specs,
    resolve_spec_by_model_name,
)
from ml_lifecycle_platform.pipeline import orchestrate
from ml_lifecycle_platform.runtime.bootstrap import reset_runtime_context

pytestmark = pytest.mark.unit

_MODEL_ENV_KEYS = ("MLP_MODEL_SPEC_PATH", "MODEL_NAME", "EXPERIMENT_NAME")


@pytest.fixture(autouse=True)
def _restore_runtime() -> Iterator[None]:
    original = {key: os.environ.get(key) for key in _MODEL_ENV_KEYS}
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reset_runtime_context()


def _discovered_names() -> set[str]:
    return {spec.model_name for spec in discover_model_specs()}


def test_discover_finds_all_specs() -> None:
    assert {
        "binance_btc_1m",
        "breast_cancer_clf",
        "local_csv_binary_clf",
    } <= _discovered_names()


def test_resolve_by_model_name_hits_and_misses() -> None:
    assert resolve_spec_by_model_name("binance_btc_1m").model_name == "binance_btc_1m"
    with pytest.raises(ValueError, match="No model spec"):
        resolve_spec_by_model_name("does_not_exist")


def test_all_runs_every_model_with_isolated_experiment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, str]] = []

    def _fake_run_one_model() -> None:
        seen.append((os.environ["MODEL_NAME"], os.environ["EXPERIMENT_NAME"]))

    monkeypatch.setattr(orchestrate, "_run_one_model", _fake_run_one_model)
    orchestrate.main(["--all"])

    assert {name for name, _ in seen} == _discovered_names()
    # experiment is keyed on model name, so each model gets a clean history
    assert all(name == experiment for name, experiment in seen)


def test_failure_is_isolated_and_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    attempted: list[str] = []

    def _fake_run_one_model() -> None:
        name = os.environ["MODEL_NAME"]
        attempted.append(name)
        if name == "binance_btc_1m":
            raise RuntimeError("boom")

    monkeypatch.setattr(orchestrate, "_run_one_model", _fake_run_one_model)
    with pytest.raises(SystemExit, match="binance_btc_1m"):
        orchestrate.main(["--all"])

    # every model is attempted despite one failing
    assert set(attempted) == _discovered_names()


def test_model_flag_runs_single_model(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def _fake_run_one_model() -> None:
        seen.append(os.environ["MODEL_NAME"])

    monkeypatch.setattr(orchestrate, "_run_one_model", _fake_run_one_model)
    orchestrate.main(["--model", "binance_btc_1m"])

    assert seen == ["binance_btc_1m"]


def test_no_flags_runs_profile_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def _fake_run_one_model() -> None:
        calls.append(1)

    monkeypatch.setattr(orchestrate, "_run_one_model", _fake_run_one_model)
    orchestrate.main([])

    assert calls == [1]
