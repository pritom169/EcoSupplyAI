"""Training script for emission forecasting models."""

from __future__ import annotations

import argparse
from pathlib import Path

import structlog
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader

from src.forecast_service.dataset import EmissionDataset
from src.forecast_service.model import EmissionLSTM

logger = structlog.get_logger(__name__)

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "emission_history.csv"


def train_model(
    data_path: str = str(DEFAULT_DATA_PATH),
    supplier_id: str = "SUP-001",
    epochs: int = 100,
    batch_size: int = 32,
    lr: float = 0.001,
    hidden_size: int = 64,
    num_layers: int = 2,
    patience: int = 10,
    save_path: str = "checkpoints/emission_model.pt",
) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("train.start", device=str(device), supplier_id=supplier_id)

    import pandas as pd
    df = pd.read_csv(data_path)
    supplier_df = df[df["supplier_id"] == supplier_id].sort_values("month").reset_index(drop=True)

    train_ds, val_ds, test_ds = EmissionDataset.train_val_test_split(
        supplier_df, sequence_length=6, forecast_horizon=1
    )
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    model = EmissionLSTM(
        input_size=4, hidden_size=hidden_size, num_layers=num_layers
    ).to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = ReduceLROnPlateau(optimizer, mode="min", patience=5, factor=0.5)

    best_val_loss = float("inf")
    epochs_without_improvement = 0
    history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}

    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0.0
        for x_batch, y_batch in train_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            output = model(x_batch).squeeze()
            loss = criterion(output, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()

        train_loss /= max(len(train_loader), 1)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x_batch, y_batch in val_loader:
                x_batch, y_batch = x_batch.to(device), y_batch.to(device)
                output = model(x_batch).squeeze()
                val_loss += criterion(output, y_batch).item()
        val_loss /= max(len(val_loader), 1)

        scheduler.step(val_loss)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_without_improvement = 0
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            torch.save({
                "model_state_dict": model.state_dict(),
                "scaler": train_ds.scaler,
                "config": {"hidden_size": hidden_size, "num_layers": num_layers},
            }, save_path)
        else:
            epochs_without_improvement += 1

        if epoch % 10 == 0:
            logger.info("train.epoch", epoch=epoch, train_loss=round(train_loss, 4), val_loss=round(val_loss, 4))

        if epochs_without_improvement >= patience:
            logger.info("train.early_stop", epoch=epoch)
            break

    return {"best_val_loss": best_val_loss, "epochs_trained": epoch + 1, "model_path": save_path}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(DEFAULT_DATA_PATH))
    parser.add_argument("--supplier", default="SUP-001")
    parser.add_argument("--epochs", type=int, default=100)
    args = parser.parse_args()
    result = train_model(data_path=args.data, supplier_id=args.supplier, epochs=args.epochs)
    print(result)
