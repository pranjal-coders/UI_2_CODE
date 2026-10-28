from __future__ import annotations

import base64
import json
import re
from typing import Optional
import httpx
from app.schemas.models import DetectedElement, Viewport, ElementType, BoundingBox
from app.vision.provider import VisionProvider


DETECTION_SYSTEM_PROMPT = """You are a specialized UI Layout and Component Detector for a compiler-assisted visual-to-web system.
Analyze the provided web page screenshot and identify the UI elements and visual structure.

CRITICAL RULES:
1. Do NOT generate HTML, CSS, or JavaScript code. Output ONLY a valid JSON object matching the schema below.
2. The bounding box (bbox) MUST use normalized coordinates (0.0 to 1.0) relative to the screenshot image:
   - x: horizontal position of top-left corner (0.0 = left edge, 1.0 = right edge)
   - y: vertical position of top-left corner (0.0 = top edge, 1.0 = bottom edge)
   - width: width as a fraction of image width (0.0 to 1.0)
   - height: height as a fraction of image height (0.0 to 1.0)
   Ensure 0.0 <= x <= 1.0, 0.0 <= y <= 1.0, 0.0 < width <= 1.0, 0.0 < height <= 1.0.
3. Element 'type' MUST be one of these exact strings:
   - page, header, nav, section, container, heading, text, button, link, image, input, form, card, list, table, footer, icon, unknown
4. Extract visible text accurately for headings, buttons, links, and paragraphs.
5. In 'style', include observed visual properties where discernible:
   - backgroundColor (hex e.g. '#1a1a2e')
   - color (hex e.g. '#ffffff')
   - fontSize (e.g. '16px', '24px', '32px')
   - fontWeight ('normal', 'bold', '600')
   - textAlign ('left', 'center', 'right')
   - borderRadius (e.g. '4px', '8px', '12px')
   - padding (e.g. '12px 24px')
   - gap (e.g. '16px')

REQUIRED JSON SCHEMA:
{
  "viewport": {
    "width": <integer image width in px>,
    "height": <integer image height in px>
  },
  "elements": [
    {
      "id": "el-1",
      "type": "<type from allowed list>",
      "text": "<visible text or null>",
      "bbox": { "x": 0.0, "y": 0.0, "width": 1.0, "height": 0.08 },
      "style": {
        "backgroundColor": "#1a1a2e",
        "color": "#ffffff"
      },
      "confidence": 0.95
    }
  ]
}
"""


def _clean_json_response(raw_text: str) -> str:
    """Strip markdown code fence blocks if present."""
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


def _parse_and_validate_detections(
    data: dict, fallback_width: int, fallback_height: int
) -> tuple[Viewport, list[DetectedElement]]:
    """Validate parsed JSON dictionary into typed models with clamping."""
    vp_data = data.get("viewport") or {}
    vp_w = int(vp_data.get("width") or fallback_width)
    vp_h = int(vp_data.get("height") or fallback_height)
    viewport = Viewport(width=max(100, vp_w), height=max(100, vp_h))

    raw_elements = data.get("elements", [])
    valid_elements: list[DetectedElement] = []

    for idx, item in enumerate(raw_elements):
        el_id = str(item.get("id") or f"el-{idx + 1}")
        raw_type = str(item.get("type", "unknown")).lower().strip()

        try:
            el_type = ElementType(raw_type)
        except ValueError:
            el_type = ElementType.UNKNOWN

        raw_bbox = item.get("bbox") or {}
        x = max(0.0, min(1.0, float(raw_bbox.get("x", 0.0))))
        y = max(0.0, min(1.0, float(raw_bbox.get("y", 0.0))))
        w = max(0.001, min(1.0 - x, float(raw_bbox.get("width", 0.1))))
        h = max(0.001, min(1.0 - y, float(raw_bbox.get("height", 0.05))))
        bbox = BoundingBox(x=round(x, 4), y=round(y, 4), width=round(w, 4), height=round(h, 4))

        text = item.get("text")
        if text is not None:
            text = str(text).strip()

        style = item.get("style")
        if isinstance(style, dict):
            clean_style = {str(k): str(v) for k, v in style.items() if v is not None}
        else:
            clean_style = None

        confidence = item.get("confidence")
        if confidence is not None:
            try:
                confidence = max(0.0, min(1.0, float(confidence)))
            except (ValueError, TypeError):
                confidence = None

        valid_elements.append(
            DetectedElement(
                id=el_id,
                type=el_type,
                text=text if text else None,
                bbox=bbox,
                style=clean_style,
                confidence=confidence,
            )
        )

    return viewport, valid_elements


class GeminiVisionProvider(VisionProvider):
    """Vision Provider implementation using Google Gemini API."""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key.strip()
        self.model_name = model_name

    async def analyze(
        self, image_bytes: bytes, image_width: int, image_height: int
    ) -> tuple[Viewport, list[DetectedElement]]:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": DETECTION_SYSTEM_PROMPT},
                        {
                            "text": f"Analyze this UI screenshot ({image_width}x{image_height}px) and produce structured layout element detections."
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": b64_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload)

            if resp.status_code != 200:
                raise ValueError(
                    f"Gemini API returned error {resp.status_code}: {resp.text[:300]}"
                )

            result_json = resp.json()

        try:
            candidates = result_json.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini Vision model")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise ValueError("Empty response parts from Gemini Vision model")

            raw_text = parts[0].get("text", "")
            cleaned = _clean_json_response(raw_text)
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as err:
            # Controlled one-time repair attempt
            raise ValueError(
                f"Failed to parse JSON response from Gemini Vision: {err}. Raw: {raw_text[:200]}"
            ) from err

        return _parse_and_validate_detections(parsed, image_width, image_height)
