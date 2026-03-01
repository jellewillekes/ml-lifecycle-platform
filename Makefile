SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

PROJECT_NAME := ml-lifecycle-platform

UV_PROJECT_DIR := .

UV ?= uv
DOCKER ?= docker
COMPOSE ?= $(DOCKER) compose

UV_RUN := $(UV) run --project $(UV_PROJECT_DIR)
PY := $(UV_RUN) python

RUFF := $(PY) -m ruff
MYPY := $(PY) -m mypy
PYTEST := $(PY) -m pytest
PRECOMMIT := $(PY) -m pre_commit

MYPY_CONFIG ?= mypy.ini
MYPY_PATHS ?= src tests
PYTEST_ARGS ?= -q

SVC_INFRA := postgres minio minio-init mlflow-server
SVC_IMAGES := mlflow-server pipeline promote rollback serving smoke

# ---- helpers ----
define assert_allowed_true
	out="$$($(COMPOSE) run --rm --use-aliases promote python -m ml_lifecycle_platform.registry.promote --dry-run --format json)"; \
	echo "$$out"; \
	if command -v jq >/dev/null 2>&1; then \
		echo "$$out" | jq -e '.allowed == true' >/dev/null; \
	else \
		echo "$$out" | grep -Eq '"allowed"[[:space:]]*:[[:space:]]*true'; \
	fi
endef

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
	@echo "Housekeeping:"
	@echo "  make clean             remove local caches"
	@echo ""

.PHONY: check format lint type test test-unit test-coverage test-integration test-all fix
check: format lint type test
	@echo "✅ All checks passed"

format:
	@$(RUFF) format --check .

lint:
	@$(RUFF) check .

type:
	@$(MYPY) --config-file $(MYPY_CONFIG) $(MYPY_PATHS)

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

fix:
	@$(RUFF) format .
	@$(RUFF) check --fix .

.PHONY: precommit install-hooks
precommit:
	@$(PRECOMMIT) run --all-files

install-hooks:
	@$(PRECOMMIT) install

.PHONY: up down logs build reset run-pipeline policy-check promote promote-dry-run rollback-prod serve smoke-test test-e2e e2e e2e-keep
up:
	@$(COMPOSE) up -d $(SVC_INFRA)
	@echo "MLflow UI: http://localhost:5050"
	@echo "MinIO Console: http://localhost:9001 (user: minioadmin / pass: minioadmin)"

down:
	@$(COMPOSE) down -v

logs:
	@$(COMPOSE) logs -f --tail=200

build:
	@$(COMPOSE) build $(SVC_IMAGES)

reset: down
	@$(COMPOSE) build --no-cache $(SVC_IMAGES)

run-pipeline: build
	@$(COMPOSE) run --rm --use-aliases pipeline

policy-check: build
	@$(assert_allowed_true)
	@echo "✅ Policy gate passed (allowed=true)"

promote: build
	@$(COMPOSE) run --rm --use-aliases promote

promote-dry-run: build
	@$(COMPOSE) run --rm --use-aliases promote python -m ml_lifecycle_platform.registry.promote --dry-run --format json

rollback-prod: build
	@$(COMPOSE) run --rm --use-aliases rollback

serve: build
	@$(COMPOSE) up -d --build serving
	@echo "Serving API: http://localhost:8000 (GET /health, POST /predict)"

smoke-test: build
	@$(COMPOSE) run --rm --use-aliases --build smoke

test-e2e: build
	@set -euo pipefail; \
	$(COMPOSE) up -d $(SVC_INFRA); \
	$(COMPOSE) run --rm --use-aliases pipeline; \
	$(assert_allowed_true); \
	$(COMPOSE) run --rm --use-aliases promote; \
	$(COMPOSE) up -d --build serving; \
	$(COMPOSE) run --rm --use-aliases --build smoke

e2e:
	@set -euo pipefail; \
	cleanup() { $(COMPOSE) down -v; }; \
	trap cleanup EXIT; \
	$(MAKE) test-e2e; \
	echo "✅ E2E passed"

e2e-keep:
	@set -euo pipefail; \
	$(MAKE) test-e2e; \
	echo "✅ E2E passed (stack kept up). Use 'make logs' or 'make down' when done."

.PHONY: clean
clean:
	@rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__ || true
