from pathlib import Path

import pytest

from porch_alert.detection import load_labels


def test_load_labels_coco():
    root = Path(__file__).resolve().parents[1]
    labels = load_labels(root / "models" / "coco_labels.txt")
    assert labels[0] == "person"
    assert labels[2] == "car"


def test_create_detector_missing_model(tmp_path):
    from porch_alert.detection import create_detector

    labels = tmp_path / "labels.txt"
    labels.write_text("person\n")
    model = tmp_path / "missing.tflite"
    with pytest.raises(FileNotFoundError, match="TFLite model"):
        create_detector(model, labels, 0.4, ("person",))
