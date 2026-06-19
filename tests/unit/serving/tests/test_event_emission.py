from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch
from starlette.testclient import TestClient

from ml_lifecycle_platform.contracts.prediction_event import PredictionEvent
from ml_lifecycle_platform.serving.model_store import get_model_store
from ml_lifecycle_platform.serving.settings import get_settings

pytestmark = pytest.mark.unit


def _valid_row() -> dict[str, float]:
    return {
        "mean_radius": 17.99,
        "mean_texture": 10.38,
        "mean_perimeter": 122.8,
        "mean_area": 1001.0,
        "mean_smoothness": 0.1184,
    }


@pytest.fixture()
def jsonl_client(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> Iterator[tuple[TestClient, Path]]:
    """Serve in UNIT_TESTING mode with the JSONL event sink enabled."""
    events_path = tmp_path / "prediction-events.jsonl"
    monkeypatch.setenv("UNIT_TESTING", "1")
    monkeypatch.setenv("MODEL_NAME", "local_csv_binary_clf")
    monkeypatch.setenv(
        "MLP_MODEL_SPEC_PATH", "configs/models/local_csv_binary_classifier.yaml"
    )
    monkeypatch.setenv("MLP_EVENT_SINK", "jsonl")
    monkeypatch.setenv("MLP_EVENT_JSONL_PATH", str(events_path))
    monkeypatch.setenv("MLP_ENV", "local")
    monkeypatch.setenv("GIT_SHA", "testsha")

    get_settings.cache_clear()
    import ml_lifecycle_platform.serving.app as app_module

    get_model_store().reset()
    app_module._load_feature_contract.cache_clear()

    try:
        with TestClient(app_module.app) as test_client:
            yield test_client, events_path
    finally:
        get_settings.cache_clear()


def _wait_for_lines(path: Path, timeout_s: float = 5.0) -> list[str]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if path.exists():
            lines = [line for line in path.read_text().splitlines() if line]
            if lines:
                return lines
        time.sleep(0.05)
    return []


def test_predict_emits_prediction_event(
    jsonl_client: tuple[TestClient, Path],
) -> None:
    client, events_path = jsonl_client
    r = client.post("/predict", json={"rows": [_valid_row()]})
    assert r.status_code == 200, r.text

    lines = _wait_for_lines(events_path)
    assert len(lines) == 1
    event = PredictionEvent.from_dict(json.loads(lines[0]))
    assert event.corr_id
    assert event.model_ref.model_name == "local_csv_binary_clf"
    assert event.envelope.env == "local"
    assert event.envelope.git_sha == "testsha"
    assert set(event.features) == set(_valid_row())
