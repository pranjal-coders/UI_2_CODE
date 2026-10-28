from __future__ import annotations

from app.schemas.models import (
    ElementType,
    BoundingBox,
    DetectedElement,
    Viewport,
    UIIRNode,
    UIIR,
)
from app.compiler.ast_builder import build_ast
from app.compiler.ir_builder import build_ir
from app.compiler.semantic_analyzer import analyze_semantics


def test_semantic_analyzer_valid_fixture(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    diagnostics = analyze_semantics(ir)

    # Valid fixture should produce no error-level diagnostics
    errors = [d for d in diagnostics if d.severity == "error"]
    assert len(errors) == 0, f"Unexpected semantic errors on valid fixture: {errors}"


def test_semantic_analyzer_duplicate_id(sample_viewport: Viewport) -> None:
    node1 = UIIRNode(
        id="btn-dup",
        type=ElementType.BUTTON,
        html_tag="button",
        text="Click 1",
        bbox=BoundingBox(x=0.1, y=0.1, width=0.2, height=0.05),
    )
    node2 = UIIRNode(
        id="btn-dup",
        type=ElementType.BUTTON,
        html_tag="button",
        text="Click 2",
        bbox=BoundingBox(x=0.4, y=0.1, width=0.2, height=0.05),
    )
    root = UIIRNode(
        id="root",
        type=ElementType.PAGE,
        html_tag="div",
        bbox=BoundingBox(x=0.0, y=0.0, width=1.0, height=1.0),
        children=[node1, node2],
    )
    ir = UIIR(viewport=sample_viewport, root=root)
    diagnostics = analyze_semantics(ir)

    duplicate_errors = [d for d in diagnostics if d.code == "DUPLICATE_ID"]
    assert len(duplicate_errors) >= 1
    assert any(d.node_id == "btn-dup" and d.severity == "error" for d in duplicate_errors)


def test_semantic_analyzer_button_inside_button(sample_viewport: Viewport) -> None:
    inner_btn = UIIRNode(
        id="btn-inner",
        type=ElementType.BUTTON,
        html_tag="button",
        text="Inner",
        bbox=BoundingBox(x=0.15, y=0.15, width=0.05, height=0.02),
    )
    outer_btn = UIIRNode(
        id="btn-outer",
        type=ElementType.BUTTON,
        html_tag="button",
        text="Outer",
        bbox=BoundingBox(x=0.1, y=0.1, width=0.2, height=0.05),
        children=[inner_btn],
    )
    root = UIIRNode(
        id="root",
        type=ElementType.PAGE,
        html_tag="div",
        bbox=BoundingBox(x=0.0, y=0.0, width=1.0, height=1.0),
        children=[outer_btn],
    )
    ir = UIIR(viewport=sample_viewport, root=root)
    diagnostics = analyze_semantics(ir)

    nesting_warnings = [
        d for d in diagnostics if d.code == "INVALID_NESTING" and d.severity == "warning"
    ]
    assert len(nesting_warnings) >= 1
    assert any("button" in d.message.lower() for d in nesting_warnings)


def test_semantic_analyzer_small_bbox_warning(sample_viewport: Viewport) -> None:
    small_node = UIIRNode(
        id="noisy-speck",
        type=ElementType.TEXT,
        html_tag="p",
        text="tiny",
        bbox=BoundingBox(x=0.1, y=0.1, width=0.001, height=0.001),
    )
    root = UIIRNode(
        id="root",
        type=ElementType.PAGE,
        html_tag="div",
        bbox=BoundingBox(x=0.0, y=0.0, width=1.0, height=1.0),
        children=[small_node],
    )
    ir = UIIR(viewport=sample_viewport, root=root)
    diagnostics = analyze_semantics(ir)

    noise_warnings = [d for d in diagnostics if d.code == "SMALL_BBOX_NOISE"]
    assert len(noise_warnings) >= 1
    assert noise_warnings[0].severity == "warning"
