from __future__ import annotations

import asyncio
import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.models import (
    Viewport,
    DetectedElement,
    CompileResponse,
)
from app.services.pipeline import run_pipeline


def test_full_pipeline_with_fixture(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    response: CompileResponse = asyncio.run(
        run_pipeline(
            viewport=demo_viewport,
            elements=demo_elements,
        )
    )

    # 1. Non-empty string outputs
    assert isinstance(response.html, str) and len(response.html) > 0
    assert isinstance(response.css, str) and len(response.css) > 0
    assert isinstance(response.js, str) and len(response.js) > 0

    # 2. Valid AST and IR dictionaries
    assert isinstance(response.ast, dict)
    assert response.ast.get("id") == "root"
    assert len(response.ast.get("children", [])) > 0

    assert isinstance(response.ir, dict)
    assert response.ir.get("version") == "1.0.0"
    assert "root" in response.ir

    # 3. Diagnostics and optimization logs are lists
    assert isinstance(response.diagnostics, list)
    assert isinstance(response.optimization_log, list)
    assert len(response.optimization_log) == 5

    # 4. Demo mode matches setting
    assert isinstance(response.demo_mode, bool)


def test_api_health_endpoint() -> None:
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "demo_mode" in data
    assert "provider_configured" in data
    assert data["version"] == "1.0.0"


def test_api_analyze_endpoint(demo_fixture_data: dict) -> None:
    client = TestClient(app)
    # Create a small valid test PNG image
    img = Image.new("RGB", (800, 600), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # Test with fixture provider
    res_fixture = client.post(
        "/api/analyze",
        files={"file": ("test_ui.png", buf.getvalue(), "image/png")},
        data={"provider": "fixture"},
    )
    assert res_fixture.status_code == 200
    data_fixture = res_fixture.json()
    assert len(data_fixture["elements"]) == len(demo_fixture_data["elements"])
    assert data_fixture["demo_mode"] is True

    # Test with default local_cv analyzer
    res_cv = client.post(
        "/api/analyze",
        files={"file": ("test_ui.png", buf.getvalue(), "image/png")},
    )
    assert res_cv.status_code == 200
    data_cv = res_cv.json()
    assert data_cv["viewport"]["width"] == 800
    assert data_cv["viewport"]["height"] == 600
    assert len(data_cv["elements"]) > 0
    assert data_cv["engine"] == "local_cv"


def test_api_compile_endpoint(demo_fixture_data: dict) -> None:
    client = TestClient(app)
    res = client.post("/api/compile", json=demo_fixture_data)
    assert res.status_code == 200
    data = res.json()
    assert "<!DOCTYPE html>" in data["html"]
    assert ".page" in data["css"]
    assert "DOMContentLoaded" in data["js"]
    assert isinstance(data["ast"], dict)
    assert isinstance(data["ir"], dict)
    assert isinstance(data["diagnostics"], list)
    assert len(data["optimization_log"]) == 5


def test_api_verify_endpoint() -> None:
    client = TestClient(app)
    img1 = Image.new("RGB", (200, 200), color=(255, 0, 0))
    img2 = Image.new("RGB", (200, 200), color=(250, 5, 5))

    buf1, buf2 = io.BytesIO(), io.BytesIO()
    img1.save(buf1, format="PNG")
    img2.save(buf2, format="PNG")

    res = client.post(
        "/api/verify",
        files={
            "source_image": ("source.png", buf1.getvalue(), "image/png"),
            "generated_image": ("gen.png", buf2.getvalue(), "image/png"),
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["width"] == 200
    assert data["height"] == 200
    assert data["mae"] >= 0.0
    assert "metric_explanation" in data
    assert data["diff_image_base64"] is not None


def test_api_refine_endpoint() -> None:
    client = TestClient(app)
    payload = {
        "ir": {"version": "1.0.0", "root": {"id": "root", "type": "page", "html_tag": "div"}},
        "source_description": "Make header sticky",
        "diagnostics": [],
    }
    res = client.post("/api/refine", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ir"] == payload["ir"]
    assert len(data["changes"]) >= 1
