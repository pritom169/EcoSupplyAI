<p align="center">
  <h1 align="center">EcoSupplyAI</h1>
  <p align="center"><strong>Sustainable Supply Chain Intelligence Platform</strong></p>
  <p align="center">
    AI-powered supply chain sustainability monitoring, scoring, and optimization for CSRD/ESG compliance
  </p>
  <p align="center">
    <a href="#getting-started">Getting Started</a> &middot;
    <a href="docs/architecture.md">Architecture</a> &middot;
    <a href="docs/responsible-ai.md">Responsible AI</a> &middot;
    <a href="docs/security-runbook.md">Security Runbook</a>
  </p>
</p>

---

## Overview

**EcoSupplyAI** is an AI-powered intelligence platform that helps enterprises monitor, score, and optimize the sustainability of their supply chains to meet CSRD, EU Taxonomy, and broader ESG compliance requirements. The platform combines multi-agent conversational AI, retrieval-augmented generation over regulatory corpora, ML-based ESG risk scoring, and deep-learning emission forecasting into a unified microservices architecture. Companies use EcoSupplyAI to automate supplier due diligence, generate audit-ready sustainability reports, and receive proactive risk alerts -- reducing compliance costs by up to 60% while improving data accuracy and coverage across Scope 1, 2, and 3 emissions.

---

## Architecture Diagram

```
                            +-------------------------------------+
                            |            Client Layer             |
                            |   (React SPA / Mobile / API Keys)   |
                            +--------------+----------------------+
                                           | HTTPS / WSS
                                           v
                    +----------------------------------------------------+
                    |               API Gateway  :8000                    |
                    |    (FastAPI - Auth - Rate Limit - PII Filter)       |
                    +--+------+------+------+------+------+------+-------+
                       |      |      |      |      |      |      |
          +------------+      |      |      |      |      |      +------------+
          v                   v      |      v      |      v                   v
   +-------------+  +--------------+| +----------+| +--------------+  +-------------+
   | Chat Agent  |  |     RAG      || | Scoring  || |   Content    |  |  Workflow   |
   |   :8001     |  |  Pipeline    || | Service  || |  Generator   |  |  Engine     |
   |             |  |   :8002      || |  :8003   || |   :8004      |  |   :8006     |
   | SK Planner  |  | Ingest/Query || | ML Model || | Reports/Email|  | Event-Driven|
   | LangGraph   |  | Reranking    || | XGBoost  || | Templates    |  | Temporal    |
   | Multi-Agent |  | Citations    || | SHAP     || | PDF/DOCX     |  | State Mgmt  |
   +------+------+  +------+------+| +----+-----+| +------+-------+  +------+------+
          |                |        |      |      |        |                  |
          |                |        v      |      v        |                  |
          |                |  +----------+ | +----------+  |                  |
          |                |  | Forecast | | |   MCP    |  |                  |
          |                |  | Service  | | |  Server  |  |                  |
          |                |  |  :8005   | | |  :8007   |  |                  |
          |                |  | PyTorch  | | | Tool Hub |  |                  |
          |                |  | LSTM/TF  | | | A2A/MCP  |  |                  |
          |                |  +----+-----+ | +----+-----+  |                  |
          |                |       |       |      |        |                  |
     -----+----------------+-------+-------+------+--------+------------------+
                                           |
                    +----------------------------------------------------+
                    |              Shared Infrastructure                  |
                    |                                                    |
                    |  +------------+  +--------+  +---------------+    |
                    |  | PostgreSQL |  | Redis  |  | Azure OpenAI  |    |
                    |  | + pgvector |  | Cache  |  | GPT-4o / Ada  |    |
                    |  +------------+  +--------+  +---------------+    |
                    |  +------------+  +--------+  +---------------+    |
                    |  |  Qdrant    |  | Azure  |  |  Prometheus   |    |
                    |  | Vector DB  |  | Blob   |  |  + Grafana    |    |
                    |  +------------+  +--------+  +---------------+    |
                    |  +--------------------------------------------+  |
                    |  |     OpenTelemetry Collector + Jaeger        |  |
                    |  +--------------------------------------------+  |
                    +----------------------------------------------------+
```

---

## Key Features

### Conversational AI
- Multi-agent orchestration with a Semantic Kernel planner and specialist agents
- LangGraph-based state machine for complex, multi-turn reasoning workflows
- Tool-use enabled agents that can query databases, run scoring models, and fetch forecasts in real time
- Streaming responses over WebSocket with token-level observability

### RAG Pipeline
- Ingestion of CSRD directives, ESRS standards, EU Taxonomy regulation, and internal policies
- Hybrid chunking strategies (recursive, semantic, markdown-aware) with metadata enrichment
- Multi-stage retrieval: dense vector search (Qdrant) + BM25 sparse retrieval + cross-encoder reranking
- Grounded generation with inline citations and confidence scoring

