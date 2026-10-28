from __future__ import annotations

import pytest
from app.compiler.refiner import (
    validate_and_apply_patch,
    apply_refinements,
    _extract_heuristic_patches,
    generate_and_apply_refinements,
)
from app.services.pipeline import run_pipeline
from app.schemas.models import Viewport


@pytest.fixture
def sample_ir():
    return {
        "version": "1.0.0",
        "viewport": {"width": 1280, "height": 800},
        "root": {
            "id": "root",
            "type": "page",
            "html_tag": "div",
            "style": {"backgroundColor": "#ffffff"},
            "css_classes": ["ui2c-page-root", "page"],
            "layout": "flow",
            "children": [
                {
                    "id": "el-card-1",
                    "type": "card",
                    "html_tag": "div",
                    "style": {"backgroundColor": "#f8f9fa", "padding": "24px"},
                    "css_classes": ["ui2c-card-1", "card"],
                    "layout": "flex",
                    "bbox": {"x": 0.1, "y": 0.2, "width": 0.35, "height": 0.3},
                    "children": [
                        {
                            "id": "el-btn-1",
                            "type": "button",
                            "html_tag": "button",
                            "text": "Click Me",
                            "style": {"backgroundColor": "#007bff", "color": "#ffffff"},
                            "css_classes": ["ui2c-button-1"],
                            "layout": "flow",
                            "children": [],
                        }
                    ],
                }
            ],
        },
        "style_tokens": {},
        "assets": [],
        "diagnostics": [],
    }


def test_refiner_allows_valid_style_patch(sample_ir):
    patch = {
        "node_id": "el-card-1",
        "field": "style.borderRadius",
        "proposed_value": "12px",
        "rationale": "Rounded aesthetic",
    }
    success, msg, record = validate_and_apply_patch(sample_ir, patch)
    assert success is True
    assert record["new_value"] == "12px"
    assert sample_ir["root"]["children"][0]["style"]["borderRadius"] == "12px"


def test_refiner_rejects_disallowed_property(sample_ir):
    patch = {
        "node_id": "el-card-1",
        "field": "style.dangerouslySetInnerHTML",
        "proposed_value": "malicious",
        "rationale": "exploit test",
    }
    success, msg, record = validate_and_apply_patch(sample_ir, patch)
    assert success is False
    assert "not in allowlist" in msg
    assert record is None


def test_refiner_rejects_unknown_node_id(sample_ir):
    patch = {
        "node_id": "non-existent-node-999",
        "field": "style.color",
        "proposed_value": "#ff0000",
        "rationale": "change color",
    }
    success, msg, record = validate_and_apply_patch(sample_ir, patch)
    assert success is False
    assert "not found" in msg


def test_refiner_bbox_validation_and_clamping(sample_ir):
    patch = {
        "node_id": "el-card-1",
        "field": "bbox",
        "proposed_value": {"x": 1.5, "y": -0.5, "width": 0.5, "height": 0.4},
        "rationale": "geometry adjustment",
    }
    success, msg, record = validate_and_apply_patch(sample_ir, patch)
    assert success is True
    # Clamped into [0, 1]
    card_bbox = sample_ir["root"]["children"][0]["bbox"]
    assert 0.0 <= card_bbox["x"] <= 1.0
    assert 0.0 <= card_bbox["y"] <= 1.0


def test_apply_refinements_preserves_original_ir(sample_ir):
    patches = [
        {
            "node_id": "el-btn-1",
            "field": "style.backgroundColor",
            "proposed_value": "#28a745",
            "rationale": "Change to green",
        }
    ]
    refined_ir, changes, diagnostics = apply_refinements(sample_ir, patches)
    # Original should be untouched
    assert sample_ir["root"]["children"][0]["children"][0]["style"]["backgroundColor"] == "#007bff"
    # Refined should have the updated value
    assert refined_ir["root"]["children"][0]["children"][0]["style"]["backgroundColor"] == "#28a745"
    assert len(changes) == 1
    assert any(d.code == "REFINE_APPLIED" for d in diagnostics)


def test_heuristic_refinement_rounding(sample_ir):
    patches = _extract_heuristic_patches(sample_ir, "Make all cards and buttons rounded with smooth borders")
    assert len(patches) >= 2
    assert any(p["node_id"] == "el-card-1" and p["field"] == "style.borderRadius" for p in patches)
    assert any(p["node_id"] == "el-btn-1" and p["field"] == "style.borderRadius" for p in patches)


@pytest.mark.anyio
async def test_recompile_refined_ir_updates_generated_css(sample_ir):
    # Apply a distinct color
    patches = [
        {
            "node_id": "el-btn-1",
            "field": "style.backgroundColor",
            "proposed_value": "#ff0077",
            "rationale": "Vibrant accent",
        }
    ]
    refined_ir, _, _ = apply_refinements(sample_ir, patches)

    compile_res = await run_pipeline(
        viewport=Viewport(width=1280, height=800),
        elements=[],
        ir=refined_ir,
    )

    assert "#ff0077" in compile_res.css
    assert "ui2c-button-1" in compile_res.html
