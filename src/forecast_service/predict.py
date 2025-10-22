"""Inference module for emission forecasting with confidence intervals via MC Dropout."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch

from src.forecast_service.model import EmissionLSTM


@dataclass
class ForecastResult:
    supplier_id: str
    dates: list[str]
    predictions: list[float]
    lower_bound: list[float]
    upper_bound: list[float]
    trend: str  # "increasing" | "decreasing" | "stable"


class EmissionPredictor:
    def __init__(self, model_path: str | None = None) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model: EmissionLSTM | None = None
        self.scaler = None
        if model_path:
            self.load_model(model_path)

    def load_model(self, path: str) -> None:
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        config = checkpoint["config"]
        self.model = EmissionLSTM(
            input_size=4, hidden_size=config["hidden_size"], num_layers=config["num_layers"]
        ).to(self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.scaler = checkpoint["scaler"]

    def predict_with_confidence(
        self,
        recent_data: pd.DataFrame,
        supplier_id: str,
        months_ahead: int = 6,
        mc_samples: int = 50,
    ) -> ForecastResult:
        """Generate forecasts with confidence intervals using MC Dropout."""
        if self.model is None:
            # Fallback: simple linear trend
            return self._linear_trend_forecast(recent_data, supplier_id, months_ahead)

        self.model.train()  # Enable dropout for MC Dropout
        features = recent_data[["scope3_emissions_tons", "energy_consumption_mwh", "transport_km", "waste_tons"]].values.astype(np.float32)
        if self.scaler:
            features = self.scaler.transform(features)

        x = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)

        all_predictions: list[list[float]] = []
        for _ in range(mc_samples):
            preds = []
            current_input = x.clone()
            for _ in range(months_ahead):
                with torch.no_grad():
                    pred = self.model(current_input).cpu().numpy()[0, 0]
                preds.append(float(pred))
                # Shift window
                new_step = current_input[:, -1:, :].clone()
                new_step[0, 0, 0] = pred
                current_input = torch.cat([current_input[:, 1:, :], new_step], dim=1)
            all_predictions.append(preds)

        self.model.eval()

        preds_array = np.array(all_predictions)
        mean_preds = preds_array.mean(axis=0).tolist()
        lower = np.percentile(preds_array, 5, axis=0).tolist()
        upper = np.percentile(preds_array, 95, axis=0).tolist()

        last_month = recent_data["month"].iloc[-1]
        dates = [f"forecast_month_{i+1}" for i in range(months_ahead)]
        trend = self._determine_trend(mean_preds)

        return ForecastResult(
            supplier_id=supplier_id, dates=dates, predictions=mean_preds,
            lower_bound=lower, upper_bound=upper, trend=trend,
        )

    def _linear_trend_forecast(self, data: pd.DataFrame, supplier_id: str, months_ahead: int) -> ForecastResult:
        """Simple linear regression fallback when no trained model is available."""
        emissions = data["scope3_emissions_tons"].values
        x = np.arange(len(emissions))
        coeffs = np.polyfit(x, emissions, deg=1)
        slope, intercept = coeffs

        future_x = np.arange(len(emissions), len(emissions) + months_ahead)
        predictions = (slope * future_x + intercept).tolist()
        std = float(np.std(emissions) * 0.2)
        lower = [p - 1.96 * std for p in predictions]
        upper = [p + 1.96 * std for p in predictions]
        dates = [f"forecast_month_{i+1}" for i in range(months_ahead)]
        trend = self._determine_trend(predictions)

        return ForecastResult(
            supplier_id=supplier_id, dates=dates, predictions=[round(p, 1) for p in predictions],
            lower_bound=[round(l, 1) for l in lower], upper_bound=[round(u, 1) for u in upper], trend=trend,
        )

    @staticmethod
    def _determine_trend(values: list[float]) -> str:
        if len(values) < 2:
            return "stable"
        change = (values[-1] - values[0]) / max(abs(values[0]), 1e-6)
        if change > 0.05:
            return "increasing"
        elif change < -0.05:
            return "decreasing"
        return "stable"
