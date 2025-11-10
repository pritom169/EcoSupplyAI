# EcoSupplyAI -- Architecture Document

> Detailed technical architecture of the Sustainable Supply Chain Intelligence Platform.

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Service Descriptions](#service-descriptions)
- [Data Flow](#data-flow)
- [Agent Architecture](#agent-architecture)
- [RAG Architecture](#rag-architecture)
- [Security Architecture](#security-architecture)
- [Observability Architecture](#observability-architecture)
- [Deployment Architecture](#deployment-architecture)

---

## System Overview

EcoSupplyAI is a microservices-based AI platform designed for enterprise supply chain sustainability intelligence. The system follows a service-oriented architecture where each capability -- conversational AI, document retrieval, risk scoring, emission forecasting, content generation, and process automation -- is encapsulated in its own independently deployable service.

All client traffic enters through a single **API Gateway** that handles authentication, rate limiting, request routing, and PII filtering. Behind the gateway, services communicate via both synchronous REST/gRPC calls and asynchronous event-driven messaging. A shared infrastructure layer provides persistence (PostgreSQL, Qdrant), caching (Redis), blob storage (Azure Blob), LLM access (Azure OpenAI), and observability (OpenTelemetry, Prometheus, Grafana, Jaeger).

The platform is designed with the following architectural principles:

- **Separation of concerns** -- each service owns its domain logic, data models, and API surface
- **AI safety by design** -- content filtering, PII protection, and guardrails are embedded at the gateway and within each AI-powered service
- **Observability-first** -- every LLM call, retrieval step, and scoring inference is traced end-to-end with OpenTelemetry
- **Horizontal scalability** -- stateless services behind a load balancer, with Temporal for durable stateful workflows
- **Evaluation-driven development** -- automated evaluation pipelines validate AI quality, safety, and cost on every change

---

## Architecture Diagram

```
 +-----------------------------------------------------------------------------+
 |                              CLIENT LAYER                                   |
 |                                                                             |
 |   +--------------+    +--------------+    +--------------+                  |
 |   |   React SPA  |    |  Mobile App  |    |  API Client  |                  |
 |   |  (Dashboard) |    |   (Alerts)   |    | (Automation) |                  |
 |   +------+-------+    +------+-------+    +------+-------+                  |
 +---------+|--------------------+-------------------+-------------------------+
            |                    |                    |
            |          HTTPS / WebSocket / REST       |
            +--------------------+--------------------+
                                 v
 +-----------------------------------------------------------------------------+
 |                          API GATEWAY  :8000                                  |
 |                                                                             |
 |  +------------+  +------------+  +------------+  +----------------------+   |
 |  |    Auth     |  |   Rate     |  |    PII     |  |   Request Router     |   |
 |  | (JWT/RBAC) |  |  Limiter   |  |  Filter    |  |  (Path -> Service)   |   |
 |  +------------+  +------------+  +------------+  +----------------------+   |
 |  +------------+  +------------+  +------------+  +----------------------+   |
 |  |  Content    |  |  Request   |  |  Response  |  |    CORS / CSRF       |   |
 |  |  Safety     |  | Validation |  |  Shaping   |  |    Middleware         |   |
 |  +------------+  +------------+  +------------+  +----------------------+   |
 +---+------+------+------+------+------+------+------+------------------------+
     |      |      |      |      |      |      |
     v      |      v      |      v      |      v
 +--------+ | +--------+  | +--------+  | +--------+
 |  Chat  | | |  RAG   |  | |Content |  | |Workflow|
 | Agent  | | |Pipeline|  | |  Gen   |  | | Engine |
 | :8001  | | | :8002  |  | | :8004  |  | | :8006  |
 +---+----+ | +---+----+  | +---+----+  | +---+----+
     |      |     |       |     |       |     |
     |      v     |       v     |       v     |
     | +--------+ |  +--------+ |  +--------+ |
     | |Scoring | |  |Forecast| |  |  MCP   | |
     | |Service | |  |Service | |  | Server | |
     | | :8003  | |  | :8005  | |  | :8007  | |
     | +---+----+ |  +---+----+ |  +---+----+ |
     |     |      |      |      |      |      |
     +-----+------+------+------+------+------+
                         |
 +-----------------------------------------------------------------------------+
 |                  SHARED INFRASTRUCTURE                                       |
 |                                                                             |
 |  +------------------+  +------------------+  +--------------------------+   |
 |  |   PostgreSQL     |  |     Qdrant       |  |     Azure OpenAI         |   |
 |  |   + pgvector     |  |   Vector DB      |  |  GPT-4o / Ada-002       |   |
 |  |                  |  |                  |  |  Content Safety API      |   |
 |  |  - User data     |  |  - Regulation    |  |                          |   |
 |  |  - Supplier data |  |    embeddings    |  |  - Chat completion       |   |
 |  |  - Audit logs    |  |  - Document      |  |  - Embedding generation  |   |
 |  |  - Score history |  |    embeddings    |  |  - Content filtering     |   |
 |  +------------------+  +------------------+  +--------------------------+   |
 |                                                                             |
 |  +------------------+  +------------------+  +--------------------------+   |
 |  |      Redis       |  |   Azure Blob     |  |      Temporal            |   |
 |  |                  |  |    Storage        |  |                          |   |
 |  |  - Session cache |  |  - Documents     |  |  - Workflow orchestration |   |
 |  |  - Rate limits   |  |  - Reports       |  |  - Durable execution     |   |
 |  |  - LLM cache     |  |  - ML models     |  |  - Retry policies        |   |
 |  |  - Feature flags |  |  - Training data |  |  - Scheduled tasks       |   |
 |  +------------------+  +------------------+  +--------------------------+   |
 |                                                                             |
 |  +----------------------------------------------------------------------+   |
 |  |                    OBSERVABILITY STACK                                |   |
 |  |                                                                      |   |
 |  |  OpenTelemetry --> Jaeger (Traces) --> Grafana (Dashboards)          |   |
 |  |  Collector     --> Prometheus (Metrics) --> AlertManager             |   |
 |  |               --> Loki (Logs) --> Grafana                            |   |
 |  +----------------------------------------------------------------------+   |
 +-----------------------------------------------------------------------------+
```

---

## Service Descriptions

### API Gateway (`:8000`)

| Aspect | Detail |
|---|---|
| **Purpose** | Single entry point for all client traffic. Handles cross-cutting concerns. |
| **Technology** | FastAPI, Starlette middleware, python-jose (JWT), Presidio |
| **API Surface** | REST (all routes), WebSocket (`/ws/chat`) |
| **Key Responsibilities** | JWT validation, RBAC enforcement, per-user rate limiting (Redis-backed), PII detection and redaction on request/response, request routing to downstream services, content safety pre-screening |
| **Dependencies** | Redis (rate limits, sessions), Azure AD (token validation), all downstream services |

### Chat Agent (`:8001`)

| Aspect | Detail |
|---|---|
| **Purpose** | Multi-agent conversational AI that orchestrates specialist agents to answer sustainability queries. |
| **Technology** | Semantic Kernel (Python), LangGraph, LangChain, Azure OpenAI GPT-4o |
| **API Surface** | REST (`POST /chat`), WebSocket (`/ws/stream`) |
| **Key Responsibilities** | Query understanding and intent classification, agent planning and task decomposition, specialist agent dispatch (RAG, Scoring, Forecast), multi-turn conversation management, streaming token delivery |
| **Dependencies** | RAG Pipeline, Scoring Service, Forecast Service, MCP Server, Azure OpenAI, Redis (conversation state) |

### RAG Pipeline (`:8002`)

| Aspect | Detail |
|---|---|
| **Purpose** | Ingest regulatory documents and provide grounded, cited answers to compliance queries. |
| **Technology** | LangChain, Qdrant, sentence-transformers, Azure OpenAI (embedding + generation) |
| **API Surface** | REST (`POST /ingest`, `POST /query`, `GET /documents`) |
| **Key Responsibilities** | Document ingestion with chunking and metadata enrichment, hybrid retrieval (dense + sparse), cross-encoder reranking, grounded generation with inline citations, confidence scoring |
| **Dependencies** | Qdrant (vector storage), PostgreSQL (document metadata), Azure OpenAI (embedding, generation), Azure Blob (raw documents) |

### Scoring Service (`:8003`)

| Aspect | Detail |
|---|---|
| **Purpose** | Predict ESG risk scores for suppliers using ML models with full explainability. |
| **Technology** | XGBoost, scikit-learn, SHAP, FastAPI, MLflow |
| **API Surface** | REST (`POST /score`, `POST /batch-score`, `GET /explain/{supplier_id}`) |
| **Key Responsibilities** | Feature engineering from supplier data, real-time and batch ESG scoring, SHAP-based feature importance explanations, model versioning and A/B testing, country-risk and industry-risk adjustments |
| **Dependencies** | PostgreSQL (supplier data, score history), MLflow (model registry), Redis (feature cache) |

### Content Generator (`:8004`)

| Aspect | Detail |
|---|---|
| **Purpose** | Generate compliance reports, executive summaries, and stakeholder communications. |
| **Technology** | Azure OpenAI GPT-4o, Jinja2, WeasyPrint (PDF), python-docx, FastAPI |
| **API Surface** | REST (`POST /report`, `POST /summary`, `POST /email`, `GET /report/{id}`) |
| **Key Responsibilities** | CSRD-structured report generation with ESRS data points, executive summary synthesis, email and notification template rendering, PDF/DOCX output with branded formatting |
| **Dependencies** | Scoring Service (risk data), Forecast Service (emission projections), RAG Pipeline (regulatory context), Azure Blob (output storage), Azure OpenAI |

### Forecast Service (`:8005`)

| Aspect | Detail |
|---|---|
| **Purpose** | Forecast Scope 1/2/3 emissions using deep learning time-series models. |
| **Technology** | PyTorch, LSTM, Transformer, NumPy, pandas, MLflow |
| **API Surface** | REST (`POST /forecast`, `POST /scenario`, `GET /forecast/{supplier_id}`) |
| **Key Responsibilities** | Time-series emission forecasting with configurable horizons, uncertainty quantification (prediction intervals), scenario analysis (baseline, optimistic, regulatory-pressure), model training pipeline with MLflow tracking |
| **Dependencies** | PostgreSQL (historical emission data), MLflow (model registry), Redis (prediction cache) |

### Workflow Engine (`:8006`)

| Aspect | Detail |
|---|---|
| **Purpose** | Orchestrate multi-step business processes as durable, event-driven workflows. |
| **Technology** | Temporal, FastAPI, Celery (lightweight tasks), Redis |
| **API Surface** | REST (`POST /workflow/start`, `GET /workflow/{id}/status`, `POST /workflow/{id}/signal`) |
| **Key Responsibilities** | Supplier onboarding workflows (data collection -> scoring -> classification -> notification), scheduled report generation, threshold-based alerting pipelines, retry and compensation logic for failed steps |
| **Dependencies** | Temporal (workflow orchestration), Scoring Service, RAG Pipeline, Content Generator, PostgreSQL (workflow state), Redis (signals) |

### MCP Server (`:8007`)

| Aspect | Detail |
|---|---|
| **Purpose** | Model Context Protocol server providing standardized tool access and agent-to-agent communication. |
| **Technology** | FastAPI, MCP SDK, WebSocket, sandboxed execution |
| **API Surface** | REST (`GET /tools`, `POST /tools/execute`), WebSocket (`/ws/a2a`) |
| **Key Responsibilities** | Dynamic tool registration and discovery, secure sandboxed tool execution, A2A (Agent-to-Agent) message routing, external system integration (ERP, SAP, Salesforce adapters), tool usage metering and audit logging |
| **Dependencies** | Redis (tool registry cache), PostgreSQL (audit logs), external systems |

---

## Data Flow

### Flow 1: Chat Query

End-to-end flow for a user asking "What is the ESG risk for Supplier X and their projected emissions?"

```
+------+     +----------+     +-----------+     +---------------------+
| User |---->|   API    |---->|   Chat    |---->|   Planner Agent     |
|      |     | Gateway  |     |   Agent   |     |  (Semantic Kernel)  |
+------+     |          |     |           |     +----------+----------+
             | - Auth   |     | - Session |                |
             | - PII    |     | - State   |     +----------+----------+
             | - Rate   |     | - Stream  |     |   Plan Decomposition |
             +----------+     +-----------+     |                      |
                                                |  Task 1: Get ESG score|
                                                |  Task 2: Get forecast |
                                                |  Task 3: Synthesize   |
                                                +----------+-----------+
                                                           |
                              +-----------------+----------+----------+
                              v                 v                     v
                     +--------------+  +--------------+     +--------------+
                     |   Scoring    |  |   Forecast   |     |     RAG      |
                     |   Agent      |  |    Agent     |     |    Agent     |
                     |              |  |              |     |              |
                     | -> Score API |  | -> Forecast  |     | -> Query     |
                     | -> SHAP data |  |    API       |     |   regulations|
                     | -> Risk level|  | -> Scenarios |     | -> Citations |
                     +------+-------+  +------+-------+     +------+-------+
                            |                 |                    |
                            +--------+--------+--------------------+
                                     v
                           +------------------+
                           |  Synthesis Agent  |
                           |                  |
                           | Combines scoring, |
                           | forecast, and     |
                           | regulatory context |
                           | into final answer  |
                           | with citations     |
                           +--------+---------+
                                    |
                                    v
                              +-----------+     +----------+     +------+
                              |   Chat    |---->|   API    |---->| User |
                              |   Agent   |     | Gateway  |     |      |
                              | (stream)  |     |(PII filt)|     |      |
                              +-----------+     +----------+     +------+
```

**Step-by-step:**

1. **User** sends a natural language query via the React dashboard or API client.
2. **API Gateway** validates the JWT, checks rate limits, scans the input for PII, and routes to the Chat Agent.
3. **Chat Agent** loads conversation history from Redis and passes the query to the **Planner Agent** (Semantic Kernel).
4. **Planner Agent** decomposes the query into subtasks: retrieve ESG score, retrieve emission forecast, retrieve relevant regulations.
5. Subtasks are dispatched in parallel to **specialist agents** (Scoring Agent, Forecast Agent, RAG Agent) via the LangGraph state machine.
6. Each specialist agent calls its respective service API and returns structured results.
7. **Synthesis Agent** combines all results into a coherent, cited response.
8. The response is streamed token-by-token back through the Chat Agent and API Gateway to the user.
9. API Gateway performs **output PII filtering** before delivering to the client.

---

### Flow 2: Supplier Onboarding

Automated workflow triggered when a new supplier is registered in the system.

```
+---------------+     +--------------+     +------------------------------+
|   Supplier    |---->|   Workflow   |---->|     Temporal Workflow        |
| Registration  |     |    Engine    |     |                              |
|   (Event)     |     |              |     |  Step 1: Validate data       |
+---------------+     +--------------+     |  Step 2: Enrich from RAG    |
                                           |  Step 3: Score supplier      |
                                           |  Step 4: Classify risk tier  |
                                           |  Step 5: Generate report     |
                                           |  Step 6: Notify stakeholders |
                                           +----------+-------------------+
                                                      |
                      +---------------+---------------+---------------+
                      v               v               v               v
              +--------------+ +-------------+ +-----------+ +--------------+
              |     RAG      | |   Scoring   | |  Content  | |  Notification|
              |  Pipeline    | |   Service   | | Generator | |   (Email)    |
              |              | |             | |           | |              |
              | Regulatory   | | ESG Risk    | | Supplier  | | Alert to     |
              | requirements | | Score +     | | Risk      | | procurement  |
              | for supplier | | SHAP        | | Brief     | | team         |
              | category     | | explanation | | (PDF)     | |              |
              +--------------+ +-------------+ +-----------+ +--------------+
```

**Step-by-step:**

1. A new supplier is registered via the API or bulk import, emitting a `supplier.created` event.
2. **Workflow Engine** catches the event and starts a Temporal workflow.
3. **Step 1 -- Validate**: Check data completeness, normalize country/industry codes, flag missing fields.
4. **Step 2 -- Enrich**: Query the RAG Pipeline for regulatory requirements applicable to the supplier's sector, geography, and commodity type.
5. **Step 3 -- Score**: Call the Scoring Service to compute an ESG risk score with SHAP explanations.
6. **Step 4 -- Classify**: Apply business rules to assign a risk tier (Critical / High / Medium / Low) based on score thresholds.
7. **Step 5 -- Generate**: Trigger the Content Generator to produce a supplier risk brief (PDF) with score details, top risk factors, and applicable regulations.
8. **Step 6 -- Notify**: Send email notifications to the procurement team with the risk brief attached. High-risk suppliers are flagged for human review.
9. If any step fails, Temporal's retry policies handle transient errors, and compensation logic rolls back state for permanent failures.

---

### Flow 3: Report Generation

On-demand or scheduled generation of CSRD-compliant sustainability reports.

```
+------------------+     +--------------+     +--------------------------+
|  Report Request  |---->|   Content    |---->|   Data Collection Phase  |
|  (User or Cron)  |     |  Generator   |     |                          |
+------------------+     +--------------+     |  +---------------------+ |
                                              |  | Scoring Service     | |
                                              |  | -> Portfolio scores | |
                                              |  | -> Risk distribution| |
                                              |  +---------------------+ |
                                              |  +---------------------+ |
                                              |  | Forecast Service    | |
                                              |  | -> Emission trends  | |
                                              |  | -> Scenario analysis| |
                                              |  +---------------------+ |
                                              |  +---------------------+ |
                                              |  | RAG Pipeline        | |
                                              |  | -> ESRS requirements| |
                                              |  | -> Regulation cites | |
                                              |  +---------------------+ |
                                              +------------+-------------+
                                                           v
                                              +--------------------------+
                                              |   Generation Phase       |
                                              |                          |
                                              |  GPT-4o generates CSRD-  |
                                              |  structured narrative    |
                                              |  sections with ESRS data |
                                              |  points and citations    |
                                              +------------+-------------+
                                                           v
                                              +--------------------------+
                                              |   Rendering Phase        |
                                              |                          |
                                              |  Jinja2 template +       |
                                              |  WeasyPrint -> branded   |
                                              |  PDF report              |
                                              |  -> Azure Blob storage   |
                                              +------------+-------------+
                                                           v
                                              +--------------------------+
                                              |   Delivery Phase         |
                                              |                          |
                                              |  - Dashboard download    |
                                              |  - Email distribution    |
                                              |  - Webhook notification  |
                                              +--------------------------+
```

**Step-by-step:**

1. A report is requested either by a user through the dashboard or triggered by a scheduled cron job in the Workflow Engine.
2. **Content Generator** initiates the data collection phase, calling multiple services in parallel.
3. **Scoring Service** provides portfolio-level risk scores, risk distribution across tiers, and year-over-year trends.
4. **Forecast Service** provides emission projections with uncertainty bands and scenario comparisons.
5. **RAG Pipeline** retrieves applicable ESRS disclosure requirements and regulatory citations.
6. **Generation Phase**: GPT-4o generates CSRD-structured narrative sections (Environment, Social, Governance), weaving in quantitative data from scoring and forecast services, and grounding compliance claims in RAG-retrieved regulations with inline citations.
7. **Rendering Phase**: Generated content is merged into a Jinja2 template and rendered to a branded PDF via WeasyPrint. The PDF is stored in Azure Blob.
8. **Delivery Phase**: The report URL is returned to the user, emailed to configured recipients, and a webhook fires for downstream integrations.

---

## Agent Architecture

EcoSupplyAI employs a multi-agent architecture that combines planning, specialization, and tool use to handle complex sustainability queries.

### Agent Hierarchy

```
                    +-------------------------------+
                    |        Planner Agent           |
                    |      (Semantic Kernel)         |
                    |                                |
                    |  - Understands user intent     |
                    |  - Decomposes into subtasks    |
                    |  - Selects specialist agents   |
                    |  - Manages execution plan      |
                    +---------------+---------------+
                                    |
               +--------------------+--------------------+
               v                    v                    v
    +------------------+ +------------------+ +------------------+
    |    RAG Agent     | |  Scoring Agent   | | Forecast Agent   |
    |                  | |                  | |                  |
    | - Regulation     | | - Supplier risk  | | - Emission       |
    |   queries        | |   assessment     | |   projections    |
    | - Document       | | - Explainability | | - Scenario       |
    |   search         | |   (SHAP)         | |   analysis       |
    | - Citation       | | - Comparative    | | - Uncertainty    |
    |   generation     | |   analysis       | |   quantification |
    +------------------+ +------------------+ +------------------+
               |                    |                    |
               +--------------------+--------------------+
                                    v
                    +-------------------------------+
                    |      Synthesis Agent           |
                    |                                |
                    |  - Merges specialist outputs   |
                    |  - Resolves contradictions     |
                    |  - Generates cited response    |
                    |  - Confidence scoring          |
                    +-------------------------------+
```

### LangGraph State Machine

The agent orchestration is managed by a LangGraph state machine that controls the flow of execution.

```
                    +----------+
                    |  START   |
                    +----+-----+
                         v
                    +----------+
                    |  Parse   | --- Extract intent, entities, constraints
                    |  Input   |
                    +----+-----+
                         v
                    +----------+
                    |   Plan   | --- Planner agent creates execution plan
                    +----+-----+
                         v
                    +----------+     +-----------------+
                    | Execute  |---->| Specialist Agents| (parallel fan-out)
                    |  Tasks   |<----| RAG, Score, Fcast|
                    +----+-----+     +-----------------+
                         v
                    +----------+
                    | Evaluate | --- Check completeness, quality
                    | Results  |
                    +----+-----+
                         |
                    +----+-----+
                    | Complete?|
                    +----+--+--+
                    Yes  |  | No (re-plan)
                         |  +------------------------+
                         v                           |
                    +----------+                     |
                    |Synthesize|                     |
                    | Response |                     |
                    +----+-----+                     |
                         v                           |
                    +----------+           +---------+--+
                    |  Stream  |           |  Re-plan   |
                    |  Output  |           |  & Route   |
                    +----+-----+           +------------+
                         v
                    +----------+
                    |   END    |
                    +----------+
```

**State schema:**

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    plan: Plan                    # Structured execution plan
    task_results: dict[str, Any]  # Results from specialist agents
    iteration: int                # Re-planning iteration counter (max 3)
    confidence: float             # Aggregated confidence score
    citations: list[Citation]     # Collected citations from RAG
    metadata: dict[str, Any]      # Tracing, user context, permissions
```

### Agent-to-Agent (A2A) Communication

For cross-system agent communication, EcoSupplyAI implements the A2A protocol via the MCP Server:

- **Discovery**: Agents register capabilities with the MCP Server's tool registry.
- **Invocation**: An agent can invoke another agent's capabilities via the MCP Server's `POST /tools/execute` endpoint.
- **Async messaging**: For long-running tasks, agents communicate via WebSocket channels on the MCP Server.
- **Security**: All A2A calls are authenticated, rate-limited, and audit-logged.

### MCP Server Integration

The Model Context Protocol server provides a standardized tool interface:

```
External System          MCP Server           Internal Agent
+------------+    +--------------------+    +----------------+
|  ERP/SAP   |<-->|  Tool: erp_query   |<-->|  Chat Agent    |
|  System    |    |                    |    |  (via tool_use)|
+------------+    |  Tool: sap_data    |    |                |
                  |  Tool: email_send  |    |  "Get supplier |
+------------+    |  Tool: score_get   |    |   data from    |
| Salesforce |<-->|  Tool: forecast_   |    |   SAP system"  |
|            |    |        run         |    |                |
+------------+    +--------------------+    +----------------+
```

---

## RAG Architecture

The Retrieval-Augmented Generation pipeline is designed for high-precision regulatory document retrieval and grounded answer generation.

### Ingestion Pipeline

```
+--------------+     +--------------+     +--------------+     +--------------+
|   Document   |---->|    Loader    |---->|   Chunker    |---->|  Embedder    |
|   Sources    |     |              |     |              |     |              |
|              |     | - PDF parser |     | - Recursive  |     | - Ada-002    |
| - CSRD text  |     | - HTML->MD  |     |   (1024 tok) |     | - 1536-dim   |
| - ESRS stds  |     | - DOCX      |     | - Semantic   |     | - Batch      |
| - EU Taxonomy|     | - CSV/Excel |     |   (similarity|     |   processing |
| - Policies   |     | - API fetch |     |    boundary) |     |              |
+--------------+     +--------------+     | - Markdown   |     +------+-------+
                                          |   (header-   |            |
                                          |    aware)    |            v
                                          +--------------+     +--------------+
                                                               |  Vector      |
                                                +--------------+  Store       |
                                                |              |  (Qdrant)    |
                                                v              +--------------+
                                          +--------------+
                                          |  Metadata    |
                                          |  Enrichment  |
                                          |              |
                                          | - Source doc  |
                                          | - Section    |
                                          | - Regulation |
                                          |   reference  |
                                          | - Date       |
                                          | - Chunk idx  |
                                          +--------------+
```

**Chunking strategies:**

| Strategy | Use Case | Parameters |
|---|---|---|
| **Recursive Character** | General-purpose text | chunk_size=1024, overlap=128 |
| **Semantic** | Dense regulatory text | similarity_threshold=0.85, min_chunk=256 |
| **Markdown Header** | Structured documents | headers_to_split=[H1, H2, H3] |

### Retrieval Pipeline

```
+--------------+     +--------------+     +--------------+     +--------------+
|   User       |---->|   Query      |---->|   Hybrid     |---->|  Reranker    |
|   Query      |     |  Embedding   |     |   Search     |     |              |
|              |     |              |     |              |     | - Cross-     |
| "What CSRD   |     | Ada-002      |     | - Dense      |     |   encoder    |
|  disclosures |     | 1536-dim     |     |   (Qdrant    |     |   (ms-marco) |
|  apply to    |     | vector       |     |   cosine)    |     | - Top-k      |
|  Scope 3?"   |     |              |     | - Sparse     |     |   selection  |
+--------------+     +--------------+     |   (BM25)     |     | - Score      |
                                          | - Metadata   |     |   fusion     |
                                          |   filter     |     |              |
                                          +--------------+     +------+-------+
                                                                      |
                                                                      v
                                                               +--------------+
                                                               |   Context    |
                                                               |  Assembly    |
                                                               |              |
                                                               | - Ranked     |
                                                               |   passages   |
                                                               | - Source     |
                                                               |   metadata   |
                                                               | - Citation   |
                                                               |   markers    |
                                                               +------+-------+
                                                                      |
                                                                      v
                                                               +--------------+
                                                               |  Generation  |
                                                               |              |
                                                               | GPT-4o with: |
                                                               | - System     |
                                                               |   prompt     |
                                                               | - Retrieved  |
                                                               |   context    |
                                                               | - Citation   |
                                                               |   format     |
                                                               |   rules      |
                                                               +------+-------+
                                                                      |
                                                                      v
                                                               +--------------+
                                                               |   Answer     |
                                                               |   + Cited    |
                                                               |   Sources    |
                                                               |              |
                                                               | "According   |
                                                               |  to ESRS E1  |
                                                               |  [1], Scope  |
                                                               |  3 requires  |
                                                               |  ..."        |
                                                               +--------------+
```

**Retrieval parameters:**

| Parameter | Value | Rationale |
|---|---|---|
| Dense top-k | 20 | Broad initial recall from vector search |
| Sparse top-k | 20 | Complement with keyword-based matches |
| Fusion method | Reciprocal Rank Fusion | Balance dense and sparse rankings |
| Rerank top-k | 5 | Final context window, ordered by relevance |
| Score threshold | 0.65 | Minimum reranker score to include passage |

### Generation Prompt Structure

```
System: You are a sustainability compliance expert. Answer the user's
question using ONLY the provided context. Cite sources using [1], [2]
format. If the context doesn't contain the answer, say so explicitly.

Context:
[1] {passage_1} (Source: ESRS E1, Section 4.2)
[2] {passage_2} (Source: CSRD Art. 19a)
[3] {passage_3} (Source: EU Taxonomy Reg. Art. 8)

User: {query}
```

---

## Security Architecture

### Authentication and Authorization Flow

```
+------+     +----------+     +----------+     +------------------+
|Client|---->|  Azure    |---->|   API    |---->|   Service        |
|      |     |  AD/OIDC  |     | Gateway  |     |   (Authorized)   |
|      |     |          |     |          |     |                  |
| 1. Login   | 2. Token |     | 3. JWT   |     | 4. Scoped        |
|    request |    issued |     |  verify  |     |    access        |
+------+     +----------+     |  + RBAC  |     +------------------+
                              +----------+
```

### Security Layers

```
                         Request Flow
                              |
                              v
                    +------------------+
           Layer 1 |   Rate Limiting   |  Per-user, per-tier quotas (Redis)
                    +--------+---------+
                              v
                    +------------------+
           Layer 2 |   Authentication  |  JWT validation, token expiry check
                    +--------+---------+
                              v
                    +------------------+
           Layer 3 |   Authorization   |  RBAC: admin, analyst, viewer roles
                    +--------+---------+
                              v
                    +------------------+
           Layer 4 | Input PII Filter  |  Presidio: detect & redact PII
                    +--------+---------+
                              v
                    +------------------+
           Layer 5 |  Content Safety   |  Azure Content Safety: block harmful input
                    +--------+---------+
                              v
                    +------------------+
                    |   SERVICE LOGIC   |  Processed by downstream service
                    +--------+---------+
                              v
                    +------------------+
           Layer 6 | Output PII Filter |  Redact any PII in LLM output
                    +--------+---------+
                              v
                    +------------------+
           Layer 7 |Output Toxicity    |  Check for toxic/harmful generated content
                    +--------+---------+
                              v
                    +------------------+
           Layer 8 |  Audit Logging    |  Log request, response hash, token usage
                    +--------+---------+
                              v
                         Response to Client
```

### Network Security

- **mTLS** between all internal services -- no plaintext inter-service communication
- **Ingress rules** restrict external access to the API Gateway only
- **Network policies** (Kubernetes NetworkPolicy) enforce service-to-service allow lists
- **Secrets management** via Azure Key Vault with automatic rotation

---

## Observability Architecture

### Tracing

Every request is traced end-to-end using OpenTelemetry with custom spans for AI-specific operations.

```
Trace: user_query_abc123
|
+-- span: api_gateway.handle_request (12ms)
|   +-- span: auth.validate_jwt (2ms)
|   +-- span: pii_filter.scan_input (3ms)
|   +-- span: router.dispatch (1ms)
|
+-- span: chat_agent.process (2340ms)
|   +-- span: planner.create_plan (450ms)
|   |   +-- span: llm.chat_completion (420ms)
|   |       +-- attribute: model=gpt-4o
|   |       +-- attribute: prompt_tokens=1250
|   |       +-- attribute: completion_tokens=180
|   |       +-- attribute: cost_usd=0.0089
|   |
|   +-- span: agent.rag_query (680ms)
|   |   +-- span: embedding.generate (45ms)
|   |   +-- span: qdrant.search (120ms)
|   |   +-- span: reranker.score (95ms)
|   |   +-- span: llm.chat_completion (400ms)
|   |
|   +-- span: agent.scoring_query (320ms)
|   |   +-- span: scoring.predict (85ms)
|   |   +-- span: scoring.explain (210ms)
|   |
|   +-- span: agent.synthesize (890ms)
|       +-- span: llm.chat_completion (860ms)
|
+-- span: api_gateway.filter_output (8ms)
    +-- span: pii_filter.scan_output (6ms)
```

### Metrics

Key metrics collected via Prometheus:

| Metric | Type | Description |
|---|---|---|
| `llm_request_duration_seconds` | Histogram | LLM API latency per model, per operation |
| `llm_token_usage_total` | Counter | Token consumption (prompt + completion) |
| `llm_cost_usd_total` | Counter | Estimated cost per model, per service |
| `rag_retrieval_score` | Histogram | Reranker relevance scores |
| `scoring_prediction_latency` | Histogram | ML model inference time |
| `pii_detections_total` | Counter | PII entities detected (by type) |
| `content_safety_blocks_total` | Counter | Requests blocked by content safety |
| `request_rate` | Counter | Requests per second per service |
| `error_rate` | Counter | 4xx/5xx responses per service |

### Logging

Structured JSON logging via `structlog` with correlation IDs:

```json
{
  "timestamp": "2025-01-15T10:23:45.123Z",
  "level": "info",
  "service": "chat_agent",
  "trace_id": "abc123def456",
  "span_id": "789ghi012",
  "user_id": "user_42",
  "event": "llm_completion",
  "model": "gpt-4o",
  "prompt_tokens": 1250,
  "completion_tokens": 180,
  "latency_ms": 420,
  "cost_usd": 0.0089
}
```

### Alerting Rules

| Alert | Condition | Severity |
|---|---|---|
| High LLM Error Rate | error_rate > 5% for 5m | Critical |
| LLM Latency Spike | p95 > 10s for 5m | Warning |
| PII Leakage Detected | pii_detections in output > 0 | Critical |
| Token Budget Exceeded | daily_cost > $500 | Warning |
| Content Safety Block Surge | blocks > 50/hour | Warning |
| Service Down | health_check fails for 30s | Critical |

---

## Deployment Architecture

### Container Orchestration

```
+-----------------------------------------------------------------+
|                     Azure Kubernetes Service (AKS)              |
|                                                                 |
|  +---------------------------------------------------------+   |
|  |                    Ingress Controller                    |   |
|  |               (NGINX / Azure App Gateway)               |   |
|  +---------------------------------------------------------+   |
|                                                                 |
|  +--------------+  +--------------+  +----------------------+   |
|  | Namespace:   |  | Namespace:   |  | Namespace:           |   |
|  | ecosupplyai  |  | monitoring   |  | temporal             |   |
|  |              |  |              |  |                      |   |
|  | - gateway    |  | - prometheus |  | - temporal-server    |   |
|  |   (3 pods)   |  | - grafana   |  | - temporal-worker    |   |
|  | - chat-agent |  | - jaeger    |  | - temporal-ui        |   |
|  |   (3 pods)   |  | - otel-     |  |                      |   |
|  | - rag        |  |   collector |  |                      |   |
|  |   (2 pods)   |  | - loki      |  |                      |   |
|  | - scoring    |  |              |  |                      |   |
|  |   (2 pods)   |  |              |  |                      |   |
|  | - forecast   |  |              |  |                      |   |
|  |   (2 pods)   |  |              |  |                      |   |
|  | - content    |  |              |  |                      |   |
|  |   (2 pods)   |  |              |  |                      |   |
|  | - workflow   |  |              |  |                      |   |
|  |   (2 pods)   |  |              |  |                      |   |
|  | - mcp        |  |              |  |                      |   |
|  |   (2 pods)   |  |              |  |                      |   |
|  +--------------+  +--------------+  +----------------------+   |
|                                                                 |
|  +---------------------------------------------------------+   |
|  |              Managed Services (Azure)                    |   |
|  |  - Azure Database for PostgreSQL (Flexible Server)      |   |
|  |  - Azure Cache for Redis                                |   |
|  |  - Azure Blob Storage                                   |   |
|  |  - Azure OpenAI Service                                 |   |
|  |  - Azure Key Vault                                      |   |
|  |  - Azure Container Registry                             |   |
|  +---------------------------------------------------------+   |
+-----------------------------------------------------------------+
```

### Scaling Strategy

| Service | Min Pods | Max Pods | Scale Trigger |
|---|---|---|---|
| API Gateway | 3 | 10 | CPU > 70%, requests/sec > 500 |
| Chat Agent | 3 | 15 | Request queue depth > 50 |
| RAG Pipeline | 2 | 8 | CPU > 70%, query latency p95 > 2s |
| Scoring Service | 2 | 6 | CPU > 80%, inference latency p95 > 500ms |
| Content Generator | 2 | 6 | Queue depth > 20 |
| Forecast Service | 2 | 4 | CPU > 80% (GPU pods for training) |
| Workflow Engine | 2 | 4 | Active workflow count > 100 |
| MCP Server | 2 | 6 | Concurrent connections > 200 |

### CI/CD Pipeline

```
+------+    +----------+    +----------+    +----------+    +----------+
| Push |--->|  Lint &   |--->|  Unit    |--->|  Build   |--->|  Deploy  |
| to   |    |  Format   |    |  Tests   |    |  Images  |    |  to Dev  |
| PR   |    |           |    |          |    |  (ACR)   |    |          |
+------+    +----------+    +----------+    +----------+    +----+-----+
                                                                 |
                                                                 v
+----------+    +----------+    +----------+    +----------------------+
|  Deploy  |<---|   Eval   |<---|  Staging  |<---|  Integration Tests   |
|  to Prod |    |  Gate    |    |  Deploy  |    |  + Eval Suite        |
|  (manual |    |  (pass   |    |          |    |                      |
|   gate)  |    |  all)    |    |          |    |                      |
+----------+    +----------+    +----------+    +----------------------+
```

---

*For security procedures, see [security-runbook.md](security-runbook.md). For responsible AI practices, see [responsible-ai.md](responsible-ai.md).*
