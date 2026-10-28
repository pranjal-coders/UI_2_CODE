from __future__ import annotations

import base64
import io
import numpy as np
from PIL import Image
from app.schemas.models import VerificationResult


def compute_verification(
    source_bytes: bytes,
    generated_bytes: bytes,
    diff_threshold: float = 30.0,
) -> VerificationResult:
    """Compare source design image against generated web rendering."""
    src_img = Image.open(io.BytesIO(source_bytes)).convert("RGB")
    gen_img = Image.open(io.BytesIO(generated_bytes)).convert("RGB")

    width, height = src_img.size
    if gen_img.size != (width, height):
        gen_img = gen_img.resize((width, height), Image.Resampling.LANCZOS)

    src_arr = np.array(src_img, dtype=np.float32)
    gen_arr = np.array(gen_img, dtype=np.float32)

    abs_diff = np.abs(src_arr - gen_arr)
    mae = float(np.mean(abs_diff) / 255.0)

    changed_mask = np.any(abs_diff > diff_threshold, axis=2)
    total_pixels = width * height
    changed_pixel_count = int(np.count_nonzero(changed_mask))
    changed_pixel_percent = float((changed_pixel_count / total_pixels) * 100.0) if total_pixels > 0 else 0.0

    similarity_estimate = max(0.0, min(1.0, 1.0 - mae))

    # Generate visual difference heatmap/amplified view
    diff_amplified = np.clip(abs_diff * 2.5, 0, 255).astype(np.uint8)
    diff_img = Image.fromarray(diff_amplified)

    buf = io.BytesIO()
    diff_img.save(buf, format="PNG")
    diff_image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    explanation = (
        f"MAE: {mae:.4f} (normalized 0-1 scale). "
        f"{changed_pixel_percent:.2f}% of pixels exceed difference threshold ({int(diff_threshold)}/255). "
        f"Estimated visual fidelity: {similarity_estimate * 100:.1f}%."
    )

    return VerificationResult(
        width=width,
        height=height,
        mae=round(mae, 4),
        changed_pixel_percent=round(changed_pixel_percent, 2),
        similarity_estimate=round(similarity_estimate, 4),
        diff_image_base64=diff_image_base64,
        metric_explanation=explanation,
    )
