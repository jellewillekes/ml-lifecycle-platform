"""Context diagram — GCP staging, M4 target state.

Same actors as the local view, but the platform boundary now sits inside a
GCP project: outputs land in BigQuery, GCS, MLflow on Cloud Run, and the
self-hosted Grafana stack on a GCE VM.  CI is in scope here because hosted
deploys are gated on GitHub Actions + OIDC.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from diagrams import Cluster, Diagram
from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.compute import Run
from diagrams.gcp.storage import GCS
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.client import User
from diagrams.onprem.monitoring import Grafana

from _common import (
    EDGE_ATTR,
    GRAPH_ATTR,
    NODE_ATTR,
    OUTPUT_DIR,
    brand,
    cluster_attr,
    contract,
    signal,
)

with Diagram(
    "Context — Hosted (M4, GCP staging)",
    filename=str(OUTPUT_DIR / "context_hosted"),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    with Cluster("Actors", graph_attr=cluster_attr("external")):
        operator = User("Operator\n(mlp CLI / dashboards)")
        contributor = User("Contributor")

    with Cluster("External data sources", graph_attr=cluster_attr("data_sources")):
        binance = brand("Binance\npublic REST", "binance.png")
        coinbase = brand("Coinbase\npublic REST", "coinbase.png")
        open_meteo = brand("Open-Meteo\npublic REST", "open_meteo.png")

    with Cluster("CI/CD", graph_attr=cluster_attr("ci_cd")):
        actions = GithubActions("GitHub Actions\n(env: staging / prod)")

    with Cluster("ML Lifecycle Platform — GCP staging", graph_attr=cluster_attr("gcp")):
        platform = Run("Cloud Run\nservices + jobs")

    with Cluster("Outputs (GCP boundary)", graph_attr=cluster_attr("registry")):
        mlflow = Run("MLflow\n(Cloud Run)")
        events = BigQuery("prediction_events_v1\n(BigQuery)")
        evidence = GCS("Release evidence\n(GCS bucket)")
        observability = Grafana("Self-hosted Grafana\n(GCE VM)")
        alert_router = Run("alert-router\n(Cloud Run)")

    contributor >> signal("git push / OIDC") >> actions
    actions >> contract("image digest + plan") >> platform

    operator >> signal("HTTPS predict\n+ IAM") >> platform

    binance >> signal("HTTP+JSON kline") >> platform
    coinbase >> signal("HTTP+JSON candle") >> platform
    open_meteo >> signal("HTTP+JSON forecast / ERA5") >> platform

    platform >> contract("ModelVersion + alias") >> mlflow
    platform >> contract("PredictionEvent") >> events
    platform >> contract("release_manifest.json") >> evidence
    platform >> signal("OTLP metrics + traces") >> observability
    observability >> signal("alert webhook") >> alert_router
