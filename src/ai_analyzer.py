from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import requests

from src.config import AISettings


class VisionAnalyzer:
    def __init__(self, settings: AISettings) -> None:
        self.settings = settings

    def analyze_image(self, image_path: str | Path, prompt: str) -> str:
        if not self.settings.api_key:
            raise RuntimeError("AI API key is empty in config.yaml")
        if self.settings.provider != "openai_compatible":
            raise RuntimeError(f"Unsupported AI provider: {self.settings.provider}")

        image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
        payload = {
            "model": self.settings.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        url = self.settings.base_url.rstrip("/") + "/chat/completions"

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.settings.timeout_sec,
                verify=self.settings.verify_ssl,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"AI request failed: {exc}") from exc

        return self._extract_text(response.json())

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("AI response did not contain choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            text = "\n".join(part.strip() for part in parts if part.strip())
            if text:
                return text
        raise RuntimeError("AI response text could not be extracted")
