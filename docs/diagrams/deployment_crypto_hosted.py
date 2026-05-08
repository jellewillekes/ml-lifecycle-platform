"""Deployment diagram — M6 low-latency BTC 15s path, GCP hosted-only.

A genuinely different topology from the M4 view: the M4 platform stays in
Cloud Run, but the tick path runs on a pinned GCE VM with Memorystore in
the same zone, Pub/Sub for the hot stream, and the existing BigQuery sink
re-used as the cold path.  Edges carry the contract crossing them; hops
on the predict path carry the target latency budget enforced by UP-60.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from diagrams import Cluster, Diagram, Edge
from diagrams.gcp.analytics import BigQuery, PubSub
from diagrams.gcp.compute import GCE, Run
from diagrams.gcp.database import Memorystore
from diagrams.gcp.network import VPC
from diagrams.onprem.client import User
from diagrams.onprem.monitoring import Grafana

from _common import (
    EDGE_ATTR,
    GRAPH_ATTR,
    NODE_ATTR,
    OUTPUT_DIR,
    brand,
    cluster_attr,
    plain,
)

with Diagram(
    "Deployment — Crypto path (M6, GCP hosted)",
    filename=str(OUTPUT_DIR / "deployment_crypto_hosted"),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    with Cluster("Internal consumer", graph_attr=cluster_attr("external")):
        consumer = User("Trading client\n(gRPC,\ninternal only)")

    binance_ws = brand("Binance\nWebSocket\n(depth + trades + klines)", "binance.png")

    with Cluster(
        "GCP project — region: europe-west1, zone: -b", graph_attr=cluster_attr("gcp")
    ):
        vpc = VPC("VPC\nprivate networking\n(same zone)")

        with Cluster("GCE VM (pinned, zone -b)", graph_attr=cluster_attr("serving")):
            ingestor = GCE("ws-ingestor\n(uvloop, UP-61)")
            fast = GCE("serving/fast\n(gRPC, uvloop,\nmsgpack, UP-65)")
            decision = GCE("decision emitter\n(UP-67)")
            ingestor >> Edge(label="feature update\np99 < 5ms (UP-60)") >> fast
            fast >> plain() >> decision

        with Cluster("Online feature store", graph_attr=cluster_attr("event_plane")):
            redis = Memorystore("Memorystore\nRedis\n(same zone)")

        vpc >> Edge(style="dotted", label="private peering") >> fast
        vpc >> Edge(style="dotted", label="private peering") >> redis

        with Cluster("Hot stream (UP-29b)", graph_attr=cluster_attr("event_plane")):
            t_ticks = PubSub("topic: ticks")
            t_pred = PubSub("topic: predictions")
            t_dec = PubSub("topic: decisions")
            t_ticks_dlq = PubSub("ticks DLQ")
            t_pred_dlq = PubSub("predictions DLQ")
            t_dec_dlq = PubSub("decisions DLQ")
            t_ticks >> Edge(style="dashed", label="DLQ") >> t_ticks_dlq
            t_pred >> Edge(style="dashed", label="DLQ") >> t_pred_dlq
            t_dec >> Edge(style="dashed", label="DLQ") >> t_dec_dlq

        with Cluster(
            "Cold path re-used (M4 BigQuery)", graph_attr=cluster_attr("registry")
        ):
            bq_pred = BigQuery("prediction_events_v1\n(re-used from M4)")

        with Cluster(
            "Observability (M4 stack)", graph_attr=cluster_attr("observability")
        ):
            otel = brand("OTel Collector\n(latency histograms)", "opentelemetry.png")
            latency_dash = Grafana("Grafana\nlatency waterfall\n(UP-60)")
            chaos = Run("chaos runner\n(UP-69)")
            otel >> plain() >> latency_dash

    binance_ws >> Edge(label="TickEvent\n(UP-62)") >> ingestor

    ingestor >> Edge(label="online write") >> redis
    fast >> Edge(label="online read\np99 < 1ms") >> redis

    ingestor >> Edge(label="TickEvent\n(EventStream port)") >> t_ticks
    fast >> Edge(label="PredictionEvent\nfire-and-forget") >> t_pred
    decision >> Edge(label="DecisionEvent\n(UP-67)") >> t_dec

    consumer >> Edge(label="gRPC predict\np99 ≤ 35ms (UP-60)") >> fast

    (
        t_pred
        >> Edge(
            label="PredictionEvent\nstreaming insert\n(cold path re-use)",
            style="dashed",
        )
        >> bq_pred
    )

    ingestor >> Edge(label="OTLP", style="dashed") >> otel
    fast >> Edge(label="OTLP", style="dashed") >> otel
    decision >> Edge(label="OTLP", style="dashed") >> otel

    (
        chaos
        >> Edge(
            label="WS disconnect /\nRedis stall /\nstream slow-consumer /\nclock skew >100ms\n(UP-69)"
        )
        >> ingestor
    )
