from __future__ import annotations

import json
from pathlib import Path
import pytest
from app.schemas.models import (
    ElementType,
    BoundingBox,
    DetectedElement,
    Viewport,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def get_fixture_path() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "fixtures" / "demo_detections.json",
        Path(__file__).resolve().parent.parent / "fixtures" / "demo_detections.json",
        Path.cwd() / "fixtures" / "demo_detections.json",
        Path.cwd().parent / "fixtures" / "demo_detections.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError("Could not find fixtures/demo_detections.json")


@pytest.fixture
def demo_fixture_data() -> dict:
    path = get_fixture_path()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def demo_viewport(demo_fixture_data: dict) -> Viewport:
    return Viewport(**demo_fixture_data["viewport"])


@pytest.fixture
def demo_elements(demo_fixture_data: dict) -> list[DetectedElement]:
    return [DetectedElement(**item) for item in demo_fixture_data["elements"]]


@pytest.fixture
def sample_viewport() -> Viewport:
    return Viewport(width=1280, height=800)


@pytest.fixture
def sample_elements() -> list[DetectedElement]:
    return [
        DetectedElement(
            id="sample-header",
            type=ElementType.HEADER,
            bbox=BoundingBox(x=0.0, y=0.0, width=1.0, height=0.1),
            style={"backgroundColor": "#1a1a2e"},
        ),
        DetectedElement(
            id="sample-heading",
            type=ElementType.HEADING,
            text="Welcome to UI2Code",
            bbox=BoundingBox(x=0.05, y=0.02, width=0.3, height=0.05),
            style={"color": "#ffffff", "fontSize": "24px"},
        ),
        DetectedElement(
            id="sample-btn",
            type=ElementType.BUTTON,
            text="Get Started",
            bbox=BoundingBox(x=0.8, y=0.02, width=0.15, height=0.05),
            style={"backgroundColor": "#e94560", "color": "#ffffff"},
        ),
    ]
