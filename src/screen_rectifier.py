from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class ScreenDetection:
    quad: np.ndarray
    confidence: float
    overlay: np.ndarray


def order_points(points: np.ndarray) -> np.ndarray:
    points = points.astype(np.float32)
    summed = points.sum(axis=1)
    diff = np.diff(points, axis=1).reshape(-1)
    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = points[np.argmin(summed)]
    ordered[2] = points[np.argmax(summed)]
    ordered[1] = points[np.argmin(diff)]
    ordered[3] = points[np.argmax(diff)]
    return ordered


def _angle_score(quad: np.ndarray) -> float:
    total_error = 0.0
    for index in range(4):
        prev_pt = quad[index - 1]
        curr_pt = quad[index]
        next_pt = quad[(index + 1) % 4]
        v1 = prev_pt - curr_pt
        v2 = next_pt - curr_pt
        norm = np.linalg.norm(v1) * np.linalg.norm(v2)
        if norm == 0:
            return 0.0
        cosine = np.clip(np.dot(v1, v2) / norm, -1.0, 1.0)
        angle = np.degrees(np.arccos(cosine))
        total_error += abs(90.0 - angle)
    return max(0.0, 1.0 - total_error / 180.0)


def _quad_confidence(quad: np.ndarray, image_shape: tuple[int, int, int]) -> float:
    height, width = image_shape[:2]
    area = cv2.contourArea(quad.astype(np.float32))
    if area <= 0:
        return 0.0

    area_ratio = area / float(width * height)
    if area_ratio < 0.08:
        return 0.0

    ordered = order_points(quad)
    top = np.linalg.norm(ordered[1] - ordered[0])
    bottom = np.linalg.norm(ordered[2] - ordered[3])
    left = np.linalg.norm(ordered[3] - ordered[0])
    right = np.linalg.norm(ordered[2] - ordered[1])
    avg_width = max((top + bottom) / 2.0, 1.0)
    avg_height = max((left + right) / 2.0, 1.0)
    aspect = avg_width / avg_height

    area_score = min(area_ratio / 0.6, 1.0)
    angle = _angle_score(ordered)
    aspect_score = max(0.0, 1.0 - min(abs(aspect - 1.6), 1.6) / 1.6)
    return round(0.45 * area_score + 0.30 * angle + 0.25 * aspect_score, 4)


def detect_screen_quad(image: np.ndarray) -> Optional[ScreenDetection]:
    original = image.copy()
    height, width = image.shape[:2]
    scale = 1.0
    if width > 960:
        scale = 960.0 / width
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), dtype=np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    best_quad = None
    best_score = 0.0

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        quad = approx.reshape(4, 2).astype(np.float32)
        score = _quad_confidence(quad, image.shape)
        if score > best_score:
            best_score = score
            best_quad = quad

    if best_quad is None:
        return None

    best_quad = best_quad / scale
    overlay = original.copy()
    cv2.polylines(
        overlay,
        [best_quad.astype(np.int32)],
        isClosed=True,
        color=(0, 255, 0),
        thickness=3,
    )
    return ScreenDetection(
        quad=order_points(best_quad),
        confidence=best_score,
        overlay=overlay,
    )


def rectify_screen(image: np.ndarray, quad: np.ndarray) -> np.ndarray:
    ordered = order_points(quad)
    width_top = np.linalg.norm(ordered[1] - ordered[0])
    width_bottom = np.linalg.norm(ordered[2] - ordered[3])
    height_left = np.linalg.norm(ordered[3] - ordered[0])
    height_right = np.linalg.norm(ordered[2] - ordered[1])

    max_width = int(max(width_top, width_bottom))
    max_height = int(max(height_left, height_right))
    if max_width < 10 or max_height < 10:
        raise ValueError("Detected screen area is too small to rectify")

    destination = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(ordered, destination)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))
