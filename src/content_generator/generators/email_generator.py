"""Email draft generator for supplier communications."""

from __future__ import annotations

from pydantic import BaseModel
from openai import AsyncAzureOpenAI

EMAIL_SYSTEM_PROMPT = """You are a professional email writer for a procurement sustainability team.
Write clear, professional, and actionable emails. Be concise but thorough."""


class EmailDraft(BaseModel):
    subject: str
    body: str
    tone: str
    recipients_suggestion: str


class EmailGenerator:
    def __init__(self, client: AsyncAzureOpenAI, model: str = "gpt-4o") -> None:
        self.client = client
        self.model = model

    async def generate_onboarding_email(self, supplier: dict) -> EmailDraft:
        prompt = f"""Draft a welcome/onboarding email for a new supplier:
Name: {supplier.get('name')}
Country: {supplier.get('country')}
Industry: {supplier.get('industry')}

The email should welcome them, outline next steps (document submission, ESG assessment, code of conduct review), and set expectations."""

        content = await self._generate(prompt)
        return EmailDraft(
            subject=f"Welcome to Our Supplier Network - {supplier.get('name')}",
            body=content,
            tone="professional, welcoming",
            recipients_suggestion=f"Procurement contact at {supplier.get('name')}",
        )

    async def generate_audit_request(self, supplier: dict, findings: list[str]) -> EmailDraft:
        findings_text = "\n".join(f"- {f}" for f in findings)
        prompt = f"""Draft an audit follow-up email for:
Supplier: {supplier.get('name')}
Findings:
{findings_text}

Request corrective actions with a 30-day deadline. Be firm but professional."""

        content = await self._generate(prompt)
        return EmailDraft(
            subject=f"Audit Findings & Corrective Action Required - {supplier.get('name')}",
            body=content,
            tone="professional, firm",
            recipients_suggestion=f"Compliance officer at {supplier.get('name')}",
        )

    async def _generate(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": EMAIL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1024,
        )
        return response.choices[0].message.content or ""
