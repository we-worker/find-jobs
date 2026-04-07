from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AISettings:
    provider: str
    base_url: str
    api_key: str
    model: str
    group: str
    stream: bool
    temperature: float
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    timeout_sec: float
    verify_ssl: bool


@dataclass
class Settings:
    stream_url: str
    stream_verify_ssl: bool
    stream_username: str
    stream_password: str
    hotkey: str
    server_host: str
    server_port: int
    capture_frame_count: int
    capture_timeout_sec: float
    output_dir: Path
    history_limit: int
    analysis_prompt: str
    ai: AISettings


def _ensure_output_dirs(output_dir: Path) -> None:
    for child in ("captures", "rectified", "debug", "results"):
        (output_dir / child).mkdir(parents=True, exist_ok=True)


def load_settings(path: str | Path) -> Settings:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    ai_raw: dict[str, Any] = raw.get("ai", {})
    output_dir = Path(raw.get("output_dir", "data"))

    settings = Settings(
        stream_url=raw.get("stream_url", ""),
        stream_verify_ssl=bool(raw.get("stream_verify_ssl", False)),
        stream_username=raw.get("stream_username", ""),
        stream_password=raw.get("stream_password", ""),
        hotkey=raw.get("hotkey", "ctrl+alt+s"),
        server_host=raw.get("server_host", "0.0.0.0"),
        server_port=int(raw.get("server_port", 8000)),
        capture_frame_count=int(raw.get("capture_frame_count", 8)),
        capture_timeout_sec=float(raw.get("capture_timeout_sec", 1.2)),
        output_dir=output_dir,
        history_limit=int(raw.get("history_limit", 20)),
        analysis_prompt=raw.get("analysis_prompt", "").strip(),
        ai=AISettings(
            provider=ai_raw.get("provider", "openai_compatible"),
            base_url=ai_raw.get("base_url", "https://api.openai.com/v1"),
            api_key=ai_raw.get("api_key", ""),
            model=ai_raw.get("model", "gpt-4.1-mini"),
            group=ai_raw.get("group", "default"),
            stream=bool(ai_raw.get("stream", True)),
            temperature=float(ai_raw.get("temperature", 0.7)),
            top_p=float(ai_raw.get("top_p", 1.0)),
            frequency_penalty=float(ai_raw.get("frequency_penalty", 0.0)),
            presence_penalty=float(ai_raw.get("presence_penalty", 0.0)),
            timeout_sec=float(ai_raw.get("timeout_sec", 30)),
            verify_ssl=bool(ai_raw.get("verify_ssl", False)),
        ),
    )
    _ensure_output_dirs(settings.output_dir)
    return settings
