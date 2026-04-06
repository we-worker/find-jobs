from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import requests
from requests.auth import HTTPBasicAuth


class StreamCaptureError(RuntimeError):
    pass


@dataclass
class MjpegStreamClient:
    stream_url: str
    verify_ssl: bool
    username: str = ""
    password: str = ""
    connect_timeout_sec: float = 3.0
    read_timeout_sec: float = 3.0
    chunk_size: int = 4096
    min_frame_count: int = 1
    frame_buffer_size: int = 24

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._frame_buffer: deque[np.ndarray] = deque(maxlen=self.frame_buffer_size)
        self._last_error: Optional[str] = None
        self._session: Optional[requests.Session] = None
        self._response: Optional[requests.Response] = None

    def capture_frames(self, frame_count: int, timeout_sec: float) -> list[np.ndarray]:
        self.start()
        deadline = time.time() + timeout_sec

        while time.time() <= deadline:
            frames = self._snapshot_frames(frame_count)
            if len(frames) >= frame_count:
                return frames
            if len(frames) >= self.min_frame_count and time.time() + 0.15 > deadline:
                return frames
            time.sleep(0.05)

        frames = self._snapshot_frames(frame_count)
        if frames:
            return frames
        if self._last_error:
            raise StreamCaptureError(f"Unable to capture frames from stream: {self._last_error}")
        raise StreamCaptureError("No frames were decoded from the MJPEG stream")

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._response is not None:
            self._response.close()
            self._response = None
        if self._session is not None:
            self._session.close()
            self._session = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    @staticmethod
    def _decode_frame(jpeg_bytes: bytes) -> np.ndarray | None:
        array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        return cv2.imdecode(array, cv2.IMREAD_COLOR)

    def _build_auth(self) -> HTTPBasicAuth | None:
        if not self.username:
            return None
        return HTTPBasicAuth(self.username, self.password)

    def _snapshot_frames(self, frame_count: int) -> list[np.ndarray]:
        with self._lock:
            frames = list(self._frame_buffer)
        if not frames:
            return []
        return frames[-frame_count:]

    def _reader_loop(self) -> None:
        while self._running.is_set():
            buffer = bytearray()
            try:
                if self._session is None:
                    self._session = requests.Session()
                self._response = self._session.get(
                    self.stream_url,
                    stream=True,
                    timeout=(self.connect_timeout_sec, self.read_timeout_sec),
                    verify=self.verify_ssl,
                    auth=self._build_auth(),
                )
                self._response.raise_for_status()
                self._last_error = None

                for chunk in self._response.iter_content(chunk_size=self.chunk_size):
                    if not self._running.is_set():
                        break
                    if not chunk:
                        continue
                    buffer.extend(chunk)
                    while True:
                        start = buffer.find(b"\xff\xd8")
                        end = buffer.find(b"\xff\xd9", start + 2)
                        if start == -1 or end == -1:
                            break
                        jpeg_bytes = bytes(buffer[start : end + 2])
                        del buffer[: end + 2]
                        frame = self._decode_frame(jpeg_bytes)
                        if frame is not None:
                            with self._lock:
                                self._frame_buffer.append(frame)
            except requests.RequestException as exc:
                self._last_error = str(exc)
                time.sleep(0.5)
            finally:
                if self._response is not None:
                    self._response.close()
                    self._response = None
