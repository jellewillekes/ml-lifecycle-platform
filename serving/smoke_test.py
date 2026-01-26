from __future__ import annotations

import os
import time
from typing import Any

import requests

SERVE_URL = os.getenv("SERVE_URL", "http://localhost:8000")


def _wait_for_service() -> None:
    """Wait until the service becomes healthy or raise."""
    for _ in range(30):
        try:
            r = requests.get(f"{SERVE_URL}/health", timeout=2)
            if r.status_code == 200:
                return
        except requests.RequestException:
            # Service not up yet; retry.
            pass
        time.sleep(1)
    raise RuntimeError("Service did not become healthy in time.")


def _payload() -> dict[str, Any]:
    """Return a minimal valid prediction payload."""
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


def _call(mode: str) -> None:
    r = requests.post(f"{SERVE_URL}/predict?mode={mode}", json=_payload(), timeout=10)
    r.raise_for_status()

    body = r.json()
    assert isinstance(body, dict)

    proba = body.get("proba")
    assert isinstance(proba, list) and len(proba) == 1

    p = proba[0]
    assert isinstance(p, (float, int))
    p_float = float(p)

    assert 0.0 <= p_float <= 1.0
    print(f"[smoke] mode={mode} OK:", body)


def main() -> None:
    _wait_for_service()

    for mode in ["prod", "candidate", "shadow", "canary"]:
        _call(mode)

    print("[smoke] ALL OK")


if __name__ == "__main__":
    main()
