from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ml_lifecycle_platform.common.constants import REPRO_CONTRACT_SCHEMA_VERSION


@dataclass(frozen=True)
class ReproContract:
    training_run_id: str
    model_name: str
    git_sha: str
    config_hash: str
    dataset_fingerprint: str
    data_source_uri: str
    env_lock_hash: str
    deterministic_seed: int
    params: dict[str, Any]
    train_dataset_artifact: str
    test_dataset_artifact: str
    preprocessor_artifact: str
    probe_inputs_artifact: str
    expected_predictions_artifact: str
    uv_lock_artifact: str
    schema_version: str = REPRO_CONTRACT_SCHEMA_VERSION

    def missing_fields(self) -> list[str]:
        missing: list[str] = []

        def _is_blank(value: str) -> bool:
            return not str(value).strip()

        if _is_blank(self.training_run_id):
            missing.append("training_run_id")
        if _is_blank(self.model_name):
            missing.append("model_name")
        if _is_blank(self.git_sha):
            missing.append("git_sha")
        if _is_blank(self.config_hash):
            missing.append("config_hash")
        if _is_blank(self.dataset_fingerprint):
            missing.append("dataset_fingerprint")
        if _is_blank(self.data_source_uri):
            missing.append("data_source_uri")
        if _is_blank(self.env_lock_hash):
            missing.append("env_lock_hash")
        if self.deterministic_seed is None:
            missing.append("deterministic_seed")
        if not self.params:
            missing.append("params")
        if _is_blank(self.train_dataset_artifact):
            missing.append("train_dataset_artifact")
        if _is_blank(self.test_dataset_artifact):
            missing.append("test_dataset_artifact")
        if _is_blank(self.preprocessor_artifact):
            missing.append("preprocessor_artifact")
        if _is_blank(self.probe_inputs_artifact):
            missing.append("probe_inputs_artifact")
        if _is_blank(self.expected_predictions_artifact):
            missing.append("expected_predictions_artifact")
        if _is_blank(self.uv_lock_artifact):
            missing.append("uv_lock_artifact")
        return missing

    def validate(self) -> None:
        missing = self.missing_fields()
        if missing:
            raise ValueError(f"Incomplete repro contract: missing {', '.join(missing)}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "training_run_id": self.training_run_id,
            "model_name": self.model_name,
            "git_sha": self.git_sha,
            "config_hash": self.config_hash,
            "dataset_fingerprint": self.dataset_fingerprint,
            "data_source_uri": self.data_source_uri,
            "env_lock_hash": self.env_lock_hash,
            "deterministic_seed": self.deterministic_seed,
            "params": self.params,
            "train_dataset_artifact": self.train_dataset_artifact,
            "test_dataset_artifact": self.test_dataset_artifact,
            "preprocessor_artifact": self.preprocessor_artifact,
            "probe_inputs_artifact": self.probe_inputs_artifact,
            "expected_predictions_artifact": self.expected_predictions_artifact,
            "uv_lock_artifact": self.uv_lock_artifact,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> ReproContract:
        schema_version = str(payload.get("schema_version", ""))
        if schema_version != REPRO_CONTRACT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported ReproContract schema_version={schema_version!r} "
                f"(expected {REPRO_CONTRACT_SCHEMA_VERSION!r})"
            )

        contract = ReproContract(
            training_run_id=str(payload.get("training_run_id", "")),
            model_name=str(payload.get("model_name", "")),
            git_sha=str(payload.get("git_sha", "")),
            config_hash=str(payload.get("config_hash", "")),
            dataset_fingerprint=str(payload.get("dataset_fingerprint", "")),
            data_source_uri=str(payload.get("data_source_uri", "")),
            env_lock_hash=str(payload.get("env_lock_hash", "")),
            deterministic_seed=int(payload["deterministic_seed"]),
            params=dict(payload.get("params", {})),
            train_dataset_artifact=str(payload.get("train_dataset_artifact", "")),
            test_dataset_artifact=str(payload.get("test_dataset_artifact", "")),
            preprocessor_artifact=str(payload.get("preprocessor_artifact", "")),
            probe_inputs_artifact=str(payload.get("probe_inputs_artifact", "")),
            expected_predictions_artifact=str(
                payload.get("expected_predictions_artifact", "")
            ),
            uv_lock_artifact=str(payload.get("uv_lock_artifact", "")),
        )
        contract.validate()
        return contract

    @staticmethod
    def from_json(payload: str) -> ReproContract:
        return ReproContract.from_dict(json.loads(payload))
