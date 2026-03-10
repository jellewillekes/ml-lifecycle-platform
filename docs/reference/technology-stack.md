# Technology Stack

This page lists the primary tools the platform uses today.

It does not list every package in `pyproject.toml`. It lists the tools a new engineer needs to understand to run, change, and debug the platform.

Companion references:

- [`configuration.md`](./configuration.md)
- [`gcp-resources.md`](./gcp-resources.md)
- [`release-contract.md`](./release-contract.md)

## Runtime and Serving

### FastAPI

What it is:
- Python web framework for HTTP APIs.

Why we use it:
- The serving API is small.
- We need clear request and response contracts, built-in validation, and straightforward health and metadata endpoints.

How it is used here:
- Defines `/livez`, `/readyz`, `/health`, `/metrics`, `/metadata/*`, and `/predict`.
- Runs the inference request path and response serialization.

Official docs:
- https://fastapi.tiangolo.com/

### Uvicorn

What it is:
- ASGI server for running FastAPI applications.

Why we use it:
- It is the standard simple runtime for FastAPI.
- It keeps the serving path boring for local development and container execution.

How it is used here:
- Runs the serving API process in the serving container and local serving flow.

Official docs:
- https://www.uvicorn.org/

### Pydantic

What it is:
- Python data validation and parsing library.

Why we use it:
- We need strict runtime and API contracts.
- Config failures and request/response failures should fail early with explicit errors.

How it is used here:
- Validates runtime profiles in `runtime/profile.py`.
- Validates serving request and response payloads in `serving/app.py`.
- Validates structured runtime events.

Official docs:
- https://docs.pydantic.dev/

### Prometheus Client

What it is:
- Python client library for Prometheus metrics.

Why we use it:
- The serving API needs cheap built-in request and latency metrics.

How it is used here:
- Exposes `/metrics`.
- Records request counts, latency, and shadow prediction difference metrics.

Official docs:
- https://prometheus.github.io/client_python/

## ML and Data

### pandas

What it is:
- DataFrame library for tabular data.

Why we use it:
- The local platform is tabular-model first.
- The training and evaluation flow is file-backed CSV and in-memory DataFrame based.

How it is used here:
- Loads source CSV data.
- Carries train/test datasets through ingest, featurize, train, evaluate, and reproduce flows.

Official docs:
- https://pandas.pydata.org/docs/

### NumPy

What it is:
- Core numerical array library for Python.

Why we use it:
- Scikit-learn metrics and prediction code rely on it.
- It keeps the numeric path standard and predictable.

How it is used here:
- Used in evaluation and prediction handling around model outputs and thresholds.

Official docs:
- https://numpy.org/doc/

### scikit-learn

What it is:
- Machine learning library for classical ML models and preprocessing.

Why we use it:
- M0 and early M1 focus on tabular binary classification.
- Logistic regression and simple preprocessing are enough to prove the platform path.

How it is used here:
- Loads the demo breast cancer dataset.
- Trains the logistic regression model.
- Runs preprocessing, metrics, signatures, and model serialization integration with MLflow.

Official docs:
- https://scikit-learn.org/stable/

### joblib

What it is:
- Python persistence library commonly used with scikit-learn objects.

Why we use it:
- Preprocessors need to be written and loaded as explicit artifacts.

How it is used here:
- Stores and loads the fitted preprocessor artifact used by training and reproduce flows.

Official docs:
- https://joblib.readthedocs.io/

### Pandera

What it is:
- DataFrame schema validation library.

Why we use it:
- Batch data boundaries need stronger checks before hosted rollout.
- We only want schema validation where data crosses important boundaries, not on every transform.

How it is used here:
- Validates labeled datasets at ingest, featurize, train, and evaluate boundaries.
- Ensures required features and label columns exist and match expected types.

Official docs:
- https://pandera.readthedocs.io/

### Matplotlib

What it is:
- Plotting library for Python.

Why we use it:
- Evaluation writes a ROC curve artifact as part of the report set.

How it is used here:
- Generates the ROC curve image during evaluation.

Official docs:
- https://matplotlib.org/stable/

