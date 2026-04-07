from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import requests

from src.config import AISettings


FALLBACK_ANALYSIS_PROMPT = (
    "请识别这张图片中的题目内容，并直接给出最终答案。"
    "如果图片里有选项，也请说明你选择的是哪一个。"
)


class VisionAnalyzer:
    def __init__(self, settings: AISettings) -> None:
        self.settings = settings

    def analyze_image(
        self,
        image_path: str | Path,
        prompt: str,
        fallback_image_path: str | Path | None = None,
    ) -> str:
        attempts: list[tuple[str | Path, str, bool]] = [
            (image_path, prompt, False),
            (image_path, FALLBACK_ANALYSIS_PROMPT, True),
        ]
        if fallback_image_path is not None:
            attempts.append((fallback_image_path, FALLBACK_ANALYSIS_PROMPT, True))

        last_error: Exception | None = None
        for attempt_image, attempt_prompt, minimal_payload in attempts:
            try:
                return self._analyze_image_internal(
                    image_path=attempt_image,
                    prompt=attempt_prompt,
                    minimal_payload=minimal_payload,
                )
            except RuntimeError as exc:
                last_error = exc
                if "did not receive a usable image input" not in str(exc).lower():
                    raise

        assert last_error is not None
        raise last_error

    def _analyze_image_internal(
        self,
        image_path: str | Path,
        prompt: str,
        minimal_payload: bool,
    ) -> str:
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
            "stream": True,
            "temperature": 0 if minimal_payload else self.settings.temperature,
        }
        if self.settings.group and not minimal_payload:
            payload["group"] = self.settings.group
        if not minimal_payload:
            payload["top_p"] = self.settings.top_p
            payload["frequency_penalty"] = self.settings.frequency_penalty
            payload["presence_penalty"] = self.settings.presence_penalty

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
                stream=True,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"AI request failed: {exc}") from exc

        if "text/event-stream" in (response.headers.get("content-type") or ""):
            text = self._extract_stream_text(response)
        else:
            text = self._extract_text(response.json())

        self._validate_analysis_text(text)
        return text

    @staticmethod
    def _extract_stream_text(response: requests.Response) -> str:
        parts: list[str] = []
        saw_chunk = False

        response.encoding = "utf-8"
        for raw_line in response.iter_lines(decode_unicode=False):
            if not raw_line:
                continue

            if isinstance(raw_line, bytes):
                line = raw_line.decode("utf-8", errors="replace").strip()
            else:
                line = str(raw_line).strip()

            if not line.startswith("data:"):
                continue

            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue

            saw_chunk = True
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue

            choices = payload.get("choices") or []
            for choice in choices:
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if isinstance(content, str) and content:
                    parts.append(content)

        text = "".join(parts).strip()
        if text:
            return text
        if saw_chunk:
            raise RuntimeError("AI stream returned chunks but no text content was found")
        raise RuntimeError("AI stream response was empty")

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        direct_text = payload.get("output_text")
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text.strip()

        output = payload.get("output")
        if isinstance(output, list):
            text = VisionAnalyzer._extract_text_from_output_items(output)
            if text:
                return text

        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError(
                f"AI response did not contain usable text; top-level keys: {sorted(payload.keys())}"
            )

        choice = choices[0]
        if isinstance(choice.get("text"), str) and choice["text"].strip():
            return choice["text"].strip()

        message = choice.get("message", {})
        text = VisionAnalyzer._extract_text_from_node(message)
        if text:
            return text

        raise RuntimeError(
            f"AI response text could not be extracted; top-level keys: {sorted(payload.keys())}"
        )

    @staticmethod
    def _extract_text_from_node(node: Any) -> str:
        if isinstance(node, str):
            return node.strip()

        if isinstance(node, list):
            parts = [VisionAnalyzer._extract_text_from_node(item) for item in node]
            return "\n".join(part for part in parts if part).strip()

        if isinstance(node, dict):
            preferred_keys = ("output_text", "text", "content")
            for key in preferred_keys:
                value = node.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict):
                    nested = VisionAnalyzer._extract_text_from_node(value)
                    if nested:
                        return nested
                if isinstance(value, list):
                    nested = VisionAnalyzer._extract_text_from_node(value)
                    if nested:
                        return nested

            if node.get("type") in {"text", "output_text"}:
                for key in ("text", "content", "value"):
                    value = node.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                    if isinstance(value, dict):
                        nested = VisionAnalyzer._extract_text_from_node(value)
                        if nested:
                            return nested

        return ""

    @staticmethod
    def _extract_text_from_output_items(items: list[Any]) -> str:
        parts: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                content_items = item.get("content")
                text = VisionAnalyzer._extract_text_from_node(content_items)
                if text:
                    parts.append(text)
            elif item.get("type") in {"text", "output_text"}:
                text = VisionAnalyzer._extract_text_from_node(item)
                if text:
                    parts.append(text)
        return "\n".join(part for part in parts if part).strip()

    @staticmethod
    def _validate_analysis_text(text: str) -> None:
        normalized = " ".join(text.lower().split())
        invalid_patterns = (
            "please upload the photo",
            "please upload the image",
            "paste the image",
            "upload the image of the screen",
            "请上传图片",
            "请上传图像",
            "没有收到你要识别的题目图片",
            "我这边还没有收到",
        )
        if any(pattern in normalized for pattern in invalid_patterns):
            raise RuntimeError(
                "AI service did not receive a usable image input; the current proxy/model route appears to ignore the uploaded image"
            )
