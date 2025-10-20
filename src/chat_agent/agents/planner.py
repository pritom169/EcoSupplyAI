"""Planner Agent — decides which specialist agents to invoke for a given query."""

from __future__ import annotations

from enum import Enum
from typing import Any

import structlog
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field

from src.chat_agent.config import ChatAgentSettings

logger = structlog.get_logger(__name__)


class AgentType(str, Enum):
    RAG = "rag"
    SCORING = "scoring"
    FORECAST = "forecast"
    SYNTHESIZER = "synthesizer"


class PlanStep(BaseModel):
    agent: AgentType
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(BaseModel):
    steps: list[PlanStep]
    reasoning: str


PLANNER_SYSTEM_PROMPT = """You are a planning agent for a supply chain sustainability platform.
Given a user query, decide which specialist agents to invoke and in what order.

Available agents:
- rag: Search regulations, policies, and supplier documents. Use for questions about rules, compliance, and documentation.
- scoring: Get ESG risk scores for suppliers. Use for questions about supplier performance, risk, and benchmarks.
- forecast: Predict future emissions. Use for questions about emission trends and projections.
- synthesizer: Combine results from multiple agents into a coherent answer. Always include as the last step if multiple agents are used.

Respond with a JSON object: {"steps": [{"agent": "...", "description": "...", "parameters": {...}}], "reasoning": "..."}
"""


class PlannerAgent:
    def __init__(self, settings: ChatAgentSettings) -> None:
        self.settings = settings
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )

    async def create_plan(self, query: str) -> ExecutionPlan:
        response = await self.client.chat.completions.create(
            model=self.settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        import json
        plan_data = json.loads(content)
        plan = ExecutionPlan(**plan_data)
        logger.info("planner.plan_created", steps=len(plan.steps), reasoning=plan.reasoning[:100])
        return plan