## Storage and Control Plane

### MLflow

What it is:
- Experiment tracking, artifact storage integration, and model registry system.

Why we use it:
- It is the control plane for this platform.
- It gives one place for runs, model versions, aliases, artifacts, and release evidence.

How it is used here:
- Stores training, evaluation, promotion, rollback, and reproduce artifacts.
- Acts as the model registry and alias store.
- Stores release evidence bundles under `reports/releases/...`.

Official docs:
- https://mlflow.org/docs/latest/index.html

### PostgreSQL

What it is:
- Relational database.

Why we use it:
- The local MLflow server needs a real backend store instead of a file-backed metadata DB.
- Hosted MLflow staging also needs a real managed backend store.

How it is used here:
- Backs the local MLflow tracking server metadata store in Docker Compose.
- Will back hosted MLflow metadata in GCP through Cloud SQL Postgres.

Official docs:
- https://www.postgresql.org/docs/

### MinIO

What it is:
- S3-compatible object storage.

Why we use it:
- MLflow needs object storage for artifacts in the local runtime.
- MinIO gives an S3-compatible local path without introducing cloud dependencies.

How it is used here:
- Stores MLflow artifacts for the local Docker Compose stack.

Official docs:
- https://min.io/docs/minio/linux/index.html

### boto3

What it is:
- AWS SDK for Python.

Why we use it:
- The local stack uses S3-compatible object storage through MinIO.

How it is used here:
- Used indirectly through MLflow artifact access and local S3-compatible storage integration.

Official docs:
- https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

## Local Infrastructure

### Google Cloud Run

What it is:
- Managed container runtime for HTTP services and jobs.

Why we use it:
- It is the hosted runtime target for the first staging platform.
- It gives a boring deploy surface for MLflow first, then serving and jobs later.

How it is used here:
- Hosts the staged MLflow control plane in `UP-17`.
- Uses IAM-authenticated direct `run.app` access before any ALB is added.
- Uses Direct VPC egress to reach Cloud SQL private IP.

Official docs:
- https://cloud.google.com/run/docs/

### Terraform

What it is:
- Infrastructure as code tool.

Why we use it:
- Hosted infrastructure should be explicit, reviewable, and reproducible.
- Existing GCP project setup, foundation resources, and hosted follow-up work should live in committed config.

How it is used here:
- Initializes remote state in the existing GCS backend bucket.
- Manages required GCP project APIs for the shared hosted Terraform root in `deployments/gcp/terraform/`.
- Manages the current hosted foundation layer: Artifact Registry, buckets, placeholder secrets, service accounts, and GitHub OIDC federation.
- Manages the current hosted staging infra layer: staging network, private service access, Cloud SQL, and MLflow staging secrets.
- Will be extended in `M2` for Cloud Run services, jobs, and scheduler resources.

Official docs:
- https://developer.hashicorp.com/terraform/docs

### Google Cloud CLI

What it is:
- Command-line interface for Google Cloud.

Why we use it:
- Terraform uses ADC, so operators need a boring way to authenticate and verify project access.
- It is the fastest way to inspect foundation resources, Artifact Registry, Workload Identity Federation, and later hosted staging resources.

How it is used here:
- Establishes user auth and ADC for Terraform.
- Verifies access to the adopted project and Terraform backend bucket.
- Verifies hosted foundation resources and CI auth prerequisites during bring-up and debugging.

Official docs:
- https://cloud.google.com/sdk/docs

### Docker

What it is:
- Container runtime and image build tool.

Why we use it:
- The supported local golden path is containerized.
- Local reproducibility is much better with a fixed image and service layout.

How it is used here:
- Builds the platform, serving, smoke, promote, and rollback images.
- Runs the local MLflow, Postgres, MinIO, and serving stack.

Official docs:
- https://docs.docker.com/

### Docker Compose

What it is:
- Multi-container local orchestration for Docker.

Why we use it:
- The local platform needs a small multi-service stack.
- Compose is the simplest supported way to run that stack.

How it is used here:
- Starts and stops Postgres, MinIO, the MLflow server, and the serving API.
- Powers `make up`, `make down`, and the local E2E path.

