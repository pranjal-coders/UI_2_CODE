from __future__ import annotations

import io
import pytest
from PIL import Image, ImageDraw
from app.vision.local_cv_provider import LocalCVVisionProvider
from app.schemas.models import ElementType


@pytest.mark.anyio
async def test_local_cv_provider_detects_real_image_elements():
    provider = LocalCVVisionProvider()

    # Create a 900x600 image with distinct colored sections:
    # Top header (dark blue), body with 2 red cards, bottom footer (dark)
    img = Image.new("RGB", (900, 600), color="#1e293b")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (900, 60)], fill="#0f172a") # Header
    draw.rectangle([(50, 200), (400, 450)], fill="#dc2626") # Card 1 (Red)
    draw.rectangle([(500, 200), (850, 450)], fill="#dc2626") # Card 2 (Red)
    draw.rectangle([(0, 540), (900, 600)], fill="#020617") # Footer

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    vp, elements = await provider.analyze(data, 900, 600)

    assert vp.width == 900
    assert vp.height == 600
    assert len(elements) > 0

    types = [el.type for el in elements]
    assert ElementType.HEADER in types
    assert ElementType.SECTION in types
    assert ElementType.FOOTER in types

    # Check header color sampled from the real pixels
    header_el = next(el for el in elements if el.type == ElementType.HEADER)
    assert header_el.style is not None
    assert "backgroundColor" in header_el.style
    # #0f172a
    assert header_el.style["backgroundColor"] == "#0f172a"

    # Check card elements detected
    cards = [el for el in elements if el.type == ElementType.CARD]
    assert len(cards) >= 2
    for card in cards:
        assert card.style is not None
        assert card.style.get("backgroundColor") == "#dc2626"


@pytest.mark.anyio
async def test_local_cv_provider_single_button_only_returns_button():
    provider = LocalCVVisionProvider()

    # Image with ONLY one blue button on white canvas
    img = Image.new("RGB", (800, 600), color="#ffffff")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(300, 260), (500, 340)], radius=8, fill="#2563eb")
    draw.text((370, 290), "Click Me", fill="#ffffff")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    vp, elements = await provider.analyze(data, 800, 600)

    assert vp.width == 800
    assert vp.height == 600
    # Must only contain the button - NO fake header, footer, or hero section!
    assert len(elements) == 1
    assert elements[0].type == ElementType.BUTTON
    assert elements[0].style is not None
    assert elements[0].style.get("backgroundColor") == "#2563eb"

    types = [el.type for el in elements]
    assert ElementType.HEADER not in types
    assert ElementType.FOOTER not in types
    assert ElementType.SECTION not in types


@pytest.mark.anyio
async def test_local_cv_provider_card_with_button_and_input():
    provider = LocalCVVisionProvider()

    # Image with a single centered card containing an input and button
    img = Image.new("RGB", (800, 600), color="#ffffff")
    draw = ImageDraw.Draw(img)
    # Card
    draw.rounded_rectangle([(250, 150), (550, 450)], radius=12, fill="#f8fafc", outline="#cbd5e1", width=2)
    # Input
    draw.rounded_rectangle([(280, 230), (520, 275)], radius=6, fill="#ffffff", outline="#94a3b8", width=2)
    # Button
    draw.rounded_rectangle([(280, 310), (520, 355)], radius=6, fill="#2563eb")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    vp, elements = await provider.analyze(data, 800, 600)

    types = [el.type for el in elements]
    assert ElementType.CARD in types
    assert ElementType.BUTTON in types
    # Must NOT invent artificial headers or footers
    assert ElementType.HEADER not in types
    assert ElementType.FOOTER not in types

