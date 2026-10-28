from __future__ import annotations

import io
import logging
from typing import Optional
import numpy as np
import cv2
from PIL import Image

from app.schemas.models import (
    ElementType,
    BoundingBox,
    DetectedElement,
    Viewport,
)
from app.vision.provider import VisionProvider

logger = logging.getLogger("ui2code.vision.local_cv")


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Format RGB tuple as standard lowercase hex string."""
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _sample_dominant_color(img_rgb: np.ndarray, x: int, y: int, w: int, h: int) -> tuple[str, float]:
    """Sample median color and relative luminance in a region."""
    img_h, img_w, _ = img_rgb.shape
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(img_w, x + w), min(img_h, y + h)

    if x2 <= x1 or y2 <= y1:
        return "#ffffff", 1.0

    crop = img_rgb[y1:y2, x1:x2]
    med_color = np.median(crop, axis=(0, 1)).astype(int)
    r, g, b = med_color[0], med_color[1], med_color[2]
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    return _rgb_to_hex(r, g, b), luminance


def _calculate_iou(b1: tuple[float, float, float, float], b2: tuple[float, float, float, float]) -> float:
    """Compute Intersection-over-Union between two normalized bounding boxes (x, y, w, h)."""
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2

    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)

    iw = max(0.0, xi2 - xi1)
    ih = max(0.0, yi2 - yi1)
    inter_area = iw * ih

    box1_area = w1 * h1
    box2_area = w2 * h2
    union_area = box1_area + box2_area - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / union_area


class LocalCVVisionProvider(VisionProvider):
    """100% Free, Offline Computer Vision UI layout & element detector using OpenCV, NumPy, and Pillow.
    
    Operates strictly as a deterministic Visual Scanner (Lexical Analyzer):
    Converts raw pixel input into discrete Visual Tokens (DetectedElements) without injecting
    synthetic boilerplate or hallucinated marketing elements.
    """

    def __init__(self) -> None:
        logger.info("LocalCVVisionProvider initialized for data-driven offline analysis")

    async def analyze(
        self, image_bytes: bytes, image_width: int, image_height: int
    ) -> tuple[Viewport, list[DetectedElement]]:
        # 1. Decode image into OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            # Fallback to PIL
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_rgb = np.array(pil_img)
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        else:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        img_h, img_w, _ = img_rgb.shape
        total_area = float(img_w * img_h)
        viewport = Viewport(width=img_w, height=img_h)

        # 2. Extract global background color from image perimeter borders
        border_pixels = np.concatenate([
            img_rgb[0, :, :],
            img_rgb[-1, :, :],
            img_rgb[:, 0, :],
            img_rgb[:, -1, :],
        ], axis=0)
        page_bg_rgb = np.median(border_pixels, axis=0).astype(int)
        page_bg_hex = _rgb_to_hex(*page_bg_rgb)
        page_lum = (0.299 * page_bg_rgb[0] + 0.587 * page_bg_rgb[1] + 0.114 * page_bg_rgb[2]) / 255.0

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        row_energy = np.mean(np.abs(sobel_y), axis=1)
        mean_energy = float(np.mean(row_energy))

        # 3. Detect major horizontal bands ONLY if distinct top header or bottom footer actually exist
        # Check for top header bar (within top 18% of image, at least 20px)
        header_box: Optional[tuple[int, int, int, int]] = None
        max_header_y = int(img_h * 0.18)
        for y_cand in range(20, max_header_y):
            if row_energy[y_cand] > max(5.0, mean_energy * 1.8):
                slice_top = img_rgb[0:y_cand, :]
                top_color = np.median(slice_top, axis=(0, 1)).astype(int)
                slice_body = img_rgb[y_cand:min(img_h, y_cand + 60), :]
                body_color = np.median(slice_body, axis=(0, 1)).astype(int)
                diff = np.linalg.norm(top_color.astype(float) - body_color.astype(float))
                if diff > 15:
                    header_box = (0, 0, img_w, y_cand)
                    break

        # Check for bottom footer bar (within bottom 20% of image, at least 20px)
        footer_box: Optional[tuple[int, int, int, int]] = None
        min_footer_y = int(img_h * 0.82)
        for y_cand in range(min_footer_y, img_h - 20):
            if row_energy[y_cand] > max(5.0, mean_energy * 1.8):
                slice_foot = img_rgb[y_cand:img_h, :]
                foot_color = np.median(slice_foot, axis=(0, 1)).astype(int)
                slice_body = img_rgb[max(0, y_cand - 60):y_cand, :]
                body_color = np.median(slice_body, axis=(0, 1)).astype(int)
                diff = np.linalg.norm(foot_color.astype(float) - body_color.astype(float))
                if diff > 15:
                    footer_box = (0, y_cand, img_w, img_h - y_cand)
                    break

        elements: list[DetectedElement] = []
        el_idx = 1

        # Add Header ONLY if visually detected
        if header_box:
            h_bg, h_lum = _sample_dominant_color(img_rgb, header_box[0], header_box[1], header_box[2], header_box[3])
            elements.append(
                DetectedElement(
                    id=f"el-{el_idx}",
                    type=ElementType.HEADER,
                    bbox=BoundingBox(x=0.0, y=0.0, width=1.0, height=round(header_box[3] / img_h, 4)),
                    style={"backgroundColor": h_bg, "padding": "16px 24px"},
                    confidence=0.92,
                )
            )
            el_idx += 1

        # Content area bounds
        body_y_start = header_box[3] if header_box else 0
        body_y_end = footer_box[1] if footer_box else img_h
        body_h = body_y_end - body_y_start

        body_crop = img_rgb[body_y_start:body_y_end, :]
        body_bg_rgb = np.median(body_crop, axis=(0, 1)).astype(int) if body_h > 0 else page_bg_rgb
        body_bg_hex = _rgb_to_hex(*body_bg_rgb)

        # In a multi-band layout (header + footer), create an enclosing Section for the body
        if header_box and footer_box:
            elements.append(
                DetectedElement(
                    id=f"el-{el_idx}",
                    type=ElementType.SECTION,
                    bbox=BoundingBox(
                        x=0.0,
                        y=round(body_y_start / img_h, 4),
                        width=1.0,
                        height=round(body_h / img_h, 4),
                    ),
                    style={"backgroundColor": body_bg_hex, "padding": "32px 24px"},
                    confidence=0.90,
                )
            )
            el_idx += 1

        # 4. Extract Foreground Contours (Cards, Buttons, Inputs, Headings, Text, Images)
        diff_from_body = np.linalg.norm(img_rgb.astype(float) - body_bg_rgb.astype(float), axis=2)
        fg_mask = (diff_from_body > 18).astype(np.uint8) * 255
        edges = cv2.Canny(gray, 30, 100)
        combined = cv2.bitwise_or(fg_mask, edges)

        # Mask out header and footer so their boundary edges don't create spurious duplicate boxes
        if header_box:
            combined[0:header_box[3], :] = 0
        if footer_box:
            combined[footer_box[1]:, :] = 0

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        raw_candidates: list[tuple[int, int, int, int, float, float, float, float, float, float]] = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area_pct = (w * h) / total_area
            # Skip tiny noise or canvas wrapper
            if area_pct < 0.001 or area_pct > 0.95 or w < 10 or h < 8:
                continue
            raw_candidates.append(
                (x, y, w, h, x / img_w, y / img_h, w / img_w, h / img_h, area_pct, w / float(h))
            )

        # Non-Maximum Suppression (NMS) to eliminate duplicate outer/inner borders
        raw_candidates.sort(key=lambda item: item[8], reverse=True)
        deduped: list[tuple[int, int, int, int, float, float, float, float, float, float]] = []
        for item in raw_candidates:
            b1 = (item[4], item[5], item[6], item[7])
            if not any(_calculate_iou(b1, (d[4], d[5], d[6], d[7])) > 0.50 for d in deduped):
                deduped.append(item)

        # Sort elements in natural visual reading order (top-to-bottom, left-to-right)
        deduped.sort(key=lambda item: (round(item[5], 2), round(item[4], 2)))

        # 5. Classify visual tokens strictly by physical visual metrics
        for item in deduped:
            x, y, w, h, nx, ny, nw, nh, area_pct, aspect = item
            c_hex, c_lum = _sample_dominant_color(img_rgb, x, y, w, h)
            crop = img_rgb[y:y+h, x:x+w]
            std_val = float(np.std(crop)) if crop.size > 0 else 0.0

            el_id = f"el-{el_idx}"
            el_idx += 1
            bbox = BoundingBox(x=round(nx, 4), y=round(ny, 4), width=round(nw, 4), height=round(nh, 4))

            # Classification heuristics
            if area_pct >= 0.035 and nw >= 0.12 and nh >= 0.08 and 0.25 <= aspect <= 4.0:
                # Card / Panel Container
                elements.append(
                    DetectedElement(
                        id=el_id,
                        type=ElementType.CARD,
                        bbox=bbox,
                        style={
                            "backgroundColor": c_hex,
                            "borderRadius": "8px",
                            "padding": "20px",
                            "boxShadow": "0 2px 8px rgba(0,0,0,0.06)",
                        },
                        confidence=0.90,
                    )
                )
            elif 1.1 <= aspect <= 7.0 and 0.02 <= nh <= 0.14 and 0.03 <= nw <= 0.55:
                # Button or Form Input
                if std_val < 35 or c_hex != body_bg_hex:
                    btn_fg = "#ffffff" if c_lum < 0.5 else "#1e293b"
                    elements.append(
                        DetectedElement(
                            id=el_id,
                            type=ElementType.BUTTON,
                            text="Submit",
                            bbox=bbox,
                            style={
                                "backgroundColor": c_hex,
                                "color": btn_fg,
                                "borderRadius": "6px",
                                "padding": "10px 20px",
                                "fontWeight": "600",
                            },
                            confidence=0.92,
                        )
                    )
                else:
                    elements.append(
                        DetectedElement(
                            id=el_id,
                            type=ElementType.INPUT,
                            bbox=bbox,
                            style={
                                "backgroundColor": c_hex,
                                "border": "1px solid #cbd5e1",
                                "borderRadius": "6px",
                                "padding": "8px 12px",
                            },
                            confidence=0.88,
                        )
                    )
            elif aspect >= 1.5 and nh >= 0.035:
                # Heading Text
                txt_color = "#ffffff" if page_lum < 0.5 else "#0f172a"
                elements.append(
                    DetectedElement(
                        id=el_id,
                        type=ElementType.HEADING,
                        text="Heading",
                        bbox=bbox,
                        style={"color": txt_color, "fontSize": "24px", "fontWeight": "bold"},
                        confidence=0.88,
                    )
                )
            elif aspect >= 1.5 and nh < 0.035:
                # Body Text / Paragraph
                txt_color = "#cbd5e1" if page_lum < 0.5 else "#475569"
                elements.append(
                    DetectedElement(
                        id=el_id,
                        type=ElementType.TEXT,
                        text="Content text",
                        bbox=bbox,
                        style={"color": txt_color, "fontSize": "14px"},
                        confidence=0.84,
                    )
                )
            elif std_val > 45 and area_pct >= 0.015:
                # Visual Media / Image Asset
                elements.append(
                    DetectedElement(
                        id=el_id,
                        type=ElementType.IMAGE,
                        bbox=bbox,
                        style={"borderRadius": "8px", "objectFit": "cover"},
                        confidence=0.85,
                    )
                )
            else:
                # Generic Container
                elements.append(
                    DetectedElement(
                        id=el_id,
                        type=ElementType.CONTAINER,
                        bbox=bbox,
                        style={"backgroundColor": c_hex},
                        confidence=0.80,
                    )
                )

        # Add Footer ONLY if visually detected
        if footer_box:
            f_bg, _ = _sample_dominant_color(img_rgb, footer_box[0], footer_box[1], footer_box[2], footer_box[3])
            elements.append(
                DetectedElement(
                    id=f"el-{el_idx}",
                    type=ElementType.FOOTER,
                    bbox=BoundingBox(
                        x=0.0,
                        y=round(footer_box[1] / img_h, 4),
                        width=1.0,
                        height=round(footer_box[3] / img_h, 4),
                    ),
                    style={"backgroundColor": f_bg, "padding": "24px 20px"},
                    confidence=0.91,
                )
            )

        # Fallback for solid/empty background images where no distinct sub-contours were found:
        # provide a single container element capturing the canvas background.
        if not elements:
            elements.append(
                DetectedElement(
                    id="el-1",
                    type=ElementType.CONTAINER,
                    bbox=BoundingBox(x=0.0, y=0.0, width=1.0, height=1.0),
                    style={"backgroundColor": page_bg_hex},
                    confidence=0.99,
                )
            )

        logger.info(f"Local CV detected {len(elements)} data-driven elements from {img_w}x{img_h} image")
        return viewport, elements
