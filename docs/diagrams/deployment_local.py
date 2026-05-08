"""Deployment diagram — local Compose runtime, M4 target state.

Where it runs: containers, named networks, persistent volumes, host port
exposures.  One Compose project, two profiles — `default` for the platform
and `observability` for the metrics/tracing stack.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.compute import Server
from diagrams.onprem.container import Docker
from diagrams.onprem.database import Postgresql
from diagrams.onprem.mlops import Mlflow
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.tracing import Tempo
from diagrams.programming.framework import Fastapi

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
    "Deployment — Local (M4)",
    filename=str(OUTPUT_DIR / "deployment_local"),
    outformat="svg",
    show=False,
    direction="TB",
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    with Cluster(
        "docker compose project: ml-lifecycle-platform",
        graph_attr=cluster_attr("local"),
    ):
        with Cluster("network: mlp_default", graph_attr=cluster_attr("registry")):
            postgres = Postgresql("postgres:16\nvolume: pgdata")
            minio = brand("minio:latest\nvolume: miniodata\n:9000 :9001", "minio.png")
            mlflow = Mlflow("mlflow-server\n:5050 → :5000")

        with Cluster(
            "pipeline + jobs (default profile)", graph_attr=cluster_attr("pipeline")
        ):
            pipeline = Docker("pipeline\n(one-shot,\n--all models)")
            promote = Docker("promote\n(one-shot)")
            rollback = Docker("rollback\n(one-shot)")
            ingest_cron = Server("ingest cron\n(per-source\nAPScheduler)")
            drift_job = Docker("drift batch\n(scheduled)")
            feedback_job = Docker("feedback ⋈\n(scheduled)")
            replay_job = Docker("replay harness\n(on-demand)")
            retrain_cron = Server("retrain cron\n(RetrainTrigger)")

        with Cluster("serving (default profile)", graph_attr=cluster_attr("serving")):
            serving = Fastapi("serving\n:8080")
            smoke = Docker("smoke\n(one-shot,\nlocal verification)")

        with Cluster(
            "observability profile (opt-in)", graph_attr=cluster_attr("observability")
        ):
            otel = brand("otel-collector\n:4317 :4318", "opentelemetry.png")
            vm = brand("victoriametrics\n:8428", "victoriametrics.png")
            tempo = Tempo("tempo\n:3200")
            prom = Prometheus("prometheus\n+ alertmanager")
            grafana = Grafana("grafana\n:3000")
            alert_router = Docker("alert-router\n:8081")

    mlflow >> Edge(label="JDBC") >> postgres
    mlflow >> Edge(label="S3 API") >> minio
    pipeline >> Edge(label="MLflow API") >> mlflow
    pipeline >> Edge(label="S3 API") >> minio
    promote >> Edge(label="MLflow API") >> mlflow
    rollback >> Edge(label="MLflow API") >> mlflow
    serving >> Edge(label="MLflow API") >> mlflow
    serving >> Edge(label="JSONL append") >> minio
    smoke >> Edge(label="HTTP") >> serving

    ingest_cron >> Edge(label="parquet write") >> minio
    ingest_cron >> Edge(label="trigger") >> pipeline
    drift_job >> Edge(label="DuckDB scan") >> minio
    feedback_job >> Edge(label="DuckDB scan") >> minio
    replay_job >> Edge(label="DuckDB scan") >> minio
    retrain_cron >> Edge(label="trigger") >> pipeline

    serving >> Edge(label="OTLP", style="dashed") >> otel
    pipeline >> Edge(label="OTLP", style="dashed") >> otel
    promote >> Edge(label="OTLP", style="dashed") >> otel
    otel >> plain() >> vm
    otel >> plain() >> tempo
    vm >> plain() >> grafana
    tempo >> plain() >> grafana
    prom >> plain() >> alert_router
