.DEFAULT_GOAL := help
SHELL := /bin/bash
PYTHON := python3
UVICORN := uvicorn
HOST := 0.0.0.0

# =============================================================================
# Help
# =============================================================================
.PHONY: help
help: ## Show this help message
	@echo "EcoSupplyAI - Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Installation
# =============================================================================
.PHONY: install
install: ## Install production dependencies
	pip install -e .

.PHONY: dev-install
dev-install: ## Install all dependencies including dev tools
	pip install -e ".[dev]"
	pre-commit install

# =============================================================================
# Code Quality
# =============================================================================
.PHONY: lint
lint: ## Run ruff linter
	ruff check .

.PHONY: format
format: ## Auto-format code with ruff
	ruff format .
	ruff check --fix .

.PHONY: type-check
type-check: ## Run mypy static type analysis
	mypy src/

# =============================================================================
# Testing
# =============================================================================
.PHONY: test
test: ## Run unit tests
	pytest tests/ -m "not integration and not e2e and not slow and not eval"

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	pytest tests/ \
		-m "not integration and not e2e and not slow and not eval" \
		--cov=src --cov-report=term-missing --cov-report=html:htmlcov

# =============================================================================
# Run Services (local development)
# =============================================================================
.PHONY: run-gateway
run-gateway: ## Start API Gateway (port 8000)
	$(UVICORN) src.api_gateway.main:app --host $(HOST) --port 8000 --reload

.PHONY: run-chat-agent
run-chat-agent: ## Start Chat Agent service (port 8001)
	$(UVICORN) src.chat_agent.service:app --host $(HOST) --port 8001 --reload

.PHONY: run-rag
run-rag: ## Start RAG Pipeline service (port 8002)
	$(UVICORN) src.rag_pipeline.service:app --host $(HOST) --port 8002 --reload

.PHONY: run-scoring
run-scoring: ## Start Scoring service (port 8003)
	$(UVICORN) src.scoring_service.service:app --host $(HOST) --port 8003 --reload

.PHONY: run-forecast
run-forecast: ## Start Forecast service (port 8004)
	$(UVICORN) src.forecast_service.service:app --host $(HOST) --port 8004 --reload

.PHONY: run-content-gen
run-content-gen: ## Start Content Generator (port 8005)
	$(UVICORN) src.content_generator.service:app --host $(HOST) --port 8005 --reload

.PHONY: run-workflow
run-workflow: ## Start Workflow Engine (port 8006)
	$(UVICORN) src.workflow_engine.service:app --host $(HOST) --port 8006 --reload

.PHONY: run-mcp-server
run-mcp-server: ## Start MCP Server (stdio transport)
	$(PYTHON) -m src.mcp_server.server

# =============================================================================
# Docker
# =============================================================================
.PHONY: docker-build
docker-build: ## Build all Docker images
	docker compose build

.PHONY: docker-up
docker-up: ## Start all services via Docker Compose
	docker compose up -d

.PHONY: docker-down
docker-down: ## Stop all Docker Compose services
	docker compose down

# =============================================================================
# Kubernetes
# =============================================================================
.PHONY: k8s-apply
k8s-apply: ## Apply all Kubernetes manifests
	kubectl apply -f infra/k8s/namespace.yaml
	kubectl apply -f infra/k8s/ --recursive

.PHONY: k8s-delete
k8s-delete: ## Delete all Kubernetes resources
	kubectl delete namespace ecosupplyai

.PHONY: helm-install
helm-install: ## Install Helm chart
	helm install ecosupplyai infra/helm/ecosupplyai/

.PHONY: helm-upgrade
helm-upgrade: ## Upgrade Helm release
	helm upgrade ecosupplyai infra/helm/ecosupplyai/

# =============================================================================
# Evaluation & Red Teaming
# =============================================================================
.PHONY: eval-run
eval-run: ## Run LLM evaluation suite
	$(PYTHON) -m eval.run_eval

.PHONY: red-team-run
red-team-run: ## Run adversarial red-team tests
	$(PYTHON) -m red_team.run_red_team

# =============================================================================
# Data
# =============================================================================
.PHONY: ingest-docs
ingest-docs: ## Ingest sample documents into RAG pipeline
	$(PYTHON) -m src.rag_pipeline.ingest --source data/sample/documents/

# =============================================================================
# Cleanup
# =============================================================================
.PHONY: clean
clean: ## Remove build artifacts, caches, and temp files
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned."
