"""Container diagram — local Compose runtime, M4 target state.

The L2-storytelling view: every named service in the platform, every port
it crosses, and the contract that crosses with it.  Local adapters are the
OSS equivalents declared in the M4 portability rule.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from diagrams import Cluster, Diagram
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.onprem.container import Docker
from diagrams.onprem.database import Duckdb, Postgresql
from diagrams.onprem.mlops import Mlflow
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.tracing import Tempo
from diagrams.programming.framework import Fastapi
from diagrams.programming.language import Python

from _common import (
    EDGE_ATTR,
    GRAPH_ATTR,
    NODE_ATTR,
    OUTPUT_DIR,
    brand,
    cluster_attr,
    contract,
    plain,
    signal,
)

with Diagram(
    "Container — Local (M4)",
    filename=str(OUTPUT_DIR / "container_local"),
    outformat="svg",
    show=False,
    direction="TB",
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    operator = User("Operator")

    with Cluster(
        "Data sources (DataSource port)", graph_attr=cluster_attr("data_sources")
    ):
        cron = Server("Compose cron\n(APScheduler)")
        binance = brand("Binance REST", "binance.png")
        coinbase = brand("Coinbase REST", "coinbase.png")
        open_meteo = brand("Open-Meteo REST", "open_meteo.png")
        cron >> signal("HTTP poll") >> binance
        cron >> signal("HTTP poll") >> coinbase
        cron >> signal("HTTP poll") >> open_meteo

    with Cluster(
        "Pipeline (Compose service: pipeline)", graph_attr=cluster_attr("pipeline")
    ):
        ingest = Python("ingest")
        validate_data = Python("validate_data\n(Pandera)")
        featurize = Python("featurize")
        train = Python("train")
        evaluate = Python("evaluate")
        validate_model = Python("validate_model")
        register = Python("register")
        ingest >> contract("RawRecord") >> validate_data
        validate_data >> contract("validation_report.json") >> featurize
        featurize >> plain() >> train
        train >> plain() >> evaluate
        evaluate >> plain() >> validate_model
        validate_model >> contract("model_validation_report.json") >> register

    with Cluster("Registry / control plane", graph_attr=cluster_attr("registry")):
        mlflow = Mlflow("MLflow server\n(Compose)")
        pg = Postgresql("Postgres\n(MLflow backend)")
        evidence = brand("MinIO bucket\nartifacts + release\nevidence", "minio.png")
        promote = Python("promote\n(env-aware gates)")
        rollback = Python("rollback")
        mlflow >> plain() >> pg
        mlflow >> plain() >> evidence

    with Cluster(
        "Serving (Compose service: serving)", graph_attr=cluster_attr("serving")
    ):
        api = Fastapi("FastAPI\n/predict/{model}")
        model_store = Python("ModelStore\n(alias resolver)")
        emitter = Python("Prediction\nemitter")
        api >> plain() >> model_store
        api >> plain() >> emitter

    with Cluster("Event plane (cold path)", graph_attr=cluster_attr("event_plane")):
        sink = brand("LocalEventStore\n(JSONL on MinIO)", "minio.png")
        reader = Duckdb("DuckDB\n(BatchEventReader)")
        drift_job = Python("drift batch job\n(UP-32)")
        feedback_job = Python("feedback ⋈\n(UP-34)")
        realized = brand("realized_performance\n(parquet)", "minio.png")
        replay = Python("replay harness\n(UP-30)")
        retrain_cron = Server("Compose cron\nRetrainTrigger")
        sink >> plain() >> reader
        reader >> plain() >> drift_job
        reader >> plain() >> feedback_job
        feedback_job >> contract("realized_performance") >> realized
        reader >> plain() >> replay

    with Cluster("Observability stack", graph_attr=cluster_attr("observability")):
        otel = brand("OTel Collector", "opentelemetry.png")
        vm = brand("VictoriaMetrics", "victoriametrics.png")
        tempo = Tempo("Tempo")
        prom = Prometheus("Prometheus\n(alertmanager)")
        grafana = Grafana("Grafana OSS")
        alert_router = Docker("alert-router\n(visible only)")
        otel >> plain() >> vm
        otel >> plain() >> tempo
        vm >> plain() >> grafana
        tempo >> plain() >> grafana
        prom >> plain() >> alert_router

    operator >> signal("HTTPS predict") >> api

    binance >> contract("RawRecord (DataSource port)") >> ingest
    coinbase >> contract("RawRecord (DataSource port)") >> ingest
    open_meteo >> contract("RawRecord (DataSource port)") >> ingest

    (
        register
        >> contract(
            "ModelVersion\n+ dataset_fingerprint (UP-45)\n+ tier: research|staging|prod (UP-55)"
        )
        >> mlflow
    )
    promote >> contract("alias mutation") >> mlflow
    (
        promote
        >> contract("release_manifest.json\n+ DriftBaseline\n+ model_card.md")
        >> evidence
    )
    rollback >> contract("alias mutation") >> mlflow

    model_store >> contract("alias resolution") >> mlflow
    emitter >> contract("PredictionEvent\n(EventSink port)") >> sink

    drift_job >> contract("drift_report.json") >> evidence
    sink >> contract("LabelEvent ⋈ PredictionEvent") >> feedback_job
    retrain_cron >> contract("RetrainTrigger") >> ingest

    drift_job >> contract("drift_report.json\n(UP-35 gate)") >> promote
    replay >> contract("replay_report.json\n(UP-35 gate)") >> promote
    api >> contract("health_check_status\n(UP-35 gate)") >> promote

    api >> signal("OTLP traces + metrics") >> otel
    register >> signal("OTLP traces + metrics") >> otel
    promote >> signal("OTLP traces + metrics") >> otel
