"""PII detection and redaction using Microsoft Presidio."""

from __future__ import annotations

from typing import Any

import structlog
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = structlog.get_logger(__name__)

# Lazily initialised singletons (Presidio models are heavy)
_analyzer: AnalyzerEngine | None = None
_anonymizer: AnonymizerEngine | None = None

SUPPORTED_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "PERSON",
    "LOCATION",
    "IP_ADDRESS",
]


def _get_analyzer() -> AnalyzerEngine:
    global _analyzer
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
    return _analyzer


def _get_anonymizer() -> AnonymizerEngine:
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer


class PIIFilter:
    def __init__(self, enabled: bool = True, language: str = "en") -> None:
        self.enabled = enabled
        self.language = language

    def detect(self, text: str) -> list[dict[str, Any]]:
        if not self.enabled or not text:
            return []
        analyzer = _get_analyzer()
        results = analyzer.analyze(
            text=text,
            entities=SUPPORTED_ENTITIES,
            language=self.language,
        )
        detections = [
            {
                "entity_type": r.entity_type,
                "score": round(r.score, 3),
                "start": r.start,
                "end": r.end,
            }
            for r in results
            if r.score >= 0.7
        ]
        if detections:
            logger.warning(
                "pii.detected",
                count=len(detections),
                types=[d["entity_type"] for d in detections],
            )
        return detections

    def redact(self, text: str) -> str:
        if not self.enabled or not text:
            return text
        analyzer = _get_analyzer()
        anonymizer = _get_anonymizer()
        analysis_results = analyzer.analyze(
            text=text,
            entities=SUPPORTED_ENTITIES,
            language=self.language,
        )
        high_confidence = [r for r in analysis_results if r.score >= 0.7]
        if not high_confidence:
            return text
        result = anonymizer.anonymize(
            text=text,
            analyzer_results=high_confidence,
            operators={
                "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL_REDACTED]"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE_REDACTED]"}),
                "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CC_REDACTED]"}),
            },
        )
        return result.text

    def sanitize_input(self, text: str) -> str:
        return self.redact(text)

    def sanitize_output(self, text: str) -> str:
        return self.redact(text)