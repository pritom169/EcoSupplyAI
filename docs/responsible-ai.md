# EcoSupplyAI -- Responsible AI

> Our principles, practices, and safeguards for building trustworthy AI systems that support sustainable supply chain decisions.

---

## Table of Contents

- [Our Commitment](#our-commitment)
- [Principles](#principles)
- [Implementation](#implementation)
- [Red Teaming Program](#red-teaming-program)
- [Evaluation Framework](#evaluation-framework)
- [Data Governance](#data-governance)
- [Human Oversight](#human-oversight)
- [Environmental Impact](#environmental-impact)
- [Continuous Improvement](#continuous-improvement)

---

## Our Commitment

EcoSupplyAI is built on the conviction that AI systems used for sustainability compliance and supply chain decisions must themselves be developed and operated responsibly. The outputs of our platform directly influence procurement decisions, supplier relationships, compliance filings, and corporate sustainability strategies. This influence demands that we hold our AI systems to the highest standards of accuracy, fairness, transparency, and safety.

We recognize that AI is not infallible. Language models can hallucinate, scoring models can encode biases, and automated workflows can amplify errors at scale. Our commitment is not to eliminate these risks entirely -- that is not yet possible -- but to detect, mitigate, measure, and continuously improve our handling of them. Every design decision, from architecture to prompt engineering to deployment, is informed by responsible AI principles.

This document describes how we put these principles into practice across every layer of the EcoSupplyAI platform.

---

## Principles

### 1. Transparency

We make the behavior of our AI systems understandable and inspectable.

- Every AI-generated response includes **source citations** linking claims to specific regulatory passages or data points
- ESG risk scores are accompanied by **SHAP explanations** showing which factors drove the prediction and by how much
- Emission forecasts include **uncertainty bands** and clearly state the model, assumptions, and data window used
- Generated reports clearly identify **AI-generated content** vs. human-authored content
- All prompts are versioned in the **prompt registry** and changes are tracked, reviewed, and auditable

### 2. Fairness

We actively monitor and mitigate bias in our AI systems, especially in scoring models that influence supplier decisions.

- ESG scoring models are tested for **demographic and geographic parity** -- a supplier in a developing nation should not be unfairly penalized for data availability differences
- We evaluate scoring distributions across **country, industry, and company size** segments to detect systematic bias
- RAG retrieval is tested to ensure **equitable coverage** of regulations across jurisdictions (not just EU-centric)
- Language models are monitored for **cultural bias** in generated communications and reports

### 3. Privacy

We protect personal data and minimize data exposure at every layer.

- **PII detection and redaction** on all inputs and outputs using Microsoft Presidio
- **Data minimization** in prompts -- we include only the context needed for the task, never entire databases
- **No personal data in training** -- fine-tuning datasets are stripped of PII before use
- **Encryption at rest and in transit** for all data stores
- **Right to erasure** support -- supplier data can be fully deleted from all stores, including vector embeddings

### 4. Safety

We implement defense-in-depth to prevent harmful outputs and system manipulation.

- **Multi-layer content filtering** on inputs and outputs (keyword, classifier, API, LLM-as-judge)
- **Prompt injection defense** through input sanitization, system prompt hardening, and injection classifiers
- **Guardrails** that prevent the AI from making definitive compliance declarations (always recommends human review)
- **Circuit breakers** that halt AI operations if safety metrics degrade beyond thresholds
- **Sandboxed tool execution** for all MCP Server tool calls

### 5. Accountability

We maintain clear responsibility chains and comprehensive audit trails.

- Every AI decision is **logged with full traceability**: user, query, model, prompt version, retrieved context, and generated output (hash)
- **Human-in-the-loop** for high-stakes decisions (supplier rejection, compliance flag escalation)
- **Evaluation pipelines** run on every code change to detect quality and safety regressions
- Clear **ownership model**: each service has a designated owner responsible for its AI behavior
- **Incident response procedures** documented in the [security runbook](security-runbook.md)

### 6. Sustainability

We practice what we preach -- monitoring and minimizing the environmental impact of our own AI operations.

- **Token usage tracking** per model, per service, per query
- **Model size optimization** -- using the smallest model that meets quality requirements for each task
- **Caching strategies** to reduce redundant LLM calls
- **Compute efficiency** monitoring as a first-class metric alongside quality and cost

---

## Implementation

### Input / Output Filtering

Our content filtering system operates as a multi-stage pipeline on both incoming requests and outgoing responses.

**Input filtering pipeline:**

```
User Input
    |
    v
+------------------------------+
|  Stage 1: Schema Validation  |  Pydantic v2: type checking, length limits, format validation
+-------------+----------------+
              v
+------------------------------+
|  Stage 2: PII Detection      |  Presidio: 15+ entity types, custom recognizers for
|                              |  domain-specific patterns (supplier IDs, contract numbers)
+-------------+----------------+
              v
+------------------------------+
|  Stage 3: Content Safety     |  Azure Content Safety API: hate, self-harm, sexual, violence
|                              |  Severity threshold: block >= Medium
+-------------+----------------+
              v
+------------------------------+
|  Stage 4: Injection Detection|  Custom classifier trained on known prompt injection patterns
|                              |  + regex patterns for common injection templates
+-------------+----------------+
              v
   Sanitized input -> Service
```

**Output filtering pipeline:**

```
LLM Response
    |
    v
+------------------------------+
|  Stage 1: PII Redaction      |  Presidio: scan generated text, redact any PII with [REDACTED]
+-------------+----------------+
              v
+------------------------------+
|  Stage 2: Toxicity Check     |  Layer 1: Keyword blocklist (< 1ms)
|                              |  Layer 2: DistilBERT classifier (< 50ms)
|                              |  Layer 3: Azure Content Safety (< 200ms, for borderline cases)
+-------------+----------------+
              v
+------------------------------+
|  Stage 3: Compliance Guard   |  Ensure AI does not make definitive legal/compliance claims
|                              |  Flag declarative compliance statements for human review
+-------------+----------------+
              v
   Filtered response -> Client
```

### PII Protection

**Detection capabilities:**

| PII Type | Detection Method | Action |
|---|---|---|
| Person names | Presidio NER (spaCy) + custom patterns | Redact |
| Email addresses | Regex + Presidio | Redact |
| Phone numbers | Presidio (multi-format) | Redact |
| Social Security Numbers | Regex + checksum validation | Block request |
| Credit card numbers | Regex + Luhn check | Block request |
| Physical addresses | Presidio NER | Redact |
| Passport numbers | Country-specific regex | Block request |
| IP addresses | Regex | Redact |
| IBAN / bank accounts | Country-specific regex + checksum | Block request |
| Custom: Supplier contract IDs | Custom Presidio recognizer | Redact (in external-facing outputs) |

**Data minimization practices:**
- RAG context windows include only the top-k most relevant passages, not full documents
- Scoring features are aggregated and anonymized before inclusion in prompts
- Conversation history is summarized after 10 turns to reduce PII exposure window
- Prompt templates use placeholders; actual data is injected at runtime and never stored in prompt registry

### Bias Monitoring

**Scoring model fairness testing:**

We evaluate the ESG scoring model for bias across protected dimensions at every model retraining cycle.

```
Fairness Evaluation Pipeline
|
+-- Segment: Country (developing vs. developed nations)
|   +-- Metric: Score distribution parity (KL divergence < 0.1)
|   +-- Metric: False positive rate parity (within 5%)
|   +-- Metric: Score variance by country (coefficient of variation < 0.3)
|
+-- Segment: Industry (agriculture, manufacturing, tech, etc.)
|   +-- Metric: Score distribution by industry normalized for inherent risk
|   +-- Metric: Feature importance stability across industries
|
+-- Segment: Company Size (SME vs. large enterprise)
|   +-- Metric: Data availability bias check (SMEs have less data)
|   +-- Metric: Score calibration by company size
|
+-- Segment: Data Completeness
    +-- Metric: Score stability with missing features (< 10% shift)
    +-- Metric: Imputation bias analysis
```

**RAG retrieval fairness:**
- Retrieval is tested across regulatory jurisdictions to ensure balanced coverage
- Query reformulation is evaluated to prevent bias toward English-language or EU-centric results
- Citation distribution is monitored to ensure diverse source representation

### Toxicity Prevention

Our multi-layer toxicity prevention system catches harmful content at multiple points.

| Layer | Technology | Latency | Coverage | False Positive Rate |
|---|---|---|---|---|
| **Keyword blocklist** | Custom dictionary (500+ terms) | < 1ms | Known harmful terms | < 0.1% |
| **ML classifier** | Fine-tuned DistilBERT | < 50ms | Contextual toxicity, subtle harm | < 2% |
| **Azure Content Safety** | Azure API (4 categories) | < 200ms | Hate, self-harm, sexual, violence | < 1% |
| **LLM-as-judge** | GPT-4o with safety prompt | < 2s | Nuanced, context-dependent harm | < 3% |

**LLM-as-judge** is invoked only for borderline cases (classifier confidence 0.4-0.7) to minimize cost and latency.

### Hallucination Mitigation

Hallucination is a critical risk in a compliance context where fabricated regulatory citations could lead to legal exposure.

**Mitigation strategies:**

1. **RAG grounding**: All compliance-related responses must be grounded in retrieved documents. The system prompt explicitly instructs the model: *"Answer ONLY based on the provided context. If the context does not contain the answer, say so explicitly. Never fabricate regulatory references."*

2. **Citation requirements**: Every factual claim in a generated response must include a bracketed citation (e.g., `[1]`) linking to a specific retrieved passage. Responses without citations are flagged.

3. **Confidence scoring**: Each response includes a confidence score (0.0-1.0) derived from:
   - Reranker relevance score of the top retrieved passages
   - Number of supporting passages found
   - Model self-assessed confidence (calibrated via evaluation)

4. **Confidence thresholds and actions:**

   | Confidence | Action |
   |---|---|
   | >= 0.8 | Deliver response normally |
   | 0.5 - 0.8 | Deliver with disclaimer: "This response has moderate confidence. Please verify with a compliance expert." |
   | < 0.5 | Do not deliver. Instead: "I don't have sufficient information to answer this accurately. Please consult a compliance expert." |

5. **Post-hoc verification**: The evaluation pipeline includes a grounding metric that checks whether generated claims are supported by the cited sources. This runs on every evaluation cycle.

### Model and Prompt Versioning

All prompts and model configurations are versioned, tested, and auditable.

**Prompt registry structure:**

```
prompt_registry/
|-- chat/
|   |-- planner_system.yaml         # v3.2 -- Planner agent system prompt
|   |-- rag_system.yaml             # v2.8 -- RAG generation system prompt
|   |-- synthesis_system.yaml       # v2.1 -- Synthesis agent system prompt
|   +-- safety_judge.yaml           # v1.5 -- LLM-as-judge safety prompt
|-- scoring/
|   |-- explanation_system.yaml     # v1.3 -- Score explanation generation
|   +-- comparison_system.yaml      # v1.1 -- Supplier comparison narrative
|-- content/
|   |-- report_system.yaml          # v2.4 -- CSRD report generation
|   |-- summary_system.yaml         # v1.7 -- Executive summary generation
|   +-- email_system.yaml           # v1.2 -- Stakeholder email generation
+-- metadata.yaml                   # Registry index with version history
```

**Each prompt YAML includes:**

```yaml
name: rag_system_prompt
version: "2.8"
description: "System prompt for RAG grounded generation over regulatory documents"
author: "ai-engineering-team"
created: "2025-01-10"
updated: "2025-03-15"
model: "gpt-4o"
temperature: 0.1
max_tokens: 2048
prompt: |
  You are a sustainability compliance expert...
changelog:
  - version: "2.8"
    date: "2025-03-15"
    change: "Added explicit instruction to never fabricate ESRS references"
  - version: "2.7"
    date: "2025-02-28"
    change: "Improved citation format instructions for consistency"
evaluation_results:
  grounding_score: 0.92
  toxicity_score: 0.01
  relevance_score: 0.89
```

**Change management process:**
1. Prompt changes are submitted as pull requests
2. Automated evaluation suite runs against the new prompt version
3. Results are compared against the current production version
4. Regressions in any safety metric block the merge
5. Quality regressions > 5% require explicit approval from the AI safety lead
6. Deployed prompts can be rolled back instantly via the registry

---

## Red Teaming Program

### Overview

We conduct regular adversarial testing to identify vulnerabilities in our AI systems before they can be exploited. Our red team program covers both automated and manual testing.

### Scope

| Attack Category | Description | Frequency |
|---|---|---|
| **Prompt injection** | Direct and indirect injection attempts to override system behavior | Every sprint |
| **Jailbreak** | Techniques to bypass safety guardrails (role-play, encoding, multi-turn) | Every sprint |
| **PII extraction** | Attempts to extract personal data from model memory or RAG context | Monthly |
| **Hallucination probing** | Queries designed to elicit fabricated regulatory citations | Every sprint |
| **Bias elicitation** | Queries designed to surface biased scoring or discriminatory outputs | Monthly |
| **Tool abuse** | Manipulation of agent tool calls to access unauthorized data or actions | Monthly |
| **Cost attacks** | Techniques to amplify token usage or trigger expensive operations | Quarterly |
| **Data exfiltration** | Attempts to extract training data, system prompts, or internal configs | Quarterly |

### Testing Process

```
+------------------+     +------------------+     +------------------+
|   Define Attack  |---->|   Execute Test   |---->|   Analyze        |
|   Scenarios      |     |   Suite          |     |   Results        |
|                  |     |                  |     |                  |
| - New techniques |     | make red-team-   |     | - Pass/fail rate |
|   from research  |     |   run            |     | - New bypasses   |
| - Past incidents |     |                  |     | - False negatives|
| - Community      |     | Automated +      |     |                  |
|   submissions    |     | manual testing   |     |                  |
+------------------+     +------------------+     +--------+---------+
                                                           |
                         +------------------+     +--------+---------+
                         |   Validate Fix   |<----|   Remediate      |
                         |                  |     |                  |
                         | Re-run failed    |     | - Update filters |
                         | scenarios        |     | - Harden prompts |
                         |                  |     | - Add guardrails |
                         +------------------+     +------------------+
```

### Reporting

Red team results are compiled into a structured report including:
- Total scenarios tested and pass/fail rates
- New vulnerabilities discovered with severity ratings
- Comparison against previous red team run
- Recommended remediation actions with priority
- Timeline for fixes

Reports are shared with the security team, AI engineering leads, and executive sponsors.

---

## Evaluation Framework

### Metrics

We track a comprehensive set of metrics across quality, safety, and efficiency dimensions.

**Quality Metrics:**

| Metric | Description | Target | Measurement |
|---|---|---|---|
| **Grounding Score** | Factual alignment between generated answers and source documents | >= 0.90 | DeepEval GroundednessMetric |
| **Answer Relevance** | How well the response addresses the user's query | >= 0.85 | DeepEval AnswerRelevancyMetric |
| **Citation Accuracy** | Whether inline citations map to real, relevant source passages | >= 0.95 | Custom verifier |
| **Completeness** | Whether the response covers all aspects of the query | >= 0.80 | LLM-as-judge evaluation |

**Safety Metrics:**

| Metric | Description | Target | Measurement |
|---|---|---|---|
| **Toxicity Score** | Presence of harmful, biased, or inappropriate content | <= 0.02 | Azure Content Safety + custom classifier |
| **PII Leakage Rate** | PII entities detected in output before filtering | <= 0.01 | Presidio output scan |
| **Injection Resistance** | Percentage of prompt injection attempts successfully blocked | >= 0.98 | Red team suite |
| **Guardrail Compliance** | Percentage of responses that include required disclaimers/citations | >= 0.99 | Rule-based checker |

**Efficiency Metrics:**

| Metric | Description | Target | Measurement |
|---|---|---|---|
| **Latency P50** | Median end-to-end response time | < 2s | OpenTelemetry traces |
| **Latency P95** | 95th percentile response time | < 8s | OpenTelemetry traces |
| **Cost per Query** | Average Azure OpenAI spend per user query | < $0.05 | Token usage * pricing |
| **Cache Hit Rate** | Percentage of queries served from cache | >= 30% | Redis metrics |

### Evaluation Pipeline

```bash
# Run the full evaluation suite
make eval-run

# Output:
# Grounding Score:      0.93 (target: 0.90)  PASS
# Answer Relevance:     0.87 (target: 0.85)  PASS
# Citation Accuracy:    0.96 (target: 0.95)  PASS
# Completeness:         0.82 (target: 0.80)  PASS
# Toxicity Score:       0.01 (target: 0.02)  PASS
# PII Leakage Rate:     0.00 (target: 0.01)  PASS
# Injection Resistance: 0.99 (target: 0.98)  PASS
# Latency P50:          1.8s (target: 2.0s)  PASS
# Cost per Query:       $0.03 (target: $0.05) PASS
#
# Overall: 9/9 metrics passing. Evaluation PASSED.
```

Evaluations run:
- **On every pull request** (subset: grounding, toxicity, injection resistance)
- **Nightly** (full suite against staging environment)
- **Weekly** (full suite + red team against production-like environment)

---

## Data Governance

### Data Classification

| Classification | Examples | Storage | Retention | Access |
|---|---|---|---|---|
| **Public** | Published regulations, ESRS standards, EU Taxonomy text | Qdrant + Blob | Indefinite | All authenticated users |
| **Internal** | Aggregated scoring data, anonymized trends, evaluation results | PostgreSQL | 3 years | Analyst + Admin roles |
| **Confidential** | Supplier-specific data, individual scores, company profiles | PostgreSQL (encrypted) | Per contract | Scoped by organization |
| **Restricted** | PII (names, emails), audit logs with user data, API keys | PostgreSQL (encrypted) + Key Vault | 1 year (PII), 7 years (audit) | Admin only, logged access |

### Data Lifecycle

```
+--------------+     +--------------+     +--------------+     +--------------+
|  Collection  |---->|  Processing  |---->|   Storage    |---->|  Deletion    |
|              |     |              |     |              |     |              |
| - Consent    |     | - PII strip  |     | - Encrypted  |     | - Retention  |
|   recorded   |     | - Anonymize  |     |   at rest    |     |   policy     |
| - Purpose    |     | - Validate   |     | - Access     |     | - Right to   |
|   documented |     | - Classify   |     |   controlled |     |   erasure    |
| - Minimized  |     |              |     | - Backed up  |     | - Crypto     |
|              |     |              |     |              |     |   shredding  |
+--------------+     +--------------+     +--------------+     +--------------+
```

### What We Do NOT Store

- Raw user chat messages are not stored beyond the session (Redis TTL: 24 hours)
- Full LLM prompts are not stored -- only prompt template version and parameter hashes
- PII detected in inputs is redacted before any logging
- Model weights and training data are stored in isolated environments, never in the application database

### Anonymization Techniques

| Technique | Application |
|---|---|
| **Pseudonymization** | Supplier IDs replace company names in analytics |
| **k-Anonymity** | Aggregated scoring data grouped to ensure k >= 5 |
| **Differential privacy** | Noise added to aggregated emission statistics |
| **Tokenization** | Sensitive fields replaced with non-reversible tokens in logs |

---

## Human Oversight

### Human-in-the-Loop Decisions

Certain AI outputs require human review before action is taken. These are defined by the impact and reversibility of the decision.

| Decision Type | AI Role | Human Role | Escalation Trigger |
|---|---|---|---|
| **Supplier rejection** | AI recommends rejection with risk score and explanation | Human reviews recommendation, makes final decision | Score above critical threshold |
| **Compliance flag** | AI identifies potential non-compliance and generates alert | Compliance officer reviews flag and determines response | Any compliance finding |
| **Report publication** | AI generates draft report with citations | Human reviews, edits, and approves before publication | All reports before external distribution |
| **Scoring model update** | AI retrains model and reports evaluation metrics | Human reviews fairness metrics and approves deployment | Every model version change |
| **Prompt change** | Engineer modifies prompt and runs evaluations | AI safety lead reviews evaluation results and approves | Any regression in safety metrics |

### Override and Appeal Process

1. Users can flag any AI output as incorrect or harmful via the dashboard
2. Flagged outputs are routed to the AI review queue
3. A human reviewer investigates the flag, checks the trace, and determines:
   - If the output was incorrect: added to evaluation test cases
   - If the output was harmful: escalated via security runbook procedures
   - If a systematic issue: triggers prompt/model review cycle
4. The user is notified of the review outcome within 48 business hours

---

## Environmental Impact

### Our Commitment to Sustainable AI

As a platform dedicated to supply chain sustainability, we hold ourselves accountable for the environmental footprint of our own AI operations.

### What We Track

| Metric | Description | Current | Target |
|---|---|---|---|
| **Tokens per query (avg)** | Average total tokens consumed per user query | ~3,200 | < 3,000 |
| **Cache hit rate** | Queries served from cache (avoiding LLM call) | 32% | > 40% |
| **Model right-sizing rate** | Percentage of tasks using the smallest sufficient model | 78% | > 85% |
| **Estimated CO2 per query** | Estimated carbon footprint per query (based on Azure region) | ~0.8g CO2e | < 0.5g CO2e |

### Optimization Strategies

1. **Model right-sizing**: Use GPT-4o only for complex reasoning tasks. Use GPT-4o-mini for classification, extraction, and formatting. Use Ada-002 only for embedding.

2. **Semantic caching**: Cache LLM responses for semantically similar queries (cosine similarity > 0.95) to avoid redundant API calls.

3. **Prompt optimization**: Regular prompt engineering reviews to minimize token usage while maintaining quality. Tracked via the `prompt_tokens` metric.

4. **Batch processing**: Aggregate non-urgent requests (e.g., nightly scoring runs) into batches to optimize compute utilization.

5. **Regional selection**: Prefer Azure regions powered by renewable energy for non-latency-sensitive workloads.

---

## Continuous Improvement

### Feedback Loops

```
+------------------+     +------------------+     +------------------+
|   User Feedback  |---->|    Analysis &    |---->|   Improvement    |
|                  |     |   Prioritization |     |                  |
| - Thumbs up/down |     |                  |     | - Prompt updates |
| - Flag incorrect |     | - Trend analysis |     | - Model retrain  |
| - Flag harmful   |     | - Root cause     |     | - Filter updates |
| - Feature request|     | - Impact scoring |     | - New test cases |
+------------------+     +------------------+     +------------------+
         ^                                                 |
         |                                                 |
         +-------------------------------------------------+
                         Measure impact
```

### Improvement Cadence

| Activity | Frequency | Participants |
|---|---|---|
| **Evaluation suite review** | Weekly | AI Engineering team |
| **Red team testing** | Sprint (bi-weekly) | Security + AI Engineering |
| **Prompt optimization** | Monthly | AI Engineering + Domain experts |
| **Model retraining** | Quarterly (or on data drift) | ML Engineering |
| **Fairness audit** | Quarterly | AI Ethics lead + External reviewer |
| **Responsible AI review** | Quarterly | Full team + stakeholders |
| **External audit** | Annually | Third-party AI ethics firm |

### Model Update Policy

1. **No model change without evaluation**: Every model version, prompt change, or configuration update must pass the full evaluation suite before deployment.
2. **Staged rollout**: Changes deploy to dev -> staging -> production with evaluation gates at each stage.
3. **Rollback capability**: Any change can be rolled back within 5 minutes using the prompt registry and model registry versioning.
4. **Regression zero-tolerance for safety**: Any regression in safety metrics (toxicity, PII leakage, injection resistance) is an automatic deployment blocker, regardless of quality improvements.
5. **Quality regression threshold**: Quality metric regressions > 5% require explicit sign-off from the AI engineering lead and product owner.

---
