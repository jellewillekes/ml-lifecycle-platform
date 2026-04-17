from __future__ import annotations

import pytest

from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context

pytestmark = pytest.mark.unit


def test_experiment_name_default() -> None:
    ctx = get_runtime_context()
    assert isinstance(ctx.experiment_name, str)
    assert ctx.experiment_name != ""


def test_model_name_default() -> None:
    ctx = get_runtime_context()
    assert isinstance(ctx.model_name, str)
    assert ctx.model_name != ""
