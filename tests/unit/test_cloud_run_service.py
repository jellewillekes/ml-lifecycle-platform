from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from ml_lifecycle_platform.ci.cloud_run_service import (
    CloudRunServiceContract,
    CloudRunServiceError,
    parse_cloud_run_service_contract,
    resolve_cloud_run_service_contract,
    write_github_output,
)

pytestmark = pytest.mark.unit


def _completed(
    stdout: str, *, returncode: int = 0, stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["gcloud"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _service_payload(
    *,
    service_name: str = "mlp-serving-staging",
    service_url: str = "https://mlp-serving-staging.run.app",
    service_image: str = "europe-west1-docker.pkg.dev/project/mlp-images/serving@sha256:abc",
) -> dict[str, object]:
    return {
        "metadata": {"name": service_name},
        "status": {"url": service_url},
        "spec": {
            "template": {
                "containers": [{"image": service_image}],
            }
        },
    }


def test_parse_cloud_run_service_contract_returns_expected_values() -> None:
    contract = parse_cloud_run_service_contract(
        _service_payload(),
        expected_service_name="mlp-serving-staging",
    )

    assert contract.service_name == "mlp-serving-staging"
    assert contract.service_url == "https://mlp-serving-staging.run.app"
    assert contract.service_image.endswith("sha256:abc")


def test_parse_cloud_run_service_contract_rejects_missing_status_url() -> None:
    payload = _service_payload(service_url="")

    with pytest.raises(CloudRunServiceError, match="status.url"):
        parse_cloud_run_service_contract(
            payload,
            expected_service_name="mlp-serving-staging",
        )


def test_resolve_cloud_run_service_contract_uses_expected_gcloud_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(
        args: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        calls.append(args)
        return _completed(
            """
            {
              "metadata": {"name": "mlp-serving-staging"},
              "status": {"url": "https://mlp-serving-staging.run.app"},
              "spec": {
                "template": {
                  "containers": [
                    {"image": "europe-west1-docker.pkg.dev/project/mlp-images/serving@sha256:abc"}
                  ]
                }
              }
            }
            """
        )

    monkeypatch.setattr(
        "ml_lifecycle_platform.ci.cloud_run_service.subprocess.run",
        fake_run,
    )

    contract = resolve_cloud_run_service_contract(
        project_id="fpl-project-jelle",
        region="europe-west1",
        service_name="mlp-serving-staging",
    )

    assert contract == CloudRunServiceContract(
        service_name="mlp-serving-staging",
        service_url="https://mlp-serving-staging.run.app",
        service_image="europe-west1-docker.pkg.dev/project/mlp-images/serving@sha256:abc",
    )
    assert calls == [
        [
            "gcloud",
            "run",
            "services",
            "describe",
            "mlp-serving-staging",
            "--region",
            "europe-west1",
            "--project",
            "fpl-project-jelle",
            "--format=json",
        ]
    ]


def test_resolve_cloud_run_service_contract_raises_actionable_error_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        args: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del args, check, capture_output, text
        return _completed("{not-json")

    monkeypatch.setattr(
        "ml_lifecycle_platform.ci.cloud_run_service.subprocess.run",
        fake_run,
    )

    with pytest.raises(CloudRunServiceError, match="invalid JSON"):
        resolve_cloud_run_service_contract(
            project_id="fpl-project-jelle",
            region="europe-west1",
            service_name="mlp-serving-staging",
        )


def test_write_github_output_writes_expected_keys(tmp_path: Path) -> None:
    output_path = tmp_path / "github-output.txt"

    write_github_output(
        output_path,
        CloudRunServiceContract(
            service_name="mlp-serving-staging",
            service_url="https://mlp-serving-staging.run.app",
            service_image="europe-west1-docker.pkg.dev/project/mlp-images/serving@sha256:abc",
        ),
    )

    assert output_path.read_text(encoding="utf-8") == (
        "service_name=mlp-serving-staging\n"
        "service_url=https://mlp-serving-staging.run.app\n"
        "service_image=europe-west1-docker.pkg.dev/project/mlp-images/serving@sha256:abc\n"
    )
