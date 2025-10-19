"""LangGraph workflow for multi-agent orchestration."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

import httpx
import structlog
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from src.chat_agent.agents.planner import AgentType, PlannerAgent
from src.chat_agent.config import get_chat_settings

logger = structlog.get_logger(__name__)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    plan: list[dict[str, Any]]
    current_step: int
    results: dict[str, Any]
    final_answer: str


async def planner_node(state: AgentState) -> dict:
    """Plan which agents to invoke based on the user message."""
    settings = get_chat_settings()
    planner = PlannerAgent(settings)

    last_message = state["messages"][-1].content if state["messages"] else ""
    plan = await planner.create_plan(last_message)

    return {
        "plan": [step.model_dump() for step in plan.steps],
        "current_step": 0,
        "results": {},
    }


async def rag_node(state: AgentState) -> dict:
    """Execute RAG search for regulatory and document questions."""
    settings = get_chat_settings()
    query = state["messages"][-1].content if state["messages"] else ""

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.RAG_SERVICE_URL}/rag/query",
            json={"question": query, "top_k": 5},
        )
        data = resp.json() if resp.status_code == 200 else {"answer": "RAG service unavailable"}

    results = state.get("results", {})
    results["rag"] = data
    return {"results": results, "current_step": state["current_step"] + 1}


async def scoring_node(state: AgentState) -> dict:
    """Execute supplier scoring queries."""
    settings = get_chat_settings()
    step = state["plan"][state["current_step"]] if state["plan"] else {}
    supplier_id = step.get("parameters", {}).get("supplier_id", "SUP-001")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.SCORING_SERVICE_URL}/scoring/esg",
            json={"supplier_id": supplier_id},
        )
        data = resp.json() if resp.status_code == 200 else {"error": "Scoring service unavailable"}

    results = state.get("results", {})
    results["scoring"] = data
    return {"results": results, "current_step": state["current_step"] + 1}


async def forecast_node(state: AgentState) -> dict:
    """Execute emission forecast queries."""
    settings = get_chat_settings()
    step = state["plan"][state["current_step"]] if state["plan"] else {}
    supplier_id = step.get("parameters", {}).get("supplier_id", "SUP-001")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.FORECAST_SERVICE_URL}/forecast/predict",
            json={"supplier_id": supplier_id, "months_ahead": 6},
        )
        data = resp.json() if resp.status_code == 200 else {"error": "Forecast service unavailable"}

    results = state.get("results", {})
    results["forecast"] = data
    return {"results": results, "current_step": state["current_step"] + 1}


async def synthesizer_node(state: AgentState) -> dict:
    """Combine results from multiple agents into a coherent response."""
    from openai import AsyncAzureOpenAI

    settings = get_chat_settings()
    client = AsyncAzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )

    context = "\n\n".join(f"[{key}]: {value}" for key, value in state.get("results", {}).items())
    query = state["messages"][-1].content if state["messages"] else ""

    response = await client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": "Synthesize the following agent results into a clear, cited answer."},
            {"role": "user", "content": f"Question: {query}\n\nAgent Results:\n{context}"},
        ],
        temperature=settings.TEMPERATURE,
    )

    answer = response.choices[0].message.content or ""
    return {"final_answer": answer}


def route_step(state: AgentState) -> str:
    """Route to the correct agent node based on the current plan step."""
    plan = state.get("plan", [])
    step_idx = state.get("current_step", 0)

    if step_idx >= len(plan):
        return "synthesizer"

    agent = plan[step_idx].get("agent", "synthesizer")
    return agent


def build_agent_graph() -> StateGraph:
    """Build the LangGraph state machine for multi-agent orchestration."""
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("rag", rag_node)
    graph.add_node("scoring", scoring_node)
    graph.add_node("forecast", forecast_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.set_entry_point("planner")
    graph.add_conditional_edges("planner", route_step, {
        "rag": "rag",
        "scoring": "scoring",
        "forecast": "forecast",
        "synthesizer": "synthesizer",
    })
    graph.add_conditional_edges("rag", route_step, {
        "rag": "rag",
        "scoring": "scoring",
        "forecast": "forecast",
        "synthesizer": "synthesizer",
    })
    graph.add_conditional_edges("scoring", route_step, {
        "rag": "rag",
        "scoring": "scoring",
        "forecast": "forecast",
        "synthesizer": "synthesizer",
    })
    graph.add_conditional_edges("forecast", route_step, {
        "rag": "rag",
        "scoring": "scoring",
        "forecast": "forecast",
        "synthesizer": "synthesizer",
    })
    graph.add_edge("synthesizer", END)

    return graph.compile()
