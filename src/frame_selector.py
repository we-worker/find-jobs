from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from src.models import FrameScore
from src.screen_rectifier import detect_screen_quad, rectify_screen


class SelectionError(RuntimeError):
    pass


@dataclass
class FrameSelectionResult:
    index: int
    frame: np.ndarray
    rectified: np.ndarray
    debug_image: np.ndarray
    quad: np.ndarray
    scores: FrameScore


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    v_min = min(values)
    v_max = max(values)
    if abs(v_max - v_min) < 1e-6:
        return [1.0 for _ in values]
    return [(value - v_min) / (v_max - v_min) for value in values]


def _sharpness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _stability(quads: list[np.ndarray | None], index: int) -> float:
    current = quads[index]
    if current is None:
        return 0.0
    distances: list[float] = []
    for neighbor_index in (index - 1, index + 1):
        if neighbor_index < 0 or neighbor_index >= len(quads):
            continue
        neighbor = quads[neighbor_index]
        if neighbor is None:
            continue
        distances.append(float(np.linalg.norm(current - neighbor, axis=1).mean()))
    if not distances:
        return 0.5
    jitter = sum(distances) / len(distances)
    return 1.0 / (1.0 + jitter / 30.0)


def select_best_frame(frames: list[np.ndarray]) -> FrameSelectionResult:
    if not frames:
        raise SelectionError("No frames available for selection")

    detections = [detect_screen_quad(frame) for frame in frames]
    sharpness_raw = [_sharpness(frame) for frame in frames]
    quad_raw = [det.confidence if det else 0.0 for det in detections]
    quads = [det.quad if det else None for det in detections]
    stability_raw = [_stability(quads, idx) for idx in range(len(frames))]

    sharpness_scores = _normalize(sharpness_raw)
    quad_scores = _normalize(quad_raw)
    stability_scores = _normalize(stability_raw)

    best_index = -1
    best_total = -1.0
    best_score = None

    for idx, detection in enumerate(detections):
        if detection is None:
            continue
        total = (
            0.45 * sharpness_scores[idx]
            + 0.40 * quad_scores[idx]
            + 0.15 * stability_scores[idx]
        )
        if total > best_total:
            best_total = total
            best_index = idx
            best_score = FrameScore(
                sharpness=round(sharpness_scores[idx], 4),
                quad_confidence=round(quad_scores[idx], 4),
                stability=round(stability_scores[idx], 4),
                total=round(total, 4),
            )

    if best_index < 0 or best_score is None:
        raise SelectionError("Unable to detect a valid screen in any captured frame")

    chosen = detections[best_index]
    assert chosen is not None
    rectified = rectify_screen(frames[best_index], chosen.quad)
    return FrameSelectionResult(
        index=best_index,
        frame=frames[best_index],
        rectified=rectified,
        debug_image=chosen.overlay,
        quad=chosen.quad,
        scores=best_score,
    )
