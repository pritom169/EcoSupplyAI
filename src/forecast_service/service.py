"""Forecast Service FastAPI — Scope 3 emission predictions with PyTorch."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import structlog
from fastapi import BackgroundTasks, FastAPI, HTTPException
from opentelemetry import trace
from pydantic import BaseModel, Field

from src.forecast_service.predict import EmissionPredictor

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
app = FastAPI(title="EcoSupplyAI Forecast Service", version="0.1.0")

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "emission_history.csv"
MODEL_PATH = "checkpoints/emission_model.pt"

predictor = EmissionPredictor(MODEL_PATH if Path(MODEL_PATH).exists() else None)


class PredictRequest(BaseModel):
    supplier_id: str = Field(..., examples=["SUP-001"])
    months_ahead: int = Field(default=6, ge=1, le=24)


@app.post("/forecast/predict")
async def predict_emissions(request: PredictRequest) -> dict:
    with tracer.start_as_current_span("forecast.predict") as span:
        span.set_attribute("supplier.id", request.supplier_id)

        if not DATA_PATH.exists():
            raise HTTPException(status_code=500, detail="Emission data not found")

        df = pd.read_csv(DATA_PATH)
        supplier_df = df[df["supplier_id"] == request.supplier_id].sort_values("month")

        if len(supplier_df) == 0:
            raise HTTPException(status_code=404, detail=f"No data for supplier {request.supplier_id}")

        result = predictor.predict_with_confidence(
            supplier_df.tail(12), request.supplier_id, request.months_ahead
        )

        return {
            "supplier_id": result.supplier_id,
            "dates": result.dates,
            "predictions": result.predictions,
            "lower_bound": result.lower_bound,
            "upper_bound": result.upper_bound,
            "trend": result.trend,
        }


@app.post("/forecast/train")
async def trigger_training(background_tasks: BackgroundTasks, supplier_id: str = "SUP-001") -> dict:
    from src.forecast_service.train import train_model

    background_tasks.add_task(train_model, data_path=str(DATA_PATH), supplier_id=supplier_id)
    return {"status": "training_started", "supplier_id": supplier_id}


@app.get("/forecast/history/{supplier_id}")
async def get_emission_history(supplier_id: str) -> dict:
    if not DATA_PATH.exists():
        raise HTTPException(status_code=500, detail="Emission data not found")
    df = pd.read_csv(DATA_PATH)
    supplier_df = df[df["supplier_id"] == supplier_id].sort_values("month")
    if len(supplier_df) == 0:
        raise HTTPException(status_code=404, detail=f"No data for supplier {supplier_id}")
    return {"supplier_id": supplier_id, "data": supplier_df.to_dict(orient="records")}


@app.get("/forecast/model-info")
async def model_info() -> dict:
    return {
        "model_loaded": predictor.model is not None,
        "model_path": MODEL_PATH,
        "architecture": "EmissionLSTM" if predictor.model else "linear_trend_fallback",
    }


@app.get("/forecast/health")
async def health() -> dict:
    return {"status": "healthy", "service": "forecast-service"}


@app.get("/forecast/ready")
async def ready() -> dict:
    return {"status": "ready"}
