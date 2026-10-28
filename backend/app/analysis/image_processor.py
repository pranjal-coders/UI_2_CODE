from __future__ import annotations

import io
from PIL import Image

ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}

ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}


def validate_image(
    file_bytes: bytes,
    content_type: str | None = None,
    max_size_mb: int = 10,
) -> tuple[int, int]:
    """Validate image file size, content type, and decodability.
    
    Raises ValueError if image is invalid.
    Returns (width, height) of the image if valid.
    """
    if not file_bytes:
        raise ValueError("Image file is empty")

    max_bytes = max_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise ValueError(f"Image file size ({len(file_bytes)} bytes) exceeds maximum of {max_size_mb}MB")

    if content_type:
        clean_content_type = content_type.lower().split(";")[0].strip()
        if clean_content_type not in ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Unsupported content type '{content_type}'. Supported types: PNG, JPG/JPEG, WebP"
            )

    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            format_name = (img.format or "").upper()
            if format_name not in ALLOWED_FORMATS:
                raise ValueError(
                    f"Unsupported image format '{format_name}'. Supported formats: PNG, JPEG, WEBP"
                )
            width, height = img.size
            if width <= 0 or height <= 0:
                raise ValueError("Image dimensions must be positive")
            return width, height
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to decode image: {e}") from e


def get_image_dimensions(file_bytes: bytes) -> tuple[int, int]:
    """Return (width, height) of image bytes."""
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            return img.size
    except Exception as e:
        raise ValueError(f"Could not read image dimensions: {e}") from e


def normalize_images_to_same_size(
    img1_bytes: bytes,
    img2_bytes: bytes,
) -> tuple[Image.Image, Image.Image]:
    """Normalize two images to the same dimensions (using first image as reference) in RGB format."""
    try:
        im1 = Image.open(io.BytesIO(img1_bytes)).convert("RGB")
        im2 = Image.open(io.BytesIO(img2_bytes)).convert("RGB")
    except Exception as e:
        raise ValueError(f"Could not decode images for normalization: {e}") from e

    target_size = im1.size
    if im2.size != target_size:
        im2 = im2.resize(target_size, Image.Resampling.LANCZOS)

    return im1, im2
