"""TensorFlow Lite object detection for porch targets (e.g. person)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class Detection:
    class_id: int
    label: str
    score: float


def load_labels(path: Path) -> dict[int, str]:
    """Load COCO-style label file with or without index prefixes."""
    labels: dict[int, str] = {}
    with path.open(encoding="utf-8") as f:
        for row_number, content in enumerate(f):
            pair = re.split(r"[:\s]+", content.strip(), maxsplit=1)
            if len(pair) == 2 and pair[0].strip().isdigit():
                labels[int(pair[0])] = pair[1].strip()
            elif content.strip():
                labels[row_number] = pair[0].strip()
    return labels


class TfliteDetector:
    """TFLite SSD detector — same outputs as detect.tflite from the garage project."""

    def __init__(
        self,
        model_path: Path,
        labels_path: Path,
        threshold: float,
        target_labels: tuple[str, ...],
    ) -> None:
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            from tensorflow.lite import Interpreter  # type: ignore[no-redef]

        self._threshold = threshold
        self._target_labels = frozenset(label.lower() for label in target_labels)
        self._labels = load_labels(labels_path)
        self._interpreter = Interpreter(str(model_path))
        self._interpreter.allocate_tensors()
        _, self._input_height, self._input_width, _ = self._interpreter.get_input_details()[
            0
        ]["shape"]

    def detect(self, image: Image.Image) -> list[Detection]:
        resized = image.convert("RGB").resize(
            (self._input_width, self._input_height), Image.Resampling.LANCZOS
        )
        input_data = np.asarray(resized, dtype=np.uint8)
        self._set_input_tensor(input_data)
        self._interpreter.invoke()

        classes = self._get_output_tensor(1)
        scores = self._get_output_tensor(2)
        count = int(self._get_output_tensor(3))

        results: list[Detection] = []
        for i in range(count):
            score = float(scores[i])
            if score < self._threshold:
                continue
            class_id = int(classes[i])
            label = self._labels.get(class_id, str(class_id))
            results.append(Detection(class_id=class_id, label=label, score=score))
        return results

    def filter_targets(self, detections: list[Detection]) -> list[Detection]:
        return [d for d in detections if d.label.lower() in self._target_labels]

    def has_target(self, image: Image.Image) -> tuple[bool, list[Detection]]:
        detections = self.detect(image)
        targets = self.filter_targets(detections)
        return bool(targets), targets

    def _set_input_tensor(self, image: np.ndarray) -> None:
        tensor_index = self._interpreter.get_input_details()[0]["index"]
        input_tensor = self._interpreter.tensor(tensor_index)()[0]
        input_tensor[:, :] = image

    def _get_output_tensor(self, index: int) -> np.ndarray:
        output_details = self._interpreter.get_output_details()[index]
        return np.squeeze(self._interpreter.get_tensor(output_details["index"]))


def create_detector(
    model_path: Path,
    labels_path: Path,
    threshold: float,
    target_labels: tuple[str, ...],
) -> TfliteDetector:
    if not model_path.is_file():
        raise FileNotFoundError(f"TFLite model not found: {model_path}")
    if not labels_path.is_file():
        raise FileNotFoundError(f"Labels file not found: {labels_path}")
    return TfliteDetector(model_path, labels_path, threshold, target_labels)
