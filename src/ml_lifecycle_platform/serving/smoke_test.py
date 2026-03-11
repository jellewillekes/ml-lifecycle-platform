from __future__ import annotations

import os
import time
from typing import Any

import pandas as pd
import requests

from ml_lifecycle_platform.runtime.bootstrap import configure_mlflow

try:
    import mlflow  # type: ignore
except Exception:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]

SERVE_URL = os.getenv("SERVE_URL", "http://localhost:8000")
SERVE_BEARER_TOKEN = os.getenv("SERVE_BEARER_TOKEN", "").strip()
MODEL_NAME = os.getenv("MODEL_NAME", "").strip()


def _request_headers() -> dict[str, str]:
    if not SERVE_BEARER_TOKEN:
        return {}
    return {"Authorization": f"Bearer {SERVE_BEARER_TOKEN}"}


def _wait_for_service() -> None:
    """Wait for the service to become healthy."""
    last_status: int | None = None
    last_body: str | None = None

    for _ in range(30):
        try:
            r = requests.get(
                f"{SERVE_URL}/health", timeout=2, headers=_request_headers()
            )
            last_status = r.status_code
            last_body = r.text
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)

    raise RuntimeError(
        f"Service did not become healthy in time. last_status={last_status} last_body={last_body!r}"
    )


def _default_payload() -> dict[str, Any]:
    """Return a minimal valid prediction payload for the demo model."""
    return {
        "rows": [
            {
                "mean radius": 14.0,
                "mean texture": 20.0,
                "mean perimeter": 90.0,
                "mean area": 600.0,
                "mean smoothness": 0.10,
                "mean compactness": 0.13,
                "mean concavity": 0.10,
                "mean concave points": 0.05,
                "mean symmetry": 0.18,
                "mean fractal dimension": 0.06,
                "radius error": 0.30,
                "texture error": 1.10,
                "perimeter error": 2.50,
                "area error": 30.0,
                "smoothness error": 0.006,
                "compactness error": 0.020,
                "concavity error": 0.030,
                "concave points error": 0.010,
                "symmetry error": 0.020,
                "fractal dimension error": 0.003,
                "worst radius": 16.0,
                "worst texture": 26.0,
                "worst perimeter": 105.0,
                "worst area": 800.0,
                "worst smoothness": 0.14,
                "worst compactness": 0.30,
                "worst concavity": 0.35,
                "worst concave points": 0.12,
                "worst symmetry": 0.28,
                "worst fractal dimension": 0.08,
            }
        ]
    }


def _payload_from_model() -> dict[str, Any] | None:
    if not MODEL_NAME or mlflow is None:
        return None

    try:
        configure_mlflow()
        model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@prod")
        metadata = getattr(model, "metadata", None)
        if metadata is None:
            return None

        input_example = metadata.load_input_example()
        if not isinstance(input_example, pd.DataFrame) or input_example.empty:
            return None
        return {"rows": input_example.to_dict(orient="records")}
    except Exception:
        return None


def _payload() -> dict[str, Any]:
    return _payload_from_model() or _default_payload()


def _assert_prediction_response(body: dict[str, Any], *, expected_n: int) -> None:
    proba = body.get("proba")
    assert isinstance(proba, list) and len(proba) == expected_n, f"bad proba={proba!r}"

    for idx, value in enumerate(proba):
        assert isinstance(value, (float, int)), f"bad proba[{idx}]={value!r}"
        p_float = float(value)
        assert 0.0 <= p_float <= 1.0, f"proba[{idx}] out of range: {p_float}"

    metadata = body.get("metadata")
    assert isinstance(metadata, dict), f"bad metadata={metadata!r}"
    assert isinstance(metadata.get("contract_version"), str)


def _assert_model_metadata_response(body: dict[str, Any]) -> None:
    assert isinstance(body.get("model_name"), str)
    assert isinstance(body.get("contract_version"), str)
    assert isinstance(body.get("allow_unknown_fields"), bool)


def _assert_schema_metadata_response(body: dict[str, Any]) -> None:
    assert isinstance(body.get("contract_version"), str)
    features = body.get("features")
    assert isinstance(features, list) and features, f"bad features={features!r}"
    first_feature = features[0]
    assert isinstance(first_feature, dict)
    assert isinstance(first_feature.get("name"), str)
    assert isinstance(first_feature.get("dtype"), str)
    assert isinstance(first_feature.get("required"), bool)


def _check_metadata_endpoints() -> None:
    model_resp = requests.get(
        f"{SERVE_URL}/metadata/model", timeout=10, headers=_request_headers()
    )
    if model_resp.status_code >= 400:
        raise RuntimeError(
            f"[smoke] /metadata/model failed: {model_resp.status_code} detail={model_resp.text!r}"
        )
    _assert_model_metadata_response(model_resp.json())

    schema_resp = requests.get(
        f"{SERVE_URL}/metadata/schema", timeout=10, headers=_request_headers()
    )
    if schema_resp.status_code >= 400:
        raise RuntimeError(
            f"[smoke] /metadata/schema failed: {schema_resp.status_code} detail={schema_resp.text!r}"
        )
    _assert_schema_metadata_response(schema_resp.json())


def _call(mode: str, payload: dict[str, Any], *, required: bool) -> None:
    r = requests.post(
        f"{SERVE_URL}/predict?mode={mode}",
        json=payload,
        timeout=15,
        headers=_request_headers(),
    )

    # Many deployments only guarantee prod.
    if r.status_code == 503 and not required:
        print(f"[smoke] mode={mode} SKIP (503): {r.text[:300]!r}")
        return

    if r.status_code >= 400:
        # Keep CI failures actionable.
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        raise RuntimeError(
            f"[smoke] mode={mode} failed: {r.status_code} detail={detail!r}"
        )

    body = r.json()
    assert isinstance(body, dict)
    _assert_prediction_response(body, expected_n=len(payload["rows"]))
    print(f"[smoke] mode={mode} OK:", body)


def main() -> None:
    _wait_for_service()
    _check_metadata_endpoints()
    payload = _payload()

    _call("prod", payload, required=True)

    for mode in ["candidate", "shadow", "canary"]:
        _call(mode, payload, required=False)

    print("[smoke] ALL OK")


if __name__ == "__main__":
    main()
