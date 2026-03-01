from __future__ import annotations

import pytest

from ml_lifecycle_platform.common.config import get_experiment_name, get_model_name

pytestmark = pytest.mark.unit


def test_get_experiment_name_default() -> None:
    assert isinstance(get_experiment_name(), str)
    assert get_experiment_name() != ""


def test_get_model_name_default() -> None:
    assert isinstance(get_model_name(), str)
    assert get_model_name() != ""
