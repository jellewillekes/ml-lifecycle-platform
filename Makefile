SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

PROJECT_NAME := ml-lifecycle-platform
export GIT_SHA ?= $(shell git rev-parse HEAD 2>/dev/null || echo dev)

UV_PROJECT_DIR := .
DEPLOYMENTS_LOCAL_DIR ?= deployments/local
COMPOSE_FILE ?= $(DEPLOYMENTS_LOCAL_DIR)/docker-compose.yml
DEPLOYMENTS_GCP_TERRAFORM_DIR ?= deployments/gcp/terraform

UV ?= uv
DOCKER ?= docker
COMPOSE ?= $(DOCKER) compose -f $(COMPOSE_FILE)
TERRAFORM ?= terraform
MLP_ENV_NAME ?= local
MODEL ?=
MODEL_SPEC ?=

UV_RUN := $(UV) run --project $(UV_PROJECT_DIR)
MLP := $(UV_RUN) mlp --env $(MLP_ENV_NAME)
PY := $(UV_RUN) python

RUFF := $(PY) -m ruff
MYPY := $(PY) -m mypy
PYTEST := $(PY) -m pytest
PRECOMMIT := $(PY) -m pre_commit

TF_STATE_BUCKET ?= fpl-tf-state-jelle
TF_STATE_PREFIX ?= ml-lifecycle-platform/gcp/bootstrap
export TF_VAR_project_id ?= fpl-project-jelle
export TF_VAR_region ?= europe-west1

MYPY_CONFIG ?= mypy.ini
MYPY_PATHS ?= src tests
PYTEST_ARGS ?= -q

SVC_INFRA := postgres minio minio-init mlflow-server
SVC_IMAGES := mlflow-server pipeline promote rollback serving smoke

.PHONY: help
help:
	@echo ""
	@echo "$(PROJECT_NAME)"
	@echo ""
	@echo "Local:"
	@echo "  make check             format+lint+type+test"
	@echo "  make test              run fast unit tests (default local path)"
	@echo "  make test-unit         run hermetic unit tests"
	@echo "  make test-coverage     run unit tests with coverage report"
	@echo "  make test-integration  run local integration tests"
	@echo "  make test-all          run unit + integration tests"
	@echo "  make docs-check        validate handbook links and local doc paths"
	@echo "  make fix               format + safe autofix"
	@echo "  make precommit         run all hooks"
	@echo "  make install-hooks     install git hooks"
	@echo ""
	@echo "Docker:"
	@echo "  make up                start infra ($(SVC_INFRA))"
	@echo "  make down              stop + wipe volumes"
	@echo "  make logs              tail logs"
	@echo "  make build             build runtime images ($(SVC_IMAGES))"
	@echo "  make reset             down + no-cache rebuild"
	@echo "  make run-pipeline      train+eval+register (candidate)"
	@echo "  make reproduce         rebuild a registered model from the source training run"
	@echo "  make policy-check      dry-run promotion gate check (fails if blocked)"
	@echo "  make promote           candidate -> prod"
	@echo "  make promote-dry-run   show dry-run JSON (no side effects)"
	@echo "  make rollback-prod     prod -> previous prod"
	@echo "  make serve             start serving API"
	@echo "  make smoke-test        smoke tests against serving"
	@echo "  make test-e2e          run the golden path without automatic teardown"
	@echo "  make e2e               pipeline -> gate -> promote -> serve -> smoke"
	@echo "  make e2e-keep          like e2e, but keep stack up"
	@echo ""
	@echo "GCP Terraform:"
	@echo "  make terraform-gcp-fmt       terraform fmt -check for deployments/gcp/terraform"
	@echo "  make terraform-gcp-init      init remote state against $(TF_STATE_BUCKET)"
	@echo "  make terraform-gcp-plan      plan the GCP Terraform root"
	@echo "  make terraform-gcp-validate  validate the GCP Terraform root"
	@echo ""
	@echo "Housekeeping:"
	@echo "  make clean             remove local caches"
	@echo ""

.PHONY: check format lint type test test-unit test-coverage test-integration test-all docs-check fix
check: format lint type test
	@echo "✅ All checks passed"

format:
	@$(RUFF) format --check .

lint:
	@$(RUFF) check .

type:
	@$(MYPY) --no-incremental --config-file $(MYPY_CONFIG) $(MYPY_PATHS)

test:
	@$(MAKE) test-unit

test-unit:
	@$(PYTEST) $(PYTEST_ARGS) -m unit

test-coverage:
	@$(PYTEST) $(PYTEST_ARGS) -m unit \
		--cov=ml_lifecycle_platform \
		--cov-report=term-missing:skip-covered \
		--cov-report=xml:coverage.xml

test-integration:
	@$(PYTEST) $(PYTEST_ARGS) -m integration

