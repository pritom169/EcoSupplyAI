"""Shared test fixtures for EcoSupplyAI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"


@pytest.fixture
def sample_suppliers() -> list[dict]:
    with open(SAMPLE_DATA_DIR / "suppliers.json") as f:
        return json.load(f)["suppliers"]


@pytest.fixture
def sample_regulations() -> list[dict]:
    with open(SAMPLE_DATA_DIR / "regulations.json") as f:
        return json.load(f)["regulations"]


@pytest.fixture
def sample_supplier() -> dict:
    return {
        "id": "SUP-TEST",
        "name": "Test Supplier GmbH",
        "country": "Germany",
        "industry": "Electronics & Components",
        "tier": 1,
        "carbon_emissions_tons": 500,
        "labor_score": 78,
        "governance_score": 82,
        "environmental_score": 71,
        "certifications": ["ISO 14001"],
        "annual_revenue_eur": 50_000_000,
        "employee_count": 300,
        "renewable_energy_pct": 55,
        "waste_recycling_pct": 70,
        "last_audit_date": "2025-06-15",
    }
