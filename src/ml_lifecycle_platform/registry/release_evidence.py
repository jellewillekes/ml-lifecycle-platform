from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mlflow.tracking import MlflowClient

from ml_lifecycle_platform.common.constants import (
    ART_MODEL_CARD_MD,
    ART_PROMOTION_DECISION_JSON,
    ART_RELEASE_MANIFEST_JSON,
    ART_ROLLBACK_TARGET_JSON,
    MLFLOW_ARTIFACT_PATH_RELEASES,
    TAG_MODEL_CARD_PATH,
    TAG_PROMOTION_DECISION_PATH,
    TAG_RELEASE_MANIFEST_PATH,
    TAG_RELEASE_REPORTS_PATH,
    TAG_ROLLBACK_TARGET_PATH,
)
from ml_lifecycle_platform.core.release_reports import (
    ReleaseManifest,
    ReleaseReportBundle,
)
from ml_lifecycle_platform.runtime.bootstrap import get_runtime_context

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmittedEvidencePaths:
    root_path: str
    promotion_decision_path: str
    release_manifest_path: str
    rollback_target_path: str
    model_card_path: str


def artifact_root(*, operation: str, model_name: str, model_version: str) -> str:
    safe_model_name = model_name.replace("/", "_")
    safe_version = model_version.replace("/", "_")
    return (
        f"{MLFLOW_ARTIFACT_PATH_RELEASES}/{operation}/{safe_model_name}/v{safe_version}"
    )


def emit_release_evidence(
    client: MlflowClient,
    *,
    source_run_id: str,
    operation: str,
    model_name: str,
    model_version: str,
    bundle: ReleaseReportBundle,
    tag_target_version: str | None = None,
    event_type: str | None = None,
) -> EmittedEvidencePaths:
    root_path = artifact_root(
        operation=operation,
        model_name=model_name,
        model_version=model_version,
    )
    with tempfile.TemporaryDirectory(prefix="release-evidence-") as tmpdir:
        tmp_path = Path(tmpdir)
        file_contents = bundle.file_contents()
        for file_name, content in file_contents.items():
            local_file = tmp_path / file_name
            local_file.write_bytes(content)
            client.log_artifact(
                run_id=source_run_id,
                local_path=str(local_file),
                artifact_path=root_path,
            )

    emitted = EmittedEvidencePaths(
        root_path=root_path,
        promotion_decision_path=f"{root_path}/{ART_PROMOTION_DECISION_JSON}",
        release_manifest_path=f"{root_path}/{ART_RELEASE_MANIFEST_JSON}",
        rollback_target_path=f"{root_path}/{ART_ROLLBACK_TARGET_JSON}",
        model_card_path=f"{root_path}/{ART_MODEL_CARD_MD}",
    )

    _mirror_local_bundle(root_path=root_path, file_contents=file_contents)

    if tag_target_version is not None:
        _set_report_tags(
            client=client,
            model_name=model_name,
            model_version=tag_target_version,
            emitted=emitted,
        )

    if event_type is not None:
        _append_event(
            event_type=event_type,
            bundle=bundle,
            emitted=emitted,
        )
    return emitted


def load_release_manifest(
    client: MlflowClient,
    *,
    source_run_id: str,
    manifest_path: str,
    work_dir: Path,
) -> ReleaseManifest:
    downloaded = Path(
        client.download_artifacts(
            run_id=source_run_id,
            path=manifest_path,
            dst_path=str(work_dir),
        )
    )
    return ReleaseManifest.from_json(downloaded.read_text(encoding="utf-8"))


def _mirror_local_bundle(*, root_path: str, file_contents: dict[str, bytes]) -> None:
    runtime = get_runtime_context()
    for file_name, content in file_contents.items():
        relative_path = f"{root_path}/{file_name}"
        try:
            runtime.artifact_store.write_bytes(relative_path, content)
        except Exception:
            logger.warning(
                "Could not mirror release evidence locally: %s", relative_path
            )


def _set_report_tags(
    client: MlflowClient,
    *,
    model_name: str,
    model_version: str,
    emitted: EmittedEvidencePaths,
) -> None:
    tags = {
        TAG_RELEASE_REPORTS_PATH: emitted.root_path,
        TAG_PROMOTION_DECISION_PATH: emitted.promotion_decision_path,
        TAG_RELEASE_MANIFEST_PATH: emitted.release_manifest_path,
        TAG_ROLLBACK_TARGET_PATH: emitted.rollback_target_path,
        TAG_MODEL_CARD_PATH: emitted.model_card_path,
    }
    for key, value in tags.items():
        client.set_model_version_tag(
            name=model_name,
            version=model_version,
            key=key,
            value=value,
        )


def _append_event(
    *,
    event_type: str,
    bundle: ReleaseReportBundle,
    emitted: EmittedEvidencePaths,
) -> None:
    runtime = get_runtime_context()
    payload: dict[str, Any] = {
        "model_name": bundle.manifest.model_name,
        "model_version": bundle.manifest.model_version,
        "operation": bundle.manifest.operation,
        "source_run_id": bundle.manifest.source_run_id,
        "current_prod_version": bundle.manifest.current_prod_version,
        "previous_prod_version": bundle.manifest.previous_prod_version,
        "result_status": bundle.manifest.result.status,
        "artifact_root": emitted.root_path,
    }
    try:
        runtime.event_store.append_event(event_type, payload)
    except Exception:
        logger.warning("Could not append release evidence event: %s", event_type)
