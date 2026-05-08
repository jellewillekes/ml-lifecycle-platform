"""Deployment diagram (runtime) — GCP staging, M4 target state.

The data plane: where the platform actually runs traffic.  Cloud Run services
and Cloud Run Jobs, the Cloud SQL + GCS state behind MLflow, the BigQuery
event plane, and the self-hosted observability VM.  Schedulers are part of
the runtime view because they fire the Cloud Run Jobs.

Governance (GitHub Environments, WIF, service accounts, Secret Manager,
Artifact Registry deploy edges) lives in
[deployment_hosted_governance.py](deployment_hosted_governance.py) so this
diagram stays scannable.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from diagrams import Cluster, Diagram, Edge
from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.compute import GCE, Run
from diagrams.gcp.database import SQL
from diagrams.gcp.devtools import Scheduler
from diagrams.gcp.network import VPC
from diagrams.gcp.storage import GCS
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
    plain,
)

with Diagram(
    "Deployment — Hosted runtime (M4, GCP staging)",
    filename=str(OUTPUT_DIR / "deployment_hosted_runtime"),
    outformat="svg",
    show=False,
    direction="TB",
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    with Cluster("GCP project: fpl-project-jelle", graph_attr=cluster_attr("gcp")):
        with Cluster("region: europe-west1", graph_attr=cluster_attr("registry")):
            vpc = VPC("VPC\n+ Serverless VPC connector")

            with Cluster("State + artifacts", graph_attr=cluster_attr("registry")):
                sql = SQL("Cloud SQL\nPostgres\n(MLflow backend)")
                gcs_artifacts = GCS("gs://mlflow-artifacts")
                gcs_evidence = GCS("gs://release-evidence")
                gcs_obs = GCS("gs://observability-config")

            with Cluster("Cloud Run services", graph_attr=cluster_attr("serving")):
                run_mlflow = Mlflow("mlflow-server\n(Cloud Run)")
                run_serving = Run("serving\n(Cloud Run,\n/predict/{model})")
                run_alert_router = Run("alert-router\n(Cloud Run)")

            with Cluster(
                "Cloud Run Jobs (platform pipeline)",
                graph_attr=cluster_attr("pipeline"),
            ):
                job_ingest = Run("ingest\n(per-source)")
                job_pipeline = Run(
                    "validate_data\nfeaturize\ntrain\nevaluate\nvalidate_model\nregister"
                )
                job_promote = Run("promote\n(env-aware\ngates +\nprogressive\nrollout)")
                job_rollback = Run("rollback")
                job_drift = Run("drift batch")
                job_feedback = Run("feedback ⋈")
                job_replay = Run("replay harness")
                job_smoke = Run("platform-smoke\n(nightly)")

            with Cluster("Schedulers", graph_attr=cluster_attr("ci_cd")):
                sch_ingest = Scheduler("Cloud Scheduler\nper-source\n(every minute)")
                sch_drift = Scheduler("Cloud Scheduler\ndrift cadence")
                sch_feedback = Scheduler("Cloud Scheduler\nfeedback cadence")
                sch_retrain = Scheduler(
                    "Cloud Scheduler\n+ Eventarc filter\n(RetrainTrigger)"
                )
                sch_smoke = Scheduler("Cloud Scheduler\nnightly smoke")

            with Cluster(
                "Event plane (BigQuery dataset: mlp_events)",
                graph_attr=cluster_attr("event_plane"),
            ):
                bq_pred = BigQuery(
                    "prediction_events_v1\npartition: event_time_ns\ncluster: model, env"
                )
                bq_real = BigQuery("realized_performance_v1")
                bq_dlq = BigQuery("prediction_events_dlq_v1")

            with Cluster("Observability VM", graph_attr=cluster_attr("observability")):
                gce_obs = GCE("observability\nGCE VM")
                otel = brand("otel-collector", "opentelemetry.png")
                vm = brand("victoriametrics", "victoriametrics.png")
                tempo = Tempo("tempo")
                prom = Prometheus("prometheus")
                grafana = Grafana("grafana")
                gce_obs >> plain() >> otel
                otel >> plain() >> vm
                otel >> plain() >> tempo
                vm >> plain() >> grafana
                tempo >> plain() >> grafana
                prom >> plain() >> grafana

    vpc >> Edge(style="dotted", label="private IP") >> sql
    vpc >> Edge(style="dotted", label="VPC connector") >> run_mlflow
    vpc >> Edge(style="dotted", label="VPC connector") >> run_serving

    run_mlflow >> Edge(label="JDBC") >> sql
    run_mlflow >> Edge(label="S3 API") >> gcs_artifacts

    run_serving >> Edge(label="model pull") >> run_mlflow
    run_serving >> Edge(label="PredictionEvent\nstreaming insert") >> bq_pred
    run_serving >> Edge(label="DLQ on 5xx") >> bq_dlq
    run_serving >> Edge(label="OTLP", style="dashed") >> otel

    job_pipeline >> Edge(label="MLflow API") >> run_mlflow
    job_pipeline >> Edge(label="evidence write") >> gcs_evidence
    job_pipeline >> Edge(label="OTLP", style="dashed") >> otel

    job_promote >> Edge(label="alias mutation") >> run_mlflow
    (
        job_promote
        >> Edge(label="manifest +\nDriftBaseline +\nmodel_card.md")
        >> gcs_evidence
    )
    job_rollback >> Edge(label="alias mutation") >> run_mlflow

    job_drift >> Edge(label="BatchEventReader") >> bq_pred
    job_drift >> Edge(label="drift_report.json") >> gcs_evidence
    job_feedback >> Edge(label="LabelEvent ⋈") >> bq_pred
    job_feedback >> Edge(label="rows") >> bq_real
    job_replay >> Edge(label="BatchEventReader") >> bq_pred

    sch_ingest >> Edge(label="trigger") >> job_ingest
    sch_drift >> Edge(label="trigger") >> job_drift
    sch_feedback >> Edge(label="trigger") >> job_feedback
    sch_retrain >> Edge(label="trigger") >> job_pipeline
    sch_smoke >> Edge(label="trigger") >> job_smoke

    grafana >> Edge(label="alert webhook") >> run_alert_router
    run_alert_router >> Edge(label="auto-rollback\non SLO burn") >> job_rollback
