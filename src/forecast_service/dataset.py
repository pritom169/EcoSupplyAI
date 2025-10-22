"""PyTorch Dataset for emission time series data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch.utils.data import Dataset


class EmissionDataset(Dataset):
    """Sliding window dataset for emission forecasting."""

    FEATURE_COLS = ["scope3_emissions_tons", "energy_consumption_mwh", "transport_km", "waste_tons"]
    TARGET_COL = "scope3_emissions_tons"

    def __init__(
        self,
        data: pd.DataFrame,
        sequence_length: int = 12,
        forecast_horizon: int = 1,
        scaler: StandardScaler | None = None,
    ) -> None:
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon

        features = data[self.FEATURE_COLS].values.astype(np.float32)
        targets = data[[self.TARGET_COL]].values.astype(np.float32)

        # Normalise features
        self.scaler = scaler or StandardScaler()
        if scaler is None:
            features = self.scaler.fit_transform(features)
        else:
            features = self.scaler.transform(features)

        self.features = torch.tensor(features, dtype=torch.float32)
        self.targets = torch.tensor(targets, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.features) - self.sequence_length - self.forecast_horizon + 1

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.features[idx : idx + self.sequence_length]
        y = self.targets[idx + self.sequence_length : idx + self.sequence_length + self.forecast_horizon]
        return x, y.squeeze()

    @classmethod
    def from_csv(cls, path: str | Path, supplier_id: str, **kwargs) -> "EmissionDataset":
        df = pd.read_csv(path)
        supplier_df = df[df["supplier_id"] == supplier_id].sort_values("month").reset_index(drop=True)
        if len(supplier_df) == 0:
            raise ValueError(f"No data found for supplier {supplier_id}")
        return cls(supplier_df, **kwargs)

    @classmethod
    def train_val_test_split(
        cls, data: pd.DataFrame, train_ratio: float = 0.7, val_ratio: float = 0.15, **kwargs
    ) -> tuple["EmissionDataset", "EmissionDataset", "EmissionDataset"]:
        n = len(data)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        train_ds = cls(data.iloc[:train_end], **kwargs)
        val_ds = cls(data.iloc[train_end:val_end], scaler=train_ds.scaler, **kwargs)
        test_ds = cls(data.iloc[val_end:], scaler=train_ds.scaler, **kwargs)
        return train_ds, val_ds, test_ds
