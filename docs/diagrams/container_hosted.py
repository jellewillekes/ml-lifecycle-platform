"""Container diagram — GCP staging, M4 target state.

Same internal structure as the local view; adapters swap to the GCP services
each port targets.  CI/CD is part of the picture here because hosted deploys
flow through GitHub Actions + OIDC under env-bound service accounts (UP-26).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from diagrams import Cluster, Diagram
from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.compute import Run
from diagrams.gcp.database import SQL
from diagrams.gcp.devtools import ContainerRegistry, Scheduler
from diagrams.gcp.security import Iam
from diagrams.gcp.storage import GCS
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.client import User
from diagrams.onprem.mlops import Mlflow
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.tracing import Tempo

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
    "Container — Hosted (M4, GCP staging)",
    filename=str(OUTPUT_DIR / "container_hosted"),
    outformat="svg",
    show=False,
    direction="TB",
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    operator = User("Operator")
    contributor = User("Contributor")

    with Cluster("CI/CD (UP-26 + UP-44)", graph_attr=cluster_attr("ci_cd")):
        actions = GithubActions("GitHub Actions\nenv: staging")
        oidc = Iam("Workload Identity\nFederation")
        registry = ContainerRegistry("Artifact Registry")
        actions >> signal("OIDC token\nsubject:env=staging") >> oidc
        (
            actions
            >> contract("image digest +\ncosign signature +\nSLSA provenance (UP-44)")
            >> registry
        )

    with Cluster(
        "Data sources (DataSource port)", graph_attr=cluster_attr("data_sources")
    ):
        scheduler = Scheduler("Cloud Scheduler")
        ingest_jobs = Run("Cloud Run Jobs\n(per-source ingestor)")
        binance = brand("Binance REST", "binance.png")
        coinbase = brand("Coinbase REST", "coinbase.png")
        open_meteo = brand("Open-Meteo REST", "open_meteo.png")
        scheduler >> signal("trigger\n(per-minute)") >> ingest_jobs
        ingest_jobs >> signal("HTTP poll") >> binance
        ingest_jobs >> signal("HTTP poll") >> coinbase
        ingest_jobs >> signal("HTTP poll") >> open_meteo

    with Cluster("Pipeline (Cloud Run Jobs)", graph_attr=cluster_attr("pipeline")):
        ingest = Run("ingest")
        validate_data = Run("validate_data\n(Pandera)")
        featurize = Run("featurize")
        train = Run("train")
        evaluate = Run("evaluate")
        validate_model = Run("validate_model")
        register = Run("register")
        ingest >> contract("RawRecord") >> validate_data
        validate_data >> contract("validation_report.json") >> featurize
        featurize >> plain() >> train
        train >> plain() >> evaluate
        evaluate >> plain() >> validate_model
        validate_model >> contract("model_validation_report.json") >> register

    with Cluster("Registry / control plane", graph_attr=cluster_attr("registry")):
        mlflow = Mlflow("MLflow server\n(Cloud Run)")
        sql = SQL("Cloud SQL\n(MLflow backend)")
        evidence = GCS("GCS bucket\nartifacts + release\nevidence")
        promote = Run("promote\n(env-aware gates +\nprogressive rollout)")
        rollback = Run("rollback")
        mlflow >> plain() >> sql
        mlflow >> plain() >> evidence

    with Cluster("Serving (Cloud Run service)", graph_attr=cluster_attr("serving")):
        api = Run("FastAPI\n/predict/{model}")
        model_store = Run("ModelStore\n(alias resolver)")
        emitter = Run("Prediction\nemitter")
        api >> plain() >> model_store
        api >> plain() >> emitter

    with Cluster("Event plane (cold path)", graph_attr=cluster_attr("event_plane")):
        sink = BigQuery("prediction_events_v1\npartitioned by\nDATE(event_time_ns)")
        drift_job = Run("drift batch job\n(UP-32)")
        feedback_job = Run("feedback ⋈\n(UP-34)")
        realized = BigQuery("realized_performance_v1")
        replay = Run("replay harness\n(UP-30)")
        retrain_eventarc = Scheduler(
            "Cloud Scheduler\n+ Eventarc filter\nRetrainTrigger"
        )
        dlq = BigQuery("prediction_events_dlq_v1")
        sink >> plain() >> drift_job
        sink >> plain() >> feedback_job
        feedback_job >> contract("realized_performance") >> realized
        sink >> plain() >> replay

    with Cluster(
        "Observability (self-hosted on GCE)", graph_attr=cluster_attr("observability")
    ):
        otel = brand("OTel Collector", "opentelemetry.png")
        vm = brand("VictoriaMetrics", "victoriametrics.png")
        tempo = Tempo("Tempo")
        prom = Prometheus("Prometheus\n(alertmanager)")
        grafana = Grafana("Grafana OSS\n(prod-tier alerts)")
        research_dash = Grafana(
            "Research-tier\ndiagnostic dashboard\n(UP-56, no paging)"
        )
        alert_router = Run("alert-router\n(Cloud Run,\nprod tier only)")
        otel >> plain() >> vm
        otel >> plain() >> tempo
        vm >> plain() >> grafana
        vm >> plain() >> research_dash
        tempo >> plain() >> grafana
        prom >> plain() >> alert_router

    contributor >> signal("git push") >> actions
    registry >> signal("deploy") >> mlflow
    registry >> signal("deploy") >> api
    registry >> signal("deploy") >> ingest

    operator >> signal("HTTPS predict\n+ IAM") >> api

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
    emitter >> signal("on 5xx → DLQ") >> dlq

    drift_job >> contract("drift_report.json") >> evidence
    sink >> contract("LabelEvent ⋈ PredictionEvent") >> feedback_job
    retrain_eventarc >> contract("RetrainTrigger") >> ingest

    drift_job >> contract("drift_report.json\n(UP-35 gate)") >> promote
    replay >> contract("replay_report.json\n(UP-35 gate)") >> promote
    api >> contract("health_check_status\n(UP-35 gate)") >> promote

    api >> signal("OTLP traces + metrics") >> otel
    register >> signal("OTLP traces + metrics") >> otel
    promote >> signal("OTLP traces + metrics") >> otel

    alert_router >> signal("auto-rollback on\nSLO burn (UP-35)") >> rollback