### ESG Risk Scoring
- XGBoost-based supplier ESG risk model trained on environmental, social, and governance features
- SHAP explainability for every prediction, surfacing the top contributing risk factors
- Batch scoring for portfolio-wide assessment and real-time scoring for on-demand queries
- Country-risk and industry-risk adjustment layers

### Emission Forecasting
- PyTorch LSTM and Transformer models for Scope 1/2/3 emission time-series forecasting
- Configurable forecast horizons (quarterly, annual, multi-year) with uncertainty quantification
- Scenario analysis: baseline, optimistic, regulatory-pressure scenarios
- Model registry with versioned training runs tracked via MLflow

### Content Generation
- Automated CSRD-compliant sustainability reports with structured ESRS data points
- Executive summaries, supplier risk briefs, and board-ready dashboards
- Email and notification templates with dynamic data binding
- PDF and DOCX rendering with branded templates

### Process Automation
- Event-driven workflow engine built on Temporal for durable, retryable workflows
- Supplier onboarding: automated data collection, scoring, risk classification, and notification
- Scheduled report generation and distribution
- Alerting pipelines for threshold breaches and anomaly detection

### MCP Server (Model Context Protocol)
- Standardized tool interface for external model and agent integration
- Agent-to-Agent (A2A) communication protocol for federated multi-agent systems
- Dynamic tool registration and discovery
- Secure sandboxed execution environment for third-party tools

---

## Tech Stack

| Category | Technologies |
|---|---|
| **Framework** | FastAPI, Pydantic v2, Uvicorn, WebSockets |
| **AI / ML** | Azure OpenAI (GPT-4o, text-embedding-ada-002), PyTorch, XGBoost, scikit-learn, SHAP |
| **Agent Frameworks** | Semantic Kernel (Python), LangGraph, LangChain, AutoGen |
| **Vector Database** | Qdrant, PostgreSQL + pgvector |
| **Observability** | OpenTelemetry, Prometheus, Grafana, Jaeger, structlog |
| **Infrastructure** | Docker, Kubernetes (AKS), Helm, Terraform, Azure Bicep |
| **Data & Storage** | PostgreSQL, Redis, Azure Blob Storage, MLflow |
| **Security** | Azure AD / JWT, Presidio (PII), Azure Content Safety, RBAC, mTLS |
| **Testing & Eval** | pytest, DeepEval, Promptfoo, locust, custom red-team harness |

---

## Project Structure

```
EcoSupplyAI/
|-- src/
|   |-- api_gateway/          # FastAPI gateway -- auth, routing, rate limiting, PII filter
|   |-- chat_agent/           # Multi-agent orchestrator -- SK planner, LangGraph state machine
|   |-- rag_pipeline/         # Ingestion, retrieval, reranking, and grounded generation
|   |-- scoring_service/      # ESG risk scoring -- XGBoost model, SHAP explanations
|   |-- content_generator/    # Report and document generation -- PDF, DOCX, email
|   |-- forecast_service/     # Emission forecasting -- PyTorch LSTM/Transformer models
|   |-- workflow_engine/      # Event-driven workflows -- Temporal-based process automation
|   +-- mcp_server/           # Model Context Protocol server -- tool hub, A2A gateway
|-- eval/                     # Evaluation framework -- DeepEval metrics, promptfoo configs
|-- red_team/                 # Adversarial testing -- prompt injection, jailbreak, PII probes
|-- fine_tuning/              # Fine-tuning pipelines -- data prep, training, evaluation
|-- prompt_registry/          # Versioned prompt templates -- YAML configs, A/B variants
|-- data/                     # Sample data, fixtures, seed files
|-- infra/                    # Infrastructure as Code -- Docker, Helm, Bicep, Terraform
|-- observability/            # Monitoring configs -- Prometheus rules, Grafana dashboards
|-- docs/                     # Documentation -- architecture, security, responsible AI
|-- docker-compose.yml        # Local development orchestration
|-- Makefile                  # Task runner -- build, test, run, eval, deploy commands
|-- pyproject.toml            # Python project metadata and dependency management
+-- .env.example              # Environment variable template
```

---

## Getting Started

### Prerequisites

- **Python 3.11+** (3.12 recommended)
- **Docker** and **Docker Compose** v2+
- **Azure OpenAI** access with GPT-4o and text-embedding-ada-002 deployments
- **Make** (for task runner commands)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/EcoSupplyAI.git
cd EcoSupplyAI

# Create environment configuration
cp .env.example .env
# Edit .env with your Azure OpenAI keys, database URLs, and service configs

# Install in development mode with all extras
pip install -e ".[dev]"
```

### Running with Docker Compose (Recommended)

```bash
# Start all services, databases, and observability stack
docker compose up

# Start in detached mode
docker compose up -d

# View logs for a specific service
docker compose logs -f chat-agent
```

### Running Individual Services

```bash
# Start the API Gateway
make run-gateway

