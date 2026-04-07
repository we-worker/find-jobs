from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import uvicorn

from src.ai_analyzer import VisionAnalyzer
from src.config import Settings, load_settings
from src.frame_selector import SelectionError, select_best_frame
from src.hotkey_listener import HotkeyListener
from src.models import AnalysisRecord
from src.state_store import AppStateStore
from src.stream_client import MjpegStreamClient, StreamCaptureError
from src.web_server import create_app


def _now_utc() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class AppRuntime:
    settings: Settings
    store: AppStateStore
    stream_client: MjpegStreamClient
    analyzer: VisionAnalyzer
    output_dir: Path
    hotkey_listener: Optional[HotkeyListener] = None
    app: object | None = None
    _job_lock: threading.Lock = field(default_factory=threading.Lock)

    def trigger_capture(self) -> bool:
        if not self._job_lock.acquire(blocking=False):
            self.store.set_status("busy", "A capture job is already running")
            return False
        worker = threading.Thread(target=self._run_capture_job, daemon=True)
        worker.start()
        return True

    def _run_capture_job(self) -> None:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        started_at = _now_utc()
        frames = []
        capture_path = None
        rectified_path = None
        debug_path = None
        stage = "capturing"
        stage_times: dict[str, float] = {}
        t0 = time.perf_counter()

        try:
            self.store.set_status("capturing", "Capturing frames from MJPEG stream")
            frames = self.stream_client.capture_frames(
                frame_count=self.settings.capture_frame_count,
                timeout_sec=self.settings.capture_timeout_sec,
            )
            stage_times["capture_sec"] = round(time.perf_counter() - t0, 3)

            stage = "rectifying"
            self.store.set_status("rectifying", "Selecting and rectifying screen")
            t1 = time.perf_counter()
            selection = select_best_frame(frames)
            capture_path = self.output_dir / "captures" / f"{run_id}.jpg"
            debug_path = self.output_dir / "debug" / f"{run_id}.jpg"
            rectified_path = self.output_dir / "rectified" / f"{run_id}.jpg"

            cv2.imwrite(str(capture_path), selection.frame)
            cv2.imwrite(str(debug_path), selection.debug_image)
            cv2.imwrite(str(rectified_path), selection.rectified)
            stage_times["rectify_sec"] = round(time.perf_counter() - t1, 3)

            stage = "analyzing"
            self.store.set_status("analyzing", "Sending corrected image to AI model")
            t2 = time.perf_counter()
            ai_text = self.analyzer.analyze_image(
                image_path=rectified_path,
                prompt=self.settings.analysis_prompt,
                fallback_image_path=capture_path,
            )
            stage_times["analyze_sec"] = round(time.perf_counter() - t2, 3)

            record = AnalysisRecord(
                record_id=run_id,
                created_at=started_at,
                status="success",
                summary_text=ai_text,
                raw_capture_path=self._relative_output(capture_path),
                rectified_path=self._relative_output(rectified_path),
                debug_path=self._relative_output(debug_path),
                selected_frame_index=selection.index,
                frame_count=len(frames),
                score_breakdown=selection.scores.to_dict(),
                timings=stage_times,
            )
            self._write_record(record)
            self.store.save_record(record)
            self.store.set_status("success", "Analysis completed")
        except (StreamCaptureError, SelectionError, RuntimeError, ValueError) as exc:
            if frames and capture_path is None:
                capture_path = self.output_dir / "captures" / f"{run_id}-error.jpg"
                cv2.imwrite(str(capture_path), frames[-1])
            record = AnalysisRecord(
                record_id=run_id,
                created_at=started_at,
                status="error",
                error_stage=stage,
                error_message=str(exc),
                raw_capture_path=self._relative_output(capture_path),
                rectified_path=self._relative_output(rectified_path),
                debug_path=self._relative_output(debug_path),
                timings=stage_times,
            )
            self._write_record(record)
            self.store.save_record(record)
            self.store.set_status("error", f"{stage}: {exc}")
        finally:
            self._job_lock.release()

    def _write_record(self, record: AnalysisRecord) -> None:
        target = self.output_dir / "results" / f"{record.record_id}.json"
        target.write_text(
            json.dumps(record.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _relative_output(self, path: Optional[Path]) -> Optional[str]:
        if not path:
            return None
        return path.relative_to(self.output_dir).as_posix()

    def shutdown(self) -> None:
        self.stream_client.stop()
        if self.hotkey_listener:
            self.hotkey_listener.stop()


def build_runtime(config_path: str = "config.yaml") -> AppRuntime:
    settings = load_settings(config_path)
    store = AppStateStore(history_limit=settings.history_limit)
    stream_client = MjpegStreamClient(
        stream_url=settings.stream_url,
        verify_ssl=settings.stream_verify_ssl,
        username=settings.stream_username,
        password=settings.stream_password,
        min_frame_count=1,
        frame_buffer_size=max(settings.capture_frame_count * 3, 24),
    )
    analyzer = VisionAnalyzer(settings.ai)
    runtime = AppRuntime(
        settings=settings,
        store=store,
        stream_client=stream_client,
        analyzer=analyzer,
        output_dir=settings.output_dir,
    )
    runtime.hotkey_listener = HotkeyListener(settings.hotkey, runtime.trigger_capture)
    runtime.app = create_app(settings, store, runtime)
    return runtime


def main() -> None:
    runtime = build_runtime()
    runtime.stream_client.start()
    runtime.hotkey_listener.start()
    print(f"Hotkey registered: {runtime.settings.hotkey}")
    print(
        f"Open LAN page: http://<your-pc-ip>:{runtime.settings.server_port} "
        f"or local page: http://127.0.0.1:{runtime.settings.server_port}"
    )
    try:
        uvicorn.run(
            runtime.app,
            host=runtime.settings.server_host,
            port=runtime.settings.server_port,
            log_level="info",
        )
    finally:
        runtime.shutdown()


if __name__ == "__main__":
    main()
