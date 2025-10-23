"""Sustainability report generator using Azure OpenAI."""

from __future__ import annotations

import structlog
from openai import AsyncAzureOpenAI

logger = structlog.get_logger(__name__)

REPORT_SYSTEM_PROMPT = """You are a professional sustainability report writer.
Generate well-structured, data-driven reports for corporate procurement teams.
Use formal language, include specific metrics, and provide actionable recommendations.
Format the output as clean Markdown with sections, tables, and bullet points."""


class SustainabilityReportGenerator:
    def __init__(self, client: AsyncAzureOpenAI, model: str = "gpt-4o") -> None:
        self.client = client
        self.model = model
        self.total_tokens = 0

    async def generate_quarterly_report(
        self, suppliers: list[dict], scores: list[dict], period: str = "Q4-2025"
    ) -> dict:
        supplier_summary = "\n".join(
            f"- {s['name']} ({s['country']}, {s['industry']}): "
            f"ESG={sc.get('composite_score', 'N/A')}, "
            f"Risk={sc.get('risk_level', 'N/A')}"
            for s, sc in zip(suppliers, scores)
        )

        prompt = f"""Generate a quarterly sustainability report for the following suppliers.
Period: {period}

Supplier Data:
{supplier_summary}

Include these sections:
1. Executive Summary (2-3 sentences)
2. Environmental Performance Overview (table with key metrics)
3. Risk Assessment Summary
4. Top Performers and Areas of Concern
5. Recommendations for Next Quarter"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=2048,
        )

        content = response.choices[0].message.content or ""
        if response.usage:
            self.total_tokens += response.usage.total_tokens

        return {
            "report": content,
            "period": period,
            "supplier_count": len(suppliers),
            "token_usage": response.usage.total_tokens if response.usage else 0,
        }
