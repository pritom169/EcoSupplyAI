# Prompt Changelog

All notable changes to prompt templates are documented here.

## [2.0.0] - 2025-12-01 — RAG Prompts

### Changed
- **rag_qa v2.0.0**: Added structured output format (answer, sources, confidence). Enforced JSON-like citation format. A/B test showed 15% improvement in citation accuracy vs v1.1.0.

## [1.1.0] - 2025-10-15 — RAG Prompts

### Changed
- **rag_qa v1.1.0**: Added explicit anti-hallucination instructions ("If the context does not contain the answer, say so"). Reduced hallucination rate by ~40% in evaluation suite.

## [1.0.0] - 2025-09-01 — Initial Release

### Added
- **rag_qa v1.0.0**: Base RAG prompt — answer from context, cite sources.
- **planner v1.0.0**: Agent planner system prompt with available agent descriptions.
- **scoring_agent v1.0.0**: Score interpretation instructions.
- **forecast_agent v1.0.0**: Forecast interpretation and trend analysis.
- **report_generation v1.0.0**: Sustainability report writing prompt.
- **email_draft v1.0.0**: Professional email drafting prompt.
- **content_filter v1.0.0**: Input/output safety filtering prompt.
- **toxicity_judge v1.0.0**: LLM-as-judge toxicity assessment prompt.
