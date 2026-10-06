"""Tests for backend.ml_classifier module."""

from pathlib import Path
import pytest
from backend.ml_classifier import (
    FEATURE_ORDER,
    classify_segment,
    get_top_contributing_factors,
    load_model,
)

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "air_quality_model.pkl"


def test_load_model_and_print_classes(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify model loading and print model.classes_."""
    model = load_model(str(MODEL_PATH))
    assert model is not None
    print(f"model.classes_: {model.classes_}")


def test_classify_segment_with_sample_input() -> None:
    """Test sample input from original repo: [29.8, 59.1, 5.2, 17.9, 18.9, 9.2, 1.72, 6.3, 319]."""
    model = load_model(str(MODEL_PATH))
    sample_values = [29.8, 59.1, 5.2, 17.9, 18.9, 9.2, 1.72, 6.3, 319]
    features = dict(zip(FEATURE_ORDER, sample_values))

    label = classify_segment(model, features)
    print(f"Predicted class for sample input: {label}")
    assert label in {"Good", "Moderate", "Poor", "Hazardous"}
    assert label == "Moderate"


def test_classify_segment_missing_features() -> None:
    """Verify ValueError is raised when features dict is incomplete."""
    model = load_model(str(MODEL_PATH))
    incomplete_features = {"Temperature": 25.0, "Humidity": 50.0}
    with pytest.raises(ValueError, match="Missing required feature keys"):
        classify_segment(model, incomplete_features)


def test_load_model_file_not_found() -> None:
    """Verify FileNotFoundError when model path does not exist."""
    with pytest.raises(FileNotFoundError):
        load_model("/invalid/path/to/model.pkl")


def test_feature_contributing_factors() -> None:
    """Verify top contributing factors extraction from model."""
    model = load_model(str(MODEL_PATH))
    factors = get_top_contributing_factors(model, top_n=3)
    assert len(factors) == 3
    for f in factors:
        assert "factor" in f
        assert "importance" in f
