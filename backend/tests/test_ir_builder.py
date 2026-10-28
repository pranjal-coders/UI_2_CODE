from __future__ import annotations

from app.schemas.models import (
    ElementType,
    BoundingBox,
    DetectedElement,
    Viewport,
    UIIRNode,
)
from app.compiler.ast_builder import build_ast
from app.compiler.ir_builder import build_ir


def _collect_ir_nodes(node: UIIRNode) -> list[UIIRNode]:
    nodes = [node]
    for child in node.children:
        nodes.extend(_collect_ir_nodes(child))
    return nodes


def test_ir_version_and_viewport(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    assert ir.version == "1.0.0"
    assert ir.viewport.width == demo_viewport.width
    assert ir.viewport.height == demo_viewport.height


def test_ir_html_tags(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    all_nodes = _collect_ir_nodes(ir.root)

    tag_by_id = {node.id: node.html_tag for node in all_nodes}

    assert tag_by_id["root"] == "div"
    assert tag_by_id["el-1"] == "header"
    assert tag_by_id["el-3"] == "nav"
    assert tag_by_id["el-4"] == "a"  # link
    assert tag_by_id["el-7"] == "button"
    assert tag_by_id["el-8"] == "section"
    assert tag_by_id["el-10"] == "p"  # text
    assert tag_by_id["el-14"] == "div"  # card
    assert tag_by_id["el-15"] == "span"  # icon
    assert tag_by_id["el-26"] == "footer"


def test_ir_layout_inference(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    all_nodes = _collect_ir_nodes(ir.root)

    node_by_id = {node.id: node for node in all_nodes}

    # Header children are arranged horizontally -> layout flex
    header = node_by_id["el-1"]
    assert header.layout == "flex"

    # Card nodes have vertical children -> layout flex
    card = node_by_id["el-14"]
    assert card.layout == "flex"


def test_ir_css_classes_generated(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    ast = build_ast(demo_viewport, demo_elements)
    ir = build_ir(ast, demo_viewport)
    all_nodes = _collect_ir_nodes(ir.root)

    for node in all_nodes:
        assert len(node.css_classes) > 0, f"Node {node.id} has no CSS classes"
        assert any(cls.startswith("ui2c-") or cls in ("card", "page") for cls in node.css_classes)

    # Check card specifically has 'card'
    card_node = next(n for n in all_nodes if n.id == "el-14")
    assert "card" in card_node.css_classes
