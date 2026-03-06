from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _dockerfile_python_mm(dockerfile_text: str) -> str:
    match = re.search(
        r"^FROM python:(?P<version>\d+\.\d+)-slim AS base$",
        dockerfile_text,
        flags=re.MULTILINE,
    )
    assert match is not None, (
        "Dockerfile must contain a base image line for python:X.Y-slim AS base."
    )
    return match.group("version")


def _pyproject_supported_mm(pyproject_text: str) -> str:
    data = tomllib.loads(pyproject_text)
    requires_python = str(data["project"]["requires-python"])
    match = re.search(r">=\s*(?P<version>\d+\.\d+)", requires_python)
    assert match is not None, (
        "pyproject.toml project.requires-python must include a >=X.Y constraint."
    )
    return match.group("version")


def test_docker_runtime_python_matches_pyproject_supported_version() -> None:
    root = _repo_root()
    dockerfile_text = (root / "Dockerfile").read_text(encoding="utf-8")
    pyproject_text = (root / "pyproject.toml").read_text(encoding="utf-8")

    assert _dockerfile_python_mm(dockerfile_text) == _pyproject_supported_mm(
        pyproject_text
    )
