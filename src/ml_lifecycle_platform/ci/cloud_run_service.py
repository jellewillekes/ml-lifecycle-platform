from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping


class CloudRunServiceError(RuntimeError):
    """Raised when a Cloud Run service contract cannot be resolved."""


@dataclass(frozen=True)
class CloudRunServiceContract:
    service_name: str
    service_url: str
    service_image: str


def _run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def _run_gcloud_json(args: list[str], *, expectation: str) -> Any:
    completed = _run_command(args)
    if completed.returncode != 0:
        stderr = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "unknown gcloud error"
        )
        raise CloudRunServiceError(f"{expectation}: {stderr}")

    stdout = completed.stdout.strip()
    if not stdout:
        raise CloudRunServiceError(f"{expectation}: gcloud returned no JSON output.")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as error:
        raise CloudRunServiceError(
            f"{expectation}: gcloud returned invalid JSON: {error.msg}."
        ) from error


def _mapping(value: Any, *, field_name: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    raise CloudRunServiceError(f"Cloud Run service payload is missing '{field_name}'.")


def _non_empty_string(value: Any, *, field_name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise CloudRunServiceError(f"Cloud Run service payload is missing '{field_name}'.")


def _first_container(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    spec = _mapping(payload.get("spec"), field_name="spec")
    template = _mapping(spec.get("template"), field_name="spec.template")

    containers = template.get("containers")
    field_name = "spec.template.containers[0]"
    if not isinstance(containers, list) or not containers:
        template_spec = template.get("spec")
        if isinstance(template_spec, Mapping):
            containers = template_spec.get("containers")
            field_name = "spec.template.spec.containers[0]"

    if not isinstance(containers, list) or not containers:
        raise CloudRunServiceError(
            "Cloud Run service payload is missing "
            "'spec.template.containers[0]' or 'spec.template.spec.containers[0]'."
        )

    first_container = containers[0]
    if not isinstance(first_container, Mapping):
        raise CloudRunServiceError(
            f"Cloud Run service payload is missing '{field_name}'."
        )

    return first_container


def parse_cloud_run_service_contract(
    payload: Mapping[str, Any], *, expected_service_name: str | None = None
) -> CloudRunServiceContract:
    metadata = _mapping(payload.get("metadata"), field_name="metadata")
    status = _mapping(payload.get("status"), field_name="status")
    first_container = _first_container(payload)

    service_name = _non_empty_string(metadata.get("name"), field_name="metadata.name")
    if expected_service_name is not None and service_name != expected_service_name:
        raise CloudRunServiceError(
            f"Expected Cloud Run service '{expected_service_name}', got '{service_name}'."
        )

    return CloudRunServiceContract(
        service_name=service_name,
        service_url=_non_empty_string(status.get("url"), field_name="status.url"),
        service_image=_non_empty_string(
            first_container.get("image"),
            field_name="spec.template.containers[0].image",
        ),
    )


def resolve_cloud_run_service_contract(
    *, project_id: str, region: str, service_name: str
) -> CloudRunServiceContract:
    payload = _run_gcloud_json(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            service_name,
            "--region",
            region,
            "--project",
            project_id,
            "--format=json",
        ],
        expectation=f"failed to describe Cloud Run service '{service_name}'",
    )
    if not isinstance(payload, Mapping):
        raise CloudRunServiceError(
            "Cloud Run service lookup returned a non-object JSON payload."
        )
    return parse_cloud_run_service_contract(payload, expected_service_name=service_name)


def write_github_output(path: Path, contract: CloudRunServiceContract) -> None:
    path.write_text(
        "\n".join(
            [
                f"service_name={contract.service_name}",
                f"service_url={contract.service_url}",
                f"service_image={contract.service_image}",
                "",
            ]
        ),
        encoding="utf-8",
    )