# Start the Chat Agent service
make run-chat-agent

# Start the RAG Pipeline
make run-rag

# Start the Scoring Service
make run-scoring

# Start the Forecast Service
make run-forecast

# Start the Content Generator
make run-content-gen

# Start the Workflow Engine
make run-workflow

# Start the MCP Server
make run-mcp
```

### Running Tests

```bash
# Run all unit tests
make test

# Run tests with coverage report
make test-coverage

# Run integration tests (requires Docker services)
make test-integration
```

---

## Services

| Service | Port | Description |
|---|---|---|
| **API Gateway** | `:8000` | Central entry point -- authentication, routing, rate limiting, PII filtering |
| **Chat Agent** | `:8001` | Multi-agent conversational AI -- planner, specialist dispatch, streaming |
| **RAG Pipeline** | `:8002` | Document ingestion, vector search, reranking, grounded generation |
| **Scoring Service** | `:8003` | ML-based ESG risk scoring with SHAP explainability |
| **Content Generator** | `:8004` | Report generation -- CSRD reports, summaries, emails, PDF/DOCX |
| **Forecast Service** | `:8005` | Time-series emission forecasting -- LSTM, Transformer, scenarios |
| **Workflow Engine** | `:8006` | Event-driven process automation -- onboarding, alerts, scheduling |
| **MCP Server** | `:8007` | Model Context Protocol -- tool registry, A2A gateway, sandboxed execution |

---

## Evaluation

EcoSupplyAI includes a comprehensive evaluation framework to measure AI quality, safety, and cost-efficiency.

```bash
# Run the full evaluation suite
make eval-run

# Run specific evaluation categories
make eval-grounding        # RAG grounding and faithfulness
make eval-toxicity         # Toxicity and content safety
make eval-relevance        # Answer relevance and completeness
make eval-cost             # Token usage and cost analysis

# Generate evaluation report
make eval-report
```

Evaluation metrics include:
- **Grounding Score** -- measures factual alignment between generated answers and source documents
- **Toxicity Score** -- detects harmful, biased, or inappropriate content in model outputs
- **Answer Relevance** -- evaluates how well responses address the user's query
- **Citation Accuracy** -- verifies that inline citations map to real source passages
- **Latency P50/P95/P99** -- end-to-end response time percentiles
- **Cost per Query** -- token consumption and estimated Azure OpenAI spend

---

## Red Team Testing

Adversarial testing is a core part of our safety posture. The red team harness probes the system for vulnerabilities across multiple attack vectors.

```bash
# Run the full red team suite
make red-team-run

# Run specific attack categories
make red-team-injection     # Prompt injection attacks
make red-team-jailbreak     # Jailbreak and guardrail bypass attempts
make red-team-pii           # PII extraction and leakage probes
make red-team-toxicity      # Toxic content generation attempts
make red-team-exfiltration  # Data exfiltration and tool abuse

# Generate red team report
make red-team-report
```

See [docs/security-runbook.md](docs/security-runbook.md) for incident response procedures.

---

## Deployment

EcoSupplyAI supports multiple deployment strategies for different environments.

### Docker Compose (Development / Staging)
```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

### Kubernetes with Helm (Production)
```bash
helm upgrade --install ecosupplyai ./infra/helm/ecosupplyai \
  --namespace ecosupplyai \
  --values ./infra/helm/values-production.yaml
```

### Azure Bicep (Infrastructure Provisioning)
```bash
az deployment group create \
  --resource-group ecosupplyai-prod \
  --template-file ./infra/bicep/main.bicep \
  --parameters ./infra/bicep/parameters.prod.json
```

### CI/CD Pipeline
The project includes GitHub Actions workflows for:
- Automated testing on pull requests
- Container image builds and registry push
- Staged deployments (dev -> staging -> production)
- Post-deployment evaluation runs

---

## Responsible AI

We are committed to building AI systems that are transparent, fair, safe, and accountable. Our responsible AI practices include:

- Multi-layer content filtering (input and output)
- PII detection and redaction using Microsoft Presidio
- Bias monitoring across supplier scoring dimensions
- Hallucination mitigation through RAG grounding and citation requirements
- Human-in-the-loop for high-stakes compliance decisions
- Regular adversarial red team testing

For our full responsible AI principles and implementation details, see **[docs/responsible-ai.md](docs/responsible-ai.md)**.

---

## Contributing

We welcome contributions to EcoSupplyAI. Please follow these guidelines:

1. **Fork** the repository and create a feature branch from `main`
2. **Write tests** for any new functionality
3. **Run the full test suite** before submitting: `make test`
4. **Run linting and formatting**: `make lint` and `make format`
5. **Run evaluations** if your change touches AI behavior: `make eval-run`
6. **Submit a pull request** with a clear description of changes and motivation

Please review our Code of Conduct before contributing.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with a commitment to sustainable, responsible AI.
</p>
