"""Model retraining script for PATHwise air quality classification."""

from pathlib import Path
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


def train_and_save_model() -> None:
    """Train RandomForestClassifier on dataset and save model artifact."""
    current_dir = Path(__file__).resolve().parent
    dataset_path = current_dir / "updated_pollution_dataset.csv"
    output_path = current_dir / "air_quality_model.pkl"

    data = pd.read_csv(dataset_path)
    label_encoder = LabelEncoder()
    data["Air Quality"] = label_encoder.fit_transform(data["Air Quality"])

    features = [
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
    x = data[features]
    y = data["Air Quality"]

    x_train, _, y_train, _ = train_test_split(
        x, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(x_train, y_train)

    joblib.dump(model, output_path)
    print(f"Model saved to {output_path}")
    print(f"Model classes: {model.classes_}")
    print(f"Label encoder mapping: {dict(enumerate(label_encoder.classes_))}")


if __name__ == "__main__":
    train_and_save_model()
