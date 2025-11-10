# EcoSupplyAI -- Security Runbook

> Security incident response procedures, threat model, and operational security practices for the AI platform.

---

## Table of Contents

- [Purpose](#purpose)
- [Threat Model](#threat-model)
- [Security Controls](#security-controls)
- [Incident Response Procedures](#incident-response-procedures)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Regular Security Tasks](#regular-security-tasks)
- [Contacts and Escalation](#contacts-and-escalation)

---

## Purpose

This runbook provides structured procedures for detecting, responding to, and remediating security incidents specific to the EcoSupplyAI platform. AI-powered systems introduce unique threat vectors beyond traditional application security -- including prompt injection, model abuse, PII leakage through generated content, and adversarial manipulation of AI outputs used for compliance decisions.

This document is intended for:
- **Platform engineers** responsible for day-to-day operations
- **Security team members** responding to incidents
- **On-call engineers** handling alerts outside business hours
- **Auditors** reviewing our security posture

All team members should review this runbook quarterly and after any significant incident.

---

## Threat Model

### AI-Specific Threats

| Threat | Description | Likelihood | Impact | Mitigations |
|---|---|---|---|---|
| **Prompt Injection** | Attacker crafts input to override system prompts, extract instructions, or manipulate agent behavior | High | High | Input sanitization, content safety filter, system prompt hardening, output validation, prompt injection classifiers |
| **Indirect Prompt Injection** | Malicious instructions embedded in ingested documents (e.g., supplier-submitted data) that manipulate RAG outputs | Medium | High | Document sanitization on ingestion, RAG output validation, source trustworthiness scoring, human review for untrusted sources |
| **PII Leakage** | Model generates responses containing personally identifiable information from training data or retrieved context | Medium | Critical | Presidio PII filter on input/output, data minimization in prompts, PII-free training data pipelines, output scanning |
| **Model Abuse / Cost Attack** | Attacker sends high-volume or high-token requests to inflate costs or degrade service | Medium | Medium | Per-user rate limiting, token budget caps, anomaly detection on usage patterns, circuit breakers |
| **Hallucination in Compliance Context** | Model generates fabricated regulatory citations or inaccurate compliance guidance | High | Critical | RAG grounding with citation requirements, confidence scoring, human-in-the-loop for high-stakes outputs, evaluation pipeline |
| **Data Exfiltration via Tool Use** | Attacker manipulates agent tool calls to extract data from connected systems (ERP, databases) | Low | Critical | Tool-level RBAC, sandboxed execution, tool call auditing, parameter validation, allowlisted tool operations |
| **Jailbreak / Guardrail Bypass** | Attacker uses sophisticated techniques (role-play, encoding, multi-turn) to bypass content filters | Medium | Medium | Multi-layer filtering (keyword + classifier + LLM-as-judge), regular red team testing, prompt hardening |
| **Adversarial Scoring Manipulation** | Attacker submits crafted supplier data to game the ESG scoring model | Low | High | Input validation, anomaly detection on feature distributions, human review for score outliers, model robustness testing |

### Traditional Application Threats

| Threat | Description | Likelihood | Impact | Mitigations |
|---|---|---|---|---|
| **Unauthorized API Access** | Attacker gains access to APIs without valid credentials | Medium | High | JWT authentication, token expiry, RBAC, API key rotation |
| **Credential Compromise** | API keys, tokens, or service credentials are leaked or stolen | Medium | Critical | Azure Key Vault, automatic rotation, secret scanning in CI, least-privilege access |
| **DDoS Attack** | Volumetric attack overwhelms the API Gateway | Medium | Medium | Azure DDoS Protection, WAF, rate limiting, auto-scaling |
| **Supply Chain Attack** | Compromised dependency introduces vulnerability | Low | High | Dependency scanning (Dependabot, Snyk), pinned versions, SBOM generation |
| **Insider Threat** | Authorized user misuses access to extract data or manipulate outputs | Low | High | Audit logging, least-privilege RBAC, separation of duties, access reviews |

---

## Security Controls

### 1. Input Validation and Sanitization

**PII Filter (Input)**
- **Technology**: Microsoft Presidio with custom recognizers
- **Trigger**: Every incoming request to the API Gateway
- **Actions**:
  - Detect PII entities: names, emails, phone numbers, SSNs, credit cards, addresses, passport numbers
  - Mode: `redact` (replace with `<REDACTED>`) for chat inputs; `block` for queries containing high-sensitivity PII (SSN, credit card)
  - Log detection events (entity type, count) without logging the PII itself
- **Configuration**: `src/api_gateway/middleware/pii_filter.py`

**Content Safety Filter (Input)**
- **Technology**: Azure Content Safety API + custom keyword filter
- **Trigger**: All user-generated text inputs
- **Actions**:
  - Classify input across categories: hate, self-harm, sexual, violence
  - Block requests with severity >= Medium in any category
  - Flag and log requests with severity = Low for review
  - Custom keyword filter catches domain-specific prompt injection patterns
- **Configuration**: `src/api_gateway/middleware/content_safety.py`

**Request Validation**
- Pydantic v2 models enforce strict schema validation on all API inputs
- Maximum input length: 10,000 characters for chat, 50,000 for document ingestion
- File upload restrictions: allowed types (PDF, DOCX, CSV, XLSX), max size 50MB
- SQL injection and XSS prevention via parameterized queries and output encoding

### 2. Output Filtering

**PII Filter (Output)**
- **Trigger**: Every LLM-generated response before returning to the client
- **Actions**:
  - Scan generated text for PII entities using the same Presidio pipeline
  - Redact any detected PII with `[REDACTED]`
  - If more than 3 PII entities detected in a single response, flag for security review
- **Configuration**: `src/api_gateway/middleware/pii_filter.py`

**Toxicity Filter (Output)**
- **Technology**: Multi-layer approach
  - Layer 1: Keyword blocklist (fast, low-latency)
  - Layer 2: Text classifier (distilbert-based toxicity model)
  - Layer 3: Azure Content Safety API (for borderline cases)
- **Actions**:
  - Block responses that score above toxicity threshold
  - Replace with safe fallback response
  - Log the incident with trace ID for investigation

### 3. Authentication and Authorization

**Authentication**
- Azure AD / OIDC for user authentication
- JWT tokens with RS256 signature validation
- Token expiry: access token = 1 hour, refresh token = 24 hours
- Service-to-service: mTLS certificates managed by cert-manager

**Role-Based Access Control (RBAC)**

| Role | Permissions |
|---|---|
| `viewer` | Read dashboards, view reports, ask chat questions |
| `analyst` | All viewer + trigger scoring, request reports, manage suppliers |
| `admin` | All analyst + manage users, configure workflows, access audit logs |
| `service` | Inter-service communication only, scoped to specific endpoints |

**Enforcement**: RBAC middleware in API Gateway checks JWT claims against route-level permission requirements.

### 4. Rate Limiting

| Tier | Requests/min | Tokens/day | Concurrent Requests |
|---|---|---|---|
| Free | 10 | 50,000 | 2 |
| Standard | 60 | 500,000 | 10 |
| Enterprise | 300 | 5,000,000 | 50 |
| Service (internal) | 1,000 | Unlimited | 100 |

- Implemented via Redis-backed sliding window counter
- Rate limit headers returned on every response (`X-RateLimit-*`)
- 429 responses include `Retry-After` header

### 5. Audit Logging

**What is logged:**
- Every API request: timestamp, user ID, endpoint, method, status code, latency
- Every LLM interaction: model, prompt hash (not full prompt), token usage, cost, latency
- Every tool invocation: tool name, parameters (sanitized), result status
- PII detections: entity type and count (never the PII itself)
- Content safety blocks: category, severity, action taken
- Authentication events: login, logout, token refresh, failed attempts
- Authorization failures: user, attempted resource, required vs actual role

**Where logs are stored:**
- Structured JSON logs -> Loki (30-day retention for operational logs)
- Audit trail -> PostgreSQL `audit_log` table (1-year retention, immutable)
- Security events -> Azure Sentinel for SIEM integration

### 6. Network Security

- **mTLS**: All inter-service communication encrypted and mutually authenticated
- **Ingress rules**: Only API Gateway is exposed externally; all other services are cluster-internal
- **Network Policies**: Kubernetes NetworkPolicy enforces service-to-service allow lists
- **Egress filtering**: Services can only reach approved external endpoints (Azure OpenAI, Azure Blob)
- **WAF**: Azure Web Application Firewall on the ingress controller
- **Private endpoints**: Database and cache accessible only via Azure Private Link

---

## Incident Response Procedures

### Procedure 1: Prompt Injection Detected

**Indicators:**
- Content safety filter blocks with `prompt_injection` category
- Anomalous agent behavior (unexpected tool calls, off-topic responses)
- Alert: `content_safety_blocks_total{category="prompt_injection"}` spike
- User report of manipulated or unexpected AI behavior

**Response Steps:**

1. **Triage** (0-15 minutes)
   - [ ] Identify the affected trace ID(s) from alerts or logs
   - [ ] Pull the full trace from Jaeger to understand the attack chain
   - [ ] Determine if the injection succeeded (did the model follow the injected instruction?)
   - [ ] Assess scope: single user, or a pattern affecting multiple sessions?

2. **Contain** (15-60 minutes)
   - [ ] If active exploitation: temporarily block the source IP/user via rate limiter override
   - [ ] If the attack vector is via ingested documents: quarantine the document and disable retrieval
   - [ ] If the injection bypassed filters: deploy an emergency keyword/regex block
   - [ ] Notify the security team lead

3. **Investigate** (1-4 hours)
   - [ ] Analyze the injection payload to understand the technique (direct, indirect, multi-turn)
   - [ ] Review all responses generated during the attack window for data leakage
   - [ ] Check if system prompts or internal instructions were exposed
   - [ ] Determine if any downstream tool calls were manipulated

4. **Remediate** (4-24 hours)
   - [ ] Update content safety filters with the new attack pattern
   - [ ] Harden system prompts against the specific technique
   - [ ] Add the attack to the red team test suite
   - [ ] Run the full red team suite to validate the fix
   - [ ] Deploy updated filters and prompts

5. **Post-Incident**
   - [ ] Write incident report with root cause analysis
   - [ ] Update this runbook with lessons learned
   - [ ] Schedule prompt hardening review

---

### Procedure 2: PII Leakage Detected

**Indicators:**
- Output PII filter detects entities in LLM responses: `pii_output_detections_total` > 0
- User reports seeing personal data in AI responses
- Audit log shows redaction events on output

**Response Steps:**

1. **Triage** (0-15 minutes)
   - [ ] Identify affected trace IDs and user sessions
   - [ ] Determine the type of PII leaked (name, email, SSN, etc.)
   - [ ] Assess whether the PII was redacted before reaching the user or leaked through
   - [ ] Check if the PII originated from RAG context, model training, or user input in another session

2. **Contain** (15-60 minutes)
   - [ ] If PII from RAG: immediately quarantine the source document and clear the affected vector embeddings
   - [ ] If PII from cross-session contamination: flush the Redis conversation cache for affected sessions
   - [ ] Enable strict PII blocking mode (block response entirely if PII detected, rather than redact)
   - [ ] Notify the Data Protection Officer (DPO)

3. **Investigate** (1-8 hours)
   - [ ] Trace the PII to its source: which document, which chunk, which embedding?
   - [ ] Determine the scope: how many users were affected? How many responses contained PII?
   - [ ] Review the ingestion pipeline for the source document -- was PII supposed to be stripped?
   - [ ] Check if the PII filter failed (false negative) or if this was a new PII pattern

4. **Remediate** (4-24 hours)
   - [ ] Remove PII from source documents and re-ingest
   - [ ] Update Presidio recognizers if a new PII pattern was missed
   - [ ] Add test cases to the evaluation suite for the specific PII type
   - [ ] Consider whether affected users need to be notified under GDPR Article 34

5. **Regulatory Compliance**
   - [ ] Document the breach in the data breach register
   - [ ] If personal data of EU residents was exposed: assess GDPR 72-hour notification requirement
   - [ ] Coordinate with DPO and legal on notification obligations
   - [ ] Prepare supervisory authority notification if required

---

### Procedure 3: Model Abuse / High Cost Anomaly

**Indicators:**
- Alert: `llm_cost_usd_total` daily spend exceeds threshold (e.g., $500/day)
- Anomaly detection: sudden spike in token usage from a single user/API key
- Alert: rate limiter hitting 429 responses at an unusual rate
- Unusual patterns: very long prompts, rapid-fire requests, systematic endpoint scanning

**Response Steps:**

1. **Triage** (0-15 minutes)
   - [ ] Identify the user/API key responsible for the anomalous usage
   - [ ] Determine if this is legitimate (large batch job) or abusive
   - [ ] Calculate the cost impact so far

2. **Contain** (15-30 minutes)
   - [ ] If abusive: immediately reduce the user's rate limit to minimum tier
   - [ ] If API key compromise suspected: rotate the API key immediately
   - [ ] If cost is critical: enable emergency cost circuit breaker (reject all LLM calls above threshold)
   - [ ] Notify engineering lead and finance

3. **Investigate** (1-4 hours)
   - [ ] Analyze the request patterns: endpoint distribution, prompt lengths, timing
   - [ ] Check if the user's credentials were compromised (login from new IP, unusual hours)
   - [ ] Review whether the usage exploited a pricing loophole (e.g., streaming without token counting)
   - [ ] Estimate total cost exposure

4. **Remediate** (4-24 hours)
   - [ ] If credential compromise: force password reset, revoke all tokens
   - [ ] If pricing exploit: patch the billing/metering logic
   - [ ] Adjust rate limit thresholds based on lessons learned
   - [ ] Add anomaly detection rule for the specific abuse pattern
   - [ ] Consider whether to bill the user for excess usage or absorb the cost

---

### Procedure 4: Unauthorized Access

**Indicators:**
- Alert: authentication failure rate > 10/minute from a single IP
- Alert: authorization denied events for sensitive endpoints
- Log: successful authentication from unexpected geography or IP range
- Alert: service account token used from outside the cluster

**Response Steps:**

1. **Triage** (0-15 minutes)
   - [ ] Determine the type of access attempt: brute force, stolen token, or escalation
   - [ ] Identify affected accounts and resources
   - [ ] Check if any unauthorized access was successful

2. **Contain** (15-30 minutes)
   - [ ] Block the source IP(s) at the WAF level
   - [ ] If tokens compromised: revoke all active tokens for affected accounts
   - [ ] If service account: rotate the service account credentials immediately
   - [ ] Enable enhanced logging for affected endpoints

3. **Investigate** (1-8 hours)
   - [ ] Analyze access logs: what was accessed? What data was returned?
   - [ ] Determine the entry point: phishing, credential stuffing, key leakage?
   - [ ] Check for lateral movement: did the attacker access other services?
   - [ ] Review audit logs for data exfiltration attempts

4. **Remediate** (4-48 hours)
   - [ ] Force password reset for all affected users
   - [ ] Rotate all potentially compromised secrets and certificates
   - [ ] Patch the vulnerability that allowed unauthorized access
   - [ ] Enable MFA if not already required
   - [ ] Review and tighten RBAC policies

5. **Notification**
   - [ ] Notify affected users of the breach
   - [ ] Assess regulatory notification requirements
   - [ ] Brief executive team if customer data was accessed

---

## Monitoring and Alerting

### Critical Dashboards

| Dashboard | Location | Purpose |
|---|---|---|
| **AI Safety Overview** | Grafana -> AI Safety | PII detections, content safety blocks, prompt injection attempts |
| **LLM Cost Tracker** | Grafana -> Costs | Token usage, cost per model, cost per service, daily trends |
| **Service Health** | Grafana -> Services | Request rates, error rates, latency percentiles, uptime |
| **Security Events** | Azure Sentinel | Authentication failures, authorization denials, suspicious patterns |
| **RAG Quality** | Grafana -> RAG | Retrieval scores, grounding metrics, citation accuracy |

### What to Watch

**Real-time (check during on-call shifts):**
- Error rate spikes (> 5% of requests returning 5xx)
- LLM latency anomalies (p95 > 10 seconds)
- PII detection alerts (any PII in output)
- Content safety block surges (> 2x baseline)
- Authentication failure spikes
- Unusual token consumption patterns

**Daily review:**
- Daily LLM cost and token usage trends
- Rate limit hit rates by user tier
- New content safety patterns flagged for review
- Failed evaluation metrics (grounding, toxicity, relevance)

**Weekly review:**
- Comprehensive security event summary
- Cost trend analysis and forecast
- Evaluation suite pass/fail trends
- Access review: new users, role changes, API key issuance

### Alert Routing

| Severity | Channel | Response Time | Escalation |
|---|---|---|---|
| **Critical** (P1) | PagerDuty -> on-call engineer | 15 minutes | Security lead at 30 min, VP Eng at 1 hour |
| **High** (P2) | Slack #security-alerts + PagerDuty | 1 hour | Security lead at 2 hours |
| **Medium** (P3) | Slack #security-alerts | 4 hours (business hours) | Team lead at 8 hours |
| **Low** (P4) | Slack #security-log | Next business day | N/A |

---

## Regular Security Tasks

### Weekly

- [ ] Review content safety block logs for new attack patterns
- [ ] Check PII detection rates for unexpected trends
- [ ] Review rate limiter effectiveness and adjust thresholds
- [ ] Verify all services are running with latest security patches
- [ ] Review and triage any flagged LLM outputs from the toxicity filter
- [ ] Check evaluation suite results for degradation

### Monthly

- [ ] Run the full red team test suite (`make red-team-run`)
- [ ] Review and update prompt injection patterns in the content safety filter
- [ ] Rotate API keys and service account credentials
- [ ] Review RBAC assignments -- remove stale accounts, verify role appropriateness
- [ ] Review audit logs for suspicious patterns
- [ ] Update dependency versions and run security scans (`make security-scan`)
- [ ] Review and test backup and recovery procedures
- [ ] Update this runbook with any new learnings

### Quarterly

- [ ] Comprehensive penetration test (including AI-specific attack vectors)
- [ ] Review and update the threat model
- [ ] Conduct tabletop exercise for a security scenario
- [ ] Review data retention policies and purge expired data
- [ ] Third-party dependency audit
- [ ] Update team training materials with new threat patterns
- [ ] Review and update incident response contacts

### Annually

- [ ] External security audit
- [ ] Full red team engagement (external team)
- [ ] Review and update security policies
- [ ] Compliance audit (GDPR, SOC 2, ISO 27001)
- [ ] Disaster recovery drill

---

## Contacts and Escalation

### Security Team

| Role | Name | Contact | Availability |
|---|---|---|---|
| **Security Lead** | [Name] | [email] / [phone] | Business hours + on-call |
| **On-Call Engineer (Primary)** | Rotating | PagerDuty schedule | 24/7 |
| **On-Call Engineer (Secondary)** | Rotating | PagerDuty schedule | 24/7 |
| **Data Protection Officer** | [Name] | [email] / [phone] | Business hours |
| **VP Engineering** | [Name] | [email] / [phone] | Escalation only |
| **Legal / Compliance** | [Name] | [email] / [phone] | Business hours |

### External Contacts

| Organization | Contact | When to Engage |
|---|---|---|
| **Azure Support** | Premier support ticket | Azure service incidents, OpenAI API issues |
| **External Incident Response** | [Firm name] / [phone] | Major breach requiring external forensics |
| **Cyber Insurance** | [Provider] / [policy #] | Any incident with potential financial impact |
| **Supervisory Authority (GDPR)** | [DPA contact] | Personal data breach requiring notification (72h) |

### Escalation Path

```
Alert Fired
    |
    v
On-Call Engineer (Primary)
    | (15 min no response)
    v
On-Call Engineer (Secondary)
    | (30 min no response OR P1 severity)
    v
Security Lead
    | (1 hour no resolution OR data breach)
    v
VP Engineering + DPO + Legal
    | (customer data breach OR regulatory notification)
    v
Executive Team + External Incident Response
```

---

*This runbook is a living document. Last reviewed: [Date]. Next review: [Date + 3 months]. Owner: Security Team.*
