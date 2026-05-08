"""Context diagram — local Compose runtime, M4 target state.

Shows actors, external systems, and the platform as a single box.  Edges
crossing the platform boundary carry the wire-level payload they transport.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from diagrams import Cluster, Diagram
from diagrams.onprem.client import User
from diagrams.onprem.container import Docker
from diagrams.onprem.mlops import Mlflow
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
    "Context — Local (M4)",
    filename=str(OUTPUT_DIR / "context_local"),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    with Cluster("Actors", graph_attr=cluster_attr("external")):
        operator = User("Operator\n(mlp CLI)")

    with Cluster("External data sources", graph_attr=cluster_attr("data_sources")):
        binance = brand("Binance\npublic REST", "binance.png")
        coinbase = brand("Coinbase\npublic REST", "coinbase.png")
        open_meteo = brand("Open-Meteo\npublic REST", "open_meteo.png")

    with Cluster(
        "ML Lifecycle Platform — Local (Compose)", graph_attr=cluster_attr("local")
    ):
        platform = Docker("docker compose\nstack")

    with Cluster("Outputs (local boundary)", graph_attr=cluster_attr("registry")):
        mlflow = Mlflow("MLflow\n(local)")
        storage = brand(
            "MinIO bucket\nLocalEventStore JSONL\n+ release evidence", "minio.png"
        )
        alerts = Grafana("Grafana OSS\n(visible only,\nno paging)")

    operator >> signal("CLI command") >> platform

    binance >> signal("HTTP+JSON kline") >> platform
    coinbase >> signal("HTTP+JSON candle") >> platform
    open_meteo >> signal("HTTP+JSON forecast / ERA5") >> platform

    platform >> contract("ModelVersion + alias") >> mlflow
    platform >> contract("PredictionEvent") >> storage
    platform >> contract("release_manifest.json") >> storage
    platform >> signal("alert (visible)") >> alerts