Official docs:
- https://docs.docker.com/compose/

## Packaging and Configuration

### uv

What it is:
- Python package manager and virtual environment tool.

Why we use it:
- The repo needs a fast, locked, reproducible install path for local development, CI, and Docker images.

How it is used here:
- Installs dependencies from `uv.lock`.
- Creates local environments.
- Runs commands in CI and local development.
- Builds container environments with frozen dependencies.

Official docs:
- https://docs.astral.sh/uv/

### PyYAML

What it is:
- YAML parser for Python.

Why we use it:
- Runtime profiles and model specs are committed YAML files.

How it is used here:
- Loads `configs/env/*.yaml` runtime profiles.
- Loads `configs/models/*.yaml` model specs.

Official docs:
- https://pyyaml.org/wiki/PyYAMLDocumentation

## Quality and Testing

### pytest

What it is:
- Python test runner.

Why we use it:
- The repo already separates unit, integration, and E2E behavior through test markers and Make targets.

How it is used here:
- Runs unit and integration tests for runtime, pipeline, registry, and serving code.

Official docs:
- https://docs.pytest.org/

### pytest-cov

What it is:
- Coverage plugin for pytest.

Why we use it:
- Unit test coverage is part of CI output and regression checks.

How it is used here:
- Produces terminal and XML coverage reports in CI.

Official docs:
- https://pytest-cov.readthedocs.io/

### mypy

What it is:
- Static type checker for Python.

Why we use it:
- The repo relies on typed interfaces and explicit contracts.
- Type regressions are cheaper to catch before runtime.

How it is used here:
- Checks application and test code in CI and `make check`.

Official docs:
- https://mypy.readthedocs.io/

### Ruff

What it is:
- Python linter and formatter.

Why we use it:
- One fast tool for formatting and linting keeps local and CI feedback simple.

How it is used here:
- Enforces formatting and lint checks in local development and CI.

Official docs:
- https://docs.astral.sh/ruff/

### pre-commit

What it is:
- Framework for local Git hook automation.

Why we use it:
- Useful for running fast quality checks before code reaches CI.

How it is used here:
- Installed as a dev tool for local hook-based checks.

Official docs:
- https://pre-commit.com/

## CI, Release, and Security

### GitHub Actions

What it is:
- CI and automation platform built into GitHub.

Why we use it:
- The repo is already centered on GitHub for CI, release automation, and security checks.

How it is used here:
- Runs CI, nightly E2E, PR title validation, release workflows, and security scanning.

Official docs:
- https://docs.github.com/actions

### Codecov

What it is:
- Coverage reporting service.

Why we use it:
- CI already uploads unit test coverage and exposes it as a repository signal.

How it is used here:
- Receives coverage XML from the unit test lane.

Official docs:
- https://docs.codecov.com/docs

### release-please

What it is:
- Release automation tool from Google for conventional-commit based versioning and release PRs.

Why we use it:
- The repo uses conventional commits and automated release management for package versions and changelog updates.

How it is used here:
- Drives the GitHub release workflow and version bumps.

Official docs:
- https://github.com/googleapis/release-please

### CodeQL

What it is:
- GitHub-native static analysis for security issues and coding errors.

Why we use it:
- It catches classes of issues that the normal lint and test stack will not catch.

How it is used here:
- Runs as a dedicated GitHub Actions security workflow for Python code.

Official docs:
- https://codeql.github.com/docs/

### Gitleaks

What it is:
- Secret scanner for committed credentials and keys.

Why we use it:
- Public repositories need an explicit secret scanning check in CI.

How it is used here:
- Runs in CI against git history and uploads SARIF when allowed by the workflow token.

Official docs:
- https://github.com/gitleaks/gitleaks

### zizmor

What it is:
- GitHub Actions security linter.

Why we use it:
- Workflow configuration is part of the attack surface once CI and release automation become non-trivial.

How it is used here:
- Scans workflow files for unsafe patterns and reports findings through GitHub code scanning.

Official docs:
- https://docs.zizmor.sh/
