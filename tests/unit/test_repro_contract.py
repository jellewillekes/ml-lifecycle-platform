from __future__ import annotations

import pytest

from ml_lifecycle_platform.contracts.repro_contract import ReproContract

pytestmark = pytest.mark.unit


def _valid_contract_payload() -> dict[str, object]:
    return {
        "schema_version": "repro_contract/v1",
        "training_run_id": "run-123",
        "model_name": "breast_cancer_clf",
        "git_sha": "deadbeef",
        "config_hash": "config-hash",
        "dataset_fingerprint": "dataset-fingerprint",
        "data_source_uri": "file:///tmp/data",
        "env_lock_hash": "lock-hash",
        "deterministic_seed": 42,
        "params": {
            "model_type": "logreg",
            "max_iter": 2000,
            "solver": "lbfgs",
            "class_weight": "balanced",
            "random_state": 42,
        },
        "train_dataset_artifact": "repro/inputs/train.csv",
        "test_dataset_artifact": "repro/inputs/test.csv",
        "preprocessor_artifact": "repro/inputs/preprocessor.joblib",
        "probe_inputs_artifact": "repro/inputs/probe_inputs.csv",
        "expected_predictions_artifact": "repro/outputs/expected_predictions.json",
        "uv_lock_artifact": "repro/env/uv.lock",
    }


def test_repro_contract_round_trips() -> None:
    payload = _valid_contract_payload()

    contract = ReproContract.from_dict(payload)

    assert contract.training_run_id == "run-123"
    assert contract.model_name == "breast_cancer_clf"
    assert contract.deterministic_seed == 42
    assert contract.params["random_state"] == 42
    assert ReproContract.from_json(contract.to_json()) == contract


def test_repro_contract_requires_complete_metadata() -> None:
    payload = _valid_contract_payload()
    payload["env_lock_hash"] = ""
    payload["params"] = {}

    with pytest.raises(ValueError) as exc:
        ReproContract.from_dict(payload)

    assert "env_lock_hash" in str(exc.value)
    assert "params" in str(exc.value)
