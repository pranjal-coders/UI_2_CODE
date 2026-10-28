from __future__ import annotations

import base64
import json
import re
from typing import Optional
import httpx
from app.schemas.models import DetectedElement, Viewport, ElementType, BoundingBox
from app.vision.provider import VisionProvider
from app.vision.gemini_provider import (
    DETECTION_SYSTEM_PROMPT,
    _clean_json_response,
    _parse_and_validate_detections,
)


class OpenAIVisionProvider(VisionProvider):
    """Vision Provider implementation using OpenAI GPT-4o API."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o") -> None:
        self.api_key = api_key.strip()
        self.model_name = model_name

    async def analyze(
        self, image_bytes: bytes, image_width: int, image_height: int
    ) -> tuple[Viewport, list[DetectedElement]]:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": DETECTION_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analyze this UI screenshot ({image_width}x{image_height}px) and output structured UI detections JSON.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=50.0) as client:
            resp = await client.post(url, headers=headers, json=payload)

            if resp.status_code != 200:
                raise ValueError(
                    f"OpenAI API returned error {resp.status_code}: {resp.text[:300]}"
                )

            result_json = resp.json()

        try:
            choices = result_json.get("choices", [])
            if not choices:
                raise ValueError("No choices returned from OpenAI Vision API")

            raw_text = choices[0].get("message", {}).get("content", "")
            cleaned = _clean_json_response(raw_text)
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as err:
            raise ValueError(
                f"Failed to parse JSON response from OpenAI Vision: {err}. Raw: {raw_text[:200]}"
            ) from err

        return _parse_and_validate_detections(parsed, image_width, image_height)