test-all:
	@$(PYTEST) $(PYTEST_ARGS) -m "unit or integration"

docs-check:
	@$(PY) scripts/check_docs_links.py

fix:
	@$(RUFF) format .
	@$(RUFF) check --fix .

.PHONY: precommit install-hooks
precommit:
	@$(PRECOMMIT) run --all-files

install-hooks:
	@$(PRECOMMIT) install

.PHONY: up down logs build reset run-pipeline reproduce policy-check promote promote-dry-run rollback-prod serve smoke-test test-e2e e2e e2e-keep
up:
	@$(MLP) infra up

down:
	@$(MLP) infra down

logs:
	@$(MLP) infra logs

build:
	@$(MLP) infra build

reset: down
	@$(MLP) infra build --no-cache

run-pipeline:
	@set -euo pipefail; \
	model_spec="$${MODEL_SPEC:-$${MLP_MODEL_SPEC_PATH:-}}"; \
	if [[ -n "$$model_spec" ]]; then \
		$(MLP) pipeline run --model-spec "$$model_spec"; \
	else \
		$(MLP) pipeline run; \
	fi

reproduce:
	@set -euo pipefail; \
	model_name="$${MODEL:-$${MODEL_NAME:-breast_cancer_clf}}"; \
	report_path="$${REPORT:-reproduce_report.json}"; \
	if [[ -n "$${VERSION:-}" ]]; then \
		selector=(--model-version "$${VERSION}"); \
	elif [[ -n "$${ALIAS:-}" ]]; then \
		selector=(--alias "$${ALIAS}"); \
	else \
		echo "Set VERSION=<model-version> or ALIAS=<alias> for make reproduce."; \
		exit 2; \
	fi; \
	$(MLP) registry reproduce \
		--model-name "$$model_name" \
		"$${selector[@]}" \
		--report-path "$$report_path"

policy-check:
	@$(MLP) registry promote --dry-run --format json
	@echo "Policy gate passed (allowed=true)"

promote:
	@$(MLP) registry promote

promote-dry-run:
	@$(MLP) registry promote --dry-run --format json

rollback-prod:
	@$(MLP) registry rollback

serve:
	@set -euo pipefail; \
	model_name="$${MODEL:-$${MODEL_NAME:-}}"; \
	model_spec="$${MODEL_SPEC:-$${MLP_MODEL_SPEC_PATH:-}}"; \
	if [[ -n "$$model_name" && -n "$$model_spec" ]]; then \
		$(MLP) serve api --model-name "$$model_name" --model-spec "$$model_spec"; \
	elif [[ -n "$$model_name" ]]; then \
		$(MLP) serve api --model-name "$$model_name"; \
	elif [[ -n "$$model_spec" ]]; then \
		$(MLP) serve api --model-spec "$$model_spec"; \
	else \
		$(MLP) serve api; \
	fi

smoke-test:
	@set -euo pipefail; \
	model_name="$${MODEL:-$${MODEL_NAME:-}}"; \
	model_spec="$${MODEL_SPEC:-$${MLP_MODEL_SPEC_PATH:-}}"; \
	if [[ -n "$$model_name" && -n "$$model_spec" ]]; then \
		$(MLP) serve smoke --model-name "$$model_name" --model-spec "$$model_spec"; \
	elif [[ -n "$$model_name" ]]; then \
		$(MLP) serve smoke --model-name "$$model_name"; \
	elif [[ -n "$$model_spec" ]]; then \
		$(MLP) serve smoke --model-spec "$$model_spec"; \
	else \
		$(MLP) serve smoke; \
	fi

test-e2e:
	@$(MLP) e2e --keep-stack

e2e:
	@$(MLP) e2e

e2e-keep:
	@$(MLP) e2e --keep-stack
	@echo "E2E passed (stack kept up). Use 'make logs' or 'make down' when done."

.PHONY: terraform-gcp-fmt terraform-gcp-init terraform-gcp-plan terraform-gcp-validate
terraform-gcp-fmt:
	@$(TERRAFORM) -chdir=$(DEPLOYMENTS_GCP_TERRAFORM_DIR) fmt -check -recursive

terraform-gcp-init:
	@$(TERRAFORM) -chdir=$(DEPLOYMENTS_GCP_TERRAFORM_DIR) init \
		-backend-config="bucket=$(TF_STATE_BUCKET)" \
		-backend-config="prefix=$(TF_STATE_PREFIX)"

terraform-gcp-plan:
	@$(TERRAFORM) -chdir=$(DEPLOYMENTS_GCP_TERRAFORM_DIR) plan

terraform-gcp-validate:
	@$(TERRAFORM) -chdir=$(DEPLOYMENTS_GCP_TERRAFORM_DIR) validate

.PHONY: clean
clean:
	@rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__ || true
