"""Local `JobRunner` implementation that launches pipeline/registry steps
as `python -m <module>` subprocesses and returns the exit code."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Mapping, Sequence


class LocalJobRunner:
    """Run local control-plane steps as Python modules."""

    def __init__(self, python_executable: str | None = None) -> None:
        self._python_executable = python_executable or sys.executable

    @property
    def python_executable(self) -> str:
        return self._python_executable

    def run_module(
        self,
        module: str,
        *,
        args: Sequence[str] | None = None,
        env: Mapping[str, str] | None = None,
    ) -> int:
        command = [self._python_executable, "-m", module, *(args or ())]
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        completed = subprocess.run(command, check=False, env=merged_env)
        return int(completed.returncode)
