"""Machine learning inference module for PATHwise air quality classification."""

from pathlib import Path
from typing import Any
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

FEATURE_ORDER: list[str] = [
    "Temperature",
    "Humidity",
    "PM2.5",
    "PM10",
    "NO2",
    "SO2",
    "CO",
    "Proximity_to_Industrial_Areas",
    "Population_Density",
]

# Mapping based on LabelEncoder classes [Good, Hazardous, Moderate, Poor]
LABEL_MAP: dict[int, str] = {
    0: "Good",
    1: "Hazardous",
    2: "Moderate",
    3: "Poor",
}


def load_model(path: str) -> RandomForestClassifier:
    """Load pre-trained RandomForestClassifier from disk artifact."""
    model_path = Path(path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found at: {path}")
    model = joblib.load(model_path)
    if not isinstance(model, RandomForestClassifier):
        raise TypeError(f"Loaded model is not RandomForestClassifier: {type(model)}")
    return model


def _prepare_feature_dataframe(features: dict[str, Any]) -> pd.DataFrame:
    """Validate and format input feature dictionary into a 1-row DataFrame."""
    missing = [k for k in FEATURE_ORDER if k not in features]
    if missing:
        raise ValueError(f"Missing required feature keys: {missing}")
    row = [float(features[k]) for k in FEATURE_ORDER]
    return pd.DataFrame([row], columns=FEATURE_ORDER)


def classify_segment(model: RandomForestClassifier, features: dict[str, Any]) -> str:
    """Predict air quality class for a route segment using given features."""
    df = _prepare_feature_dataframe(features)
    raw_pred = model.predict(df)[0]
    if isinstance(raw_pred, (int, float, complex)) or hasattr(raw_pred, "item"):
        label = LABEL_MAP.get(int(raw_pred))
        if label is None:
            raise ValueError(f"Unmapped model prediction index: {raw_pred}")
        return label
    label_str = str(raw_pred).strip().capitalize()
    if label_str not in {"Good", "Moderate", "Poor", "Hazardous"}:
        raise ValueError(f"Unexpected prediction label: {label_str}")
    return label_str


def get_top_contributing_factors(
    model: RandomForestClassifier, top_n: int = 3
) -> list[dict[str, str]]:
    """Return top feature importances from trained model."""
    if not hasattr(model, "feature_importances_"):
        return []
    importances = model.feature_importances_
    ranked_indices = importances.argsort()[::-1][:top_n]
    return [
        {"factor": FEATURE_ORDER[i], "importance": f"{importances[i]:.4f}"}
        for i in ranked_indices
    ]
