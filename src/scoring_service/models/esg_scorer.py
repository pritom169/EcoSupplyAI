"""ESG Scoring model using scikit-learn with feature importance explanations."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler


class ESGScorer:
    """Gradient Boosting classifier for supplier ESG risk level prediction."""

    FEATURES = [
        "carbon_emissions_tons",
        "renewable_energy_pct",
        "waste_recycling_pct",
        "labor_score",
        "governance_score",
        "employee_count",
        "certifications_count",
        "emission_intensity",  # emissions / revenue
    ]
    RISK_LEVELS = ["low", "medium", "high", "critical"]

    def __init__(self) -> None:
        self.model = GradientBoostingClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42
        )
        self.scaler = StandardScaler()
        self._is_fitted = False

    def _extract_features(self, supplier: dict) -> np.ndarray:
        revenue = supplier.get("annual_revenue", 1)
        emissions = supplier.get("carbon_emissions_tons", 0)
        return np.array([
            emissions,
            supplier.get("renewable_energy_pct", 0),
            supplier.get("waste_recycling_pct", 0),
            supplier.get("labor_score", 50),
            supplier.get("governance_score", 50),
            supplier.get("employee_count", 100),
            len(supplier.get("certifications", [])),
            emissions / max(revenue, 1) * 1_000_000,  # emission intensity
        ]).reshape(1, -1)

    def score_supplier(self, supplier: dict) -> dict:
        """Calculate ESG score using weighted formula (no ML model needed for basic scoring)."""
        env = supplier.get("environmental_score", 50)
        soc = supplier.get("labor_score", 50)
        gov = supplier.get("governance_score", 50)

        composite = round(env * 0.4 + soc * 0.3 + gov * 0.3, 1)

        if composite >= 85:
            risk_level = "low"
        elif composite >= 70:
            risk_level = "medium"
        elif composite >= 50:
            risk_level = "high"
        else:
            risk_level = "critical"

        return {
            "composite_score": composite,
            "risk_level": risk_level,
            "breakdown": {
                "environmental": {"score": env, "weight": 0.4, "weighted": round(env * 0.4, 1)},
                "social": {"score": soc, "weight": 0.3, "weighted": round(soc * 0.3, 1)},
                "governance": {"score": gov, "weight": 0.3, "weighted": round(gov * 0.3, 1)},
            },
            "contributing_factors": self._get_contributing_factors(supplier),
        }

    def _get_contributing_factors(self, supplier: dict) -> list[dict]:
        factors = []
        if supplier.get("renewable_energy_pct", 0) < 30:
            factors.append({"factor": "Low renewable energy", "impact": "negative", "value": supplier["renewable_energy_pct"]})
        if supplier.get("renewable_energy_pct", 0) >= 80:
            factors.append({"factor": "High renewable energy", "impact": "positive", "value": supplier["renewable_energy_pct"]})
        if supplier.get("waste_recycling_pct", 0) < 50:
            factors.append({"factor": "Low waste recycling rate", "impact": "negative", "value": supplier["waste_recycling_pct"]})
        if len(supplier.get("certifications", [])) >= 4:
            factors.append({"factor": "Strong certification portfolio", "impact": "positive", "value": len(supplier["certifications"])})
        if supplier.get("carbon_emissions_tons", 0) > 10000:
            factors.append({"factor": "High absolute emissions", "impact": "negative", "value": supplier["carbon_emissions_tons"]})
        return factors

    def save(self, path: str) -> None:
        joblib.dump({"model": self.model, "scaler": self.scaler}, path)

    def load(self, path: str) -> None:
        data = joblib.load(path)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self._is_fitted = True
