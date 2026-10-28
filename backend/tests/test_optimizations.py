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
from app.compiler.optimizations import (
    style_normalization,
    duplicate_style_elimination,
    repeated_pattern_recognition,
    safe_wrapper_simplification,
    run_optimizations,
)


def _count_nodes(node: UIIRNode) -> int:
    return 1 + sum(_count_nodes(child) for child in node.children)


def test_style_normalization_canonicalizes_colors(sample_viewport: Viewport) -> None:
    node = UIIRNode(
        id="test-node",
        type=ElementType.BUTTON,
        html_tag="button",
        style={"color": "#FFF", "backgroundColor": "#123", "fontSize": "16"},
    )
    root = UIIRNode(
        id="root",
        type=ElementType.PAGE,
        html_tag="div",
        children=[node],
    )
    ir = UIIR(viewport=sample_viewport, root=root)
    opt_ir, event = style_normalization(ir)

    optimized_node = opt_ir.root.children[0]
    assert optimized_node.style["color"] == "#ffffff"
    assert optimized_node.style["backgroundColor"] == "#112233"
    assert optimized_node.style["fontSize"] == "16px"
    assert event.changed_count == 3


def test_duplicate_styles_get_shared_class(sample_viewport: Viewport) -> None:
    style = {"color": "#ffffff", "padding": "10px"}
    node1 = UIIRNode(id="n1", type=ElementType.BUTTON, html_tag="button", style=dict(style))
    node2 = UIIRNode(id="n2", type=ElementType.BUTTON, html_tag="button", style=dict(style))
    root = UIIRNode(
        id="root",
        type=ElementType.PAGE,
        html_tag="div",
        children=[node1, node2],
    )
    ir = UIIR(viewport=sample_viewport, root=root)
    opt_ir, event = duplicate_style_elimination(ir)

    assert len(opt_ir.style_tokens) == 1
    shared_class = list(opt_ir.style_tokens.keys())[0]
    assert opt_ir.style_tokens[shared_class] == style
    assert shared_class in opt_ir.root.children[0].css_classes
    assert shared_class in opt_ir.root.children[1].css_classes


def test_pattern_recognition_assigns_shared_class(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    opt_ir, event = repeated_pattern_recognition(ir)

    # Features section has 3 card siblings
    features = opt_ir.root.children[2]
    cards = [c for c in features.children if c.type == ElementType.CARD]
    assert len(cards) == 3

    card_group_classes = [
        cls for card in cards for cls in card.css_classes if "card-group" in cls
    ]
    assert len(card_group_classes) == 3
    # All 3 cards should share the same group class
    assert len(set(card_group_classes)) == 1


def test_safe_wrapper_simplification_behavior(sample_viewport: Viewport) -> None:
    # 1. Redundant unstyled container with single child -> should be unwrapped
    leaf = UIIRNode(id="leaf-btn", type=ElementType.BUTTON, html_tag="button", text="Click")
    safe_wrapper = UIIRNode(
        id="wrapper-div",
        type=ElementType.CONTAINER,
        html_tag="div",
        style={},
        children=[leaf],
    )
    # 2. Styled container with background -> should NOT be unwrapped
    styled_leaf = UIIRNode(id="styled-leaf", type=ElementType.TEXT, html_tag="p", text="Text")
    styled_container = UIIRNode(
        id="styled-container",
        type=ElementType.CONTAINER,
        html_tag="div",
        style={"backgroundColor": "#f0f0f0"},
        children=[styled_leaf],
    )
    root = UIIRNode(
        id="root",
        type=ElementType.PAGE,
        html_tag="div",
        children=[safe_wrapper, styled_container],
    )
    ir = UIIR(viewport=sample_viewport, root=root)
    opt_ir, event = safe_wrapper_simplification(ir)

    child_ids = [c.id for c in opt_ir.root.children]
    assert "leaf-btn" in child_ids  # unwrapped
    assert "wrapper-div" not in child_ids
    assert "styled-container" in child_ids  # preserved because it has visual styling


def test_no_elements_deleted_from_fixture(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    initial_count = _count_nodes(ir.root)

    opt_ir, events = run_optimizations(ir)
    final_count = _count_nodes(opt_ir.root)

    # No elements should be dropped from the semantic fixture
    assert final_count == initial_count


def test_optimization_is_deterministic(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast1 = build_ast(demo_viewport, demo_elements)
    ir1 = build_ir(ast1, demo_viewport)
    opt1, events1 = run_optimizations(ir1)

    ast2 = build_ast(demo_viewport, demo_elements)
    ir2 = build_ir(ast2, demo_viewport)
    opt2, events2 = run_optimizations(ir2)

    assert opt1.model_dump() == opt2.model_dump()
    assert [e.model_dump() for e in events1] == [e.model_dump() for e in events2]
