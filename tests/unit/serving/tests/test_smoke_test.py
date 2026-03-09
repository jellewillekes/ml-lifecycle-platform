from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

import ml_lifecycle_platform.serving.smoke_test as smoke_test

pytestmark = pytest.mark.unit


class _FakeMetadata:
    def __init__(self, input_example: Any) -> None:
        self._input_example = input_example

    def load_input_example(self) -> Any:
        return self._input_example


class _FakeModel:
    def __init__(self, input_example: Any) -> None:
        self.metadata = _FakeMetadata(input_example)


class _FakePyFunc:
    def __init__(self, input_example: Any) -> None:
        self._input_example = input_example

    def load_model(self, model_uri: str) -> _FakeModel:
        assert model_uri == "models:/local_csv_binary_clf@prod"
        return _FakeModel(self._input_example)


class _FakeMlflow:
    def __init__(self, input_example: Any) -> None:
        self.pyfunc = _FakePyFunc(input_example)


def test_payload_uses_model_input_example(monkeypatch: pytest.MonkeyPatch) -> None:
    input_example = pd.DataFrame(
        [{"mean_radius": 20.29, "mean_texture": 14.34, "mean_perimeter": 135.1}]
    )
    monkeypatch.setattr(smoke_test, "MODEL_NAME", "local_csv_binary_clf")
    monkeypatch.setattr(smoke_test, "mlflow", _FakeMlflow(input_example))
    monkeypatch.setattr(smoke_test, "configure_mlflow", lambda: None)

    payload = smoke_test._payload()

    assert payload == {"rows": input_example.to_dict(orient="records")}


def test_payload_falls_back_to_demo_row_on_model_metadata_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(smoke_test, "MODEL_NAME", "local_csv_binary_clf")
    monkeypatch.setattr(smoke_test, "mlflow", None)

    payload = smoke_test._payload()

    assert list(payload) == ["rows"]
    assert len(payload["rows"]) == 1
    assert "mean radius" in payload["rows"][0]
