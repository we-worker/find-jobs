from __future__ import annotations

import threading
from typing import Optional

from src.models import AnalysisRecord


class AppStateStore:
    def __init__(self, history_limit: int) -> None:
        self._lock = threading.Lock()
        self._history_limit = history_limit
        self._status = "idle"
        self._message = "Ready"
        self._latest: Optional[AnalysisRecord] = None
        self._history: list[AnalysisRecord] = []

    def set_status(self, status: str, message: str) -> None:
        with self._lock:
            self._status = status
            self._message = message

    def save_record(self, record: AnalysisRecord) -> None:
        with self._lock:
            self._latest = record
            self._history.insert(0, record)
            self._history = self._history[: self._history_limit]

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            return {"status": self._status, "message": self._message}

    def latest(self) -> Optional[dict]:
        with self._lock:
            return self._latest.to_dict() if self._latest else None

    def history(self) -> list[dict]:
        with self._lock:
            return [record.to_dict() for record in self._history]
