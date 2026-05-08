"""Deployment diagram (governance) — GCP staging, M4 target state.

The control plane that gates deploys: GitHub Environments (UP-26), Workload
Identity Federation, env-bound service accounts, Secret Manager, and the
Artifact Registry that the runtime services pull images from.

The runtime side (Cloud Run, Cloud Run Jobs, BigQuery, observability VM)
lives in
[deployment_hosted_runtime.py](deployment_hosted_runtime.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from diagrams import Cluster, Diagram, Edge
from diagrams.gcp.compute import Run
from diagrams.gcp.devtools import ContainerRegistry
from diagrams.gcp.security import Iam, KeyManagementService
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.client import User
from diagrams.onprem.mlops import Mlflow

from _common import (
    EDGE_ATTR,
    GRAPH_ATTR,
    NODE_ATTR,
    OUTPUT_DIR,
    cluster_attr,
    plain,
)

with Diagram(
    "Deployment — Hosted governance (M4, GCP staging)",
    filename=str(OUTPUT_DIR / "deployment_hosted_governance"),
    outformat="svg",
    show=False,
    direction="TB",
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    with Cluster("GitHub", graph_attr=cluster_attr("ci_cd")):
        contributor = User("Contributor")
        actions = GithubActions("GitHub Actions\nworkflows")
        env_staging = Iam("env: staging\nscoped secrets")
        env_prod = Iam("env: prod\n(reserved, UP-26)")
        contributor >> Edge(label="git push") >> actions
        actions >> plain() >> env_staging
        actions >> plain() >> env_prod

    with Cluster("GCP project: fpl-project-jelle", graph_attr=cluster_attr("gcp")):
        wif = Iam("Workload Identity\nFederation pool")
        sa_staging = Iam("SA: mlp-ci-staging")
        sa_prod = Iam("SA: mlp-ci-prod\n(reserved)")
        sa_runtime = Iam("SA: serving runtime\n(scoped: BQ table,\nGCS evidence)")
        secrets = KeyManagementService(
            "Secret Manager\n(MLflow basic auth,\nrouter keys)"
        )
        ar = ContainerRegistry(
            "Artifact Registry\n(platform images:\npipeline, serving,\njobs, alert-router)"
        )

        wif >> plain() >> sa_staging
        wif >> plain() >> sa_prod

        with Cluster(
            "Runtime targets (deployed by CI)", graph_attr=cluster_attr("serving")
        ):
            run_mlflow = Mlflow("mlflow-server")
            run_serving = Run("serving")
            run_alert_router = Run("alert-router")
            jobs = Run(
                "Cloud Run Jobs\n(pipeline, promote,\nrollback, drift,\nfeedback, replay,\nsmoke)"
            )

    env_staging >> Edge(label="OIDC →\nimpersonate") >> wif
    env_prod >> Edge(label="OIDC (reserved)") >> wif

    sa_staging >> Edge(label="push image\n(cosign-signed,\nSLSA attested)") >> ar
    sa_staging >> Edge(label="deploy") >> run_mlflow
    sa_staging >> Edge(label="deploy") >> run_serving
    sa_staging >> Edge(label="deploy") >> run_alert_router
    sa_staging >> Edge(label="deploy") >> jobs

    ar >> Edge(label="image pull\n(digest-pinned)", style="dashed") >> run_mlflow
    ar >> Edge(label="image pull\n(digest-pinned)", style="dashed") >> run_serving
    ar >> Edge(label="image pull\n(digest-pinned)", style="dashed") >> run_alert_router
    ar >> Edge(label="image pull\n(digest-pinned)", style="dashed") >> jobs

    run_mlflow >> Edge(label="secret read") >> secrets
    run_alert_router >> Edge(label="secret read") >> secrets

    sa_runtime >> Edge(label="bound to") >> run_serving
