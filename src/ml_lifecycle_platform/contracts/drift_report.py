"""Schema-versioned ``DriftReport`` artifact — the output of batch drift
(UP-32). Per feature it carries the KS statistic against the release baseline,
the mean/std deltas, and whether it breached the threshold. Written into release
evidence and consumed by promotion gates (UP-35)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ml_lifecycle_platform.common.constants import DRIFT_REPORT_SCHEMA_VERSION


@dataclass(frozen=True)
class FeatureDrift:
    feature: str
    ks_statistic: float
    mean_delta: float
    std_delta: float
    n_events: int
    flagged: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "ks_statistic": self.ks_statistic,
            "mean_delta": self.mean_delta,
            "std_delta": self.std_delta,
            "n_events": self.n_events,
            "flagged": self.flagged,
        }

    @staticmethod
    def from_dict(payload: Mapping[str, Any]) -> FeatureDrift:
        return FeatureDrift(
            feature=str(payload["feature"]),
            ks_statistic=float(payload["ks_statistic"]),
            mean_delta=float(payload["mean_delta"]),
            std_delta=float(payload["std_delta"]),
            n_events=int(payload["n_events"]),
            flagged=bool(payload["flagged"]),
        )


@dataclass(frozen=True)
class DriftReport:
    model_name: str
    model_version: str
    window_start_ns: int
    window_end_ns: int
    n_events: int
    threshold: float
    created_at: str
    features: dict[str, FeatureDrift]
    drifted: bool
    schema_version: str = DRIFT_REPORT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "window_start_ns": self.window_start_ns,
            "window_end_ns": self.window_end_ns,
            "n_events": self.n_events,
            "threshold": self.threshold,
            "created_at": self.created_at,
            "drifted": self.drifted,
            "features": {
                name: feature.to_dict() for name, feature in self.features.items()
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @staticmethod
    def from_dict(payload: Mapping[str, Any]) -> DriftReport:
        schema_version = str(payload.get("schema_version", ""))
        if schema_version != DRIFT_REPORT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported DriftReport schema_version={schema_version!r} "
                f"(expected {DRIFT_REPORT_SCHEMA_VERSION!r})"
            )
        raw_features = payload.get("features")
        if not isinstance(raw_features, dict):
            raise TypeError("DriftReport.features must be a dict")
        return DriftReport(
            model_name=str(payload["model_name"]),
            model_version=str(payload["model_version"]),
            window_start_ns=int(payload["window_start_ns"]),
            window_end_ns=int(payload["window_end_ns"]),
            n_events=int(payload["n_events"]),
            threshold=float(payload["threshold"]),
            created_at=str(payload["created_at"]),
            features={
                str(name): FeatureDrift.from_dict(value)
                for name, value in raw_features.items()
            },
            drifted=bool(payload["drifted"]),
        )

    @staticmethod
    def from_json(payload: str) -> DriftReport:
        return DriftReport.from_dict(json.loads(payload))
