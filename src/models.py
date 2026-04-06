from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class FrameScore:
    sharpness: float
    quad_confidence: float
    stability: float
    total: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class AnalysisRecord:
    record_id: str
    created_at: str
    status: str
    summary_text: str = ""
    raw_capture_path: Optional[str] = None
    rectified_path: Optional[str] = None
    debug_path: Optional[str] = None
    selected_frame_index: Optional[int] = None
    frame_count: Optional[int] = None
    score_breakdown: dict[str, float] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
    error_stage: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
