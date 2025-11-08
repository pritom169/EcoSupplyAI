"""Tests for PII filtering middleware."""

from __future__ import annotations

import re

import pytest

# Simple PII patterns for testing (mirrors the middleware logic)
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"\+?\d{1,4}[\s-]?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,9}")
CC_PATTERN = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")


class TestPIIDetection:
    """Test PII detection patterns."""

    def test_detects_email(self) -> None:
        text = "Contact john.doe@example.com for details."
        assert EMAIL_PATTERN.search(text) is not None

    def test_detects_phone(self) -> None:
        text = "Call +49 30 12345678 for support."
        assert PHONE_PATTERN.search(text) is not None

    def test_detects_credit_card(self) -> None:
        text = "Card number: 4532 1234 5678 9012"
        assert CC_PATTERN.search(text) is not None

    def test_no_false_positive_on_clean_text(self) -> None:
        text = "The CSRD requires companies to report ESG metrics annually."
        assert EMAIL_PATTERN.search(text) is None
        assert CC_PATTERN.search(text) is None


class TestPIIRedaction:
    """Test PII redaction (replacement)."""

    def test_redacts_email(self) -> None:
        text = "Email: user@company.de"
        redacted = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
        assert "user@company.de" not in redacted
        assert "[EMAIL_REDACTED]" in redacted

    def test_redacts_credit_card(self) -> None:
        text = "Card: 1234-5678-9012-3456"
        redacted = CC_PATTERN.sub("[CC_REDACTED]", text)
        assert "1234-5678-9012-3456" not in redacted

    def test_preserves_non_pii_content(self) -> None:
        text = "Supplier SUP-001 has an ESG score of 78.5."
        redacted = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
        redacted = CC_PATTERN.sub("[CC_REDACTED]", redacted)
        assert redacted == text
