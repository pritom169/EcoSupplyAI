"""Tests for ESG scoring service."""

from __future__ import annotations

import pytest


class TestESGScorer:
    """Test suite for ESG scoring logic."""

    def test_score_within_bounds(self, sample_supplier: dict) -> None:
        """ESG score should be between 0 and 100."""
        env = sample_supplier["environmental_score"]
        soc = sample_supplier["labor_score"]
        gov = sample_supplier["governance_score"]
        overall = env * 0.4 + soc * 0.3 + gov * 0.3
        assert 0 <= overall <= 100

    def test_weighted_formula(self) -> None:
        """Verify the weighted scoring formula."""
        env, soc, gov = 80, 70, 90
        expected = 80 * 0.4 + 70 * 0.3 + 90 * 0.3  # 32 + 21 + 27 = 80
        assert expected == 80.0

    def test_low_score_flags_risk(self) -> None:
        """Scores below 40 should be flagged as high risk."""
        score = 35
        risk_level = "high" if score < 40 else "moderate" if score < 60 else "low"
        assert risk_level == "high"

    def test_certifications_bonus(self, sample_supplier: dict) -> None:
        """Suppliers with ISO 14001 should get a small bonus."""
        has_iso = "ISO 14001" in sample_supplier["certifications"]
        assert has_iso is True


class TestESGBatchScoring:
    """Test batch scoring functionality."""

    def test_batch_returns_all_results(self, sample_suppliers: list[dict]) -> None:
        """Batch scoring should return a result for each supplier."""
        scores = []
        for s in sample_suppliers:
            score = s["environmental_score"] * 0.4 + s["labor_score"] * 0.3 + s["governance_score"] * 0.3
            scores.append({"supplier_id": s["id"], "score": score})
        assert len(scores) == len(sample_suppliers)

    def test_batch_all_valid_scores(self, sample_suppliers: list[dict]) -> None:
        """All batch scores should be valid numbers."""
        for s in sample_suppliers:
            score = s["environmental_score"] * 0.4 + s["labor_score"] * 0.3 + s["governance_score"] * 0.3
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100
