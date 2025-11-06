"""LLM evaluation metrics — quality, faithfulness, toxicity, citations."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass
class MetricResult:
    score: float
    explanation: str
    details: dict = None

    def __post_init__(self):
        self.details = self.details or {}


def answer_relevance(question: str, answer: str) -> MetricResult:
    """Heuristic relevance check: does the answer address key terms from the question?"""
    q_tokens = set(question.lower().split())
    a_tokens = set(answer.lower().split())
    overlap = q_tokens & a_tokens
    # Remove stop words from consideration
    stop_words = {"the", "a", "is", "in", "of", "for", "to", "and", "what", "how", "which", "does", "are"}
    meaningful_q = q_tokens - stop_words
    meaningful_overlap = overlap - stop_words
    score = len(meaningful_overlap) / max(len(meaningful_q), 1)
    return MetricResult(
        score=min(score, 1.0),
        explanation=f"Keyword overlap: {len(meaningful_overlap)}/{len(meaningful_q)} question terms found in answer",
    )


def faithfulness(answer: str, context: str) -> MetricResult:
    """Check if claims in the answer are supported by the context."""
    answer_sentences = [s.strip() for s in answer.split(".") if len(s.strip()) > 10]
    if not answer_sentences:
        return MetricResult(score=1.0, explanation="No claims to verify")

    supported = 0
    for sentence in answer_sentences:
        key_words = set(sentence.lower().split()) - {"the", "a", "is", "in", "of", "and", "to"}
        context_words = set(context.lower().split())
        overlap = len(key_words & context_words) / max(len(key_words), 1)
        if overlap > 0.3:
            supported += 1

    score = supported / len(answer_sentences)
    return MetricResult(
        score=score,
        explanation=f"{supported}/{len(answer_sentences)} claims grounded in context",
    )


def toxicity_score(text: str) -> MetricResult:
    """Keyword-based toxicity check."""
    toxic_patterns = [
        r"\b(hate|kill|destroy|attack|stupid|idiot|worst)\b",
        r"\b(discriminat|racist|sexist)\w*\b",
    ]
    findings = []
    for pattern in toxic_patterns:
        matches = re.findall(pattern, text.lower())
        findings.extend(matches)

    score = min(len(findings) * 0.2, 1.0)
    return MetricResult(
        score=score,
        explanation=f"Found {len(findings)} potentially toxic terms" if findings else "No toxic content detected",
        details={"flagged_terms": findings},
    )


def citation_accuracy(answer: str) -> MetricResult:
    """Check if the answer includes source citations."""
    citation_pattern = r"\[Source:.*?\]|\[[\d]+\]|\(Source:.*?\)"
    citations = re.findall(citation_pattern, answer)
    sentences = [s for s in answer.split(".") if len(s.strip()) > 10]
    claim_count = max(len(sentences), 1)

    score = min(len(citations) / claim_count, 1.0) if citations else 0.0
    return MetricResult(
        score=score,
        explanation=f"{len(citations)} citations found for ~{claim_count} claims",
        details={"citations_found": len(citations)},
    )
