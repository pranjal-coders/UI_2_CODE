from __future__ import annotations

from app.schemas.models import (
    ElementType,
    BoundingBox,
    DetectedElement,
    Viewport,
    UIASTNode,
)
from app.compiler.ast_builder import build_ast


def _get_all_ast_ids(node: UIASTNode) -> list[str]:
    ids = [node.id]
    for child in node.children:
        ids.extend(_get_all_ast_ids(child))
    return ids


def test_build_ast_root_is_page(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    root = build_ast(demo_viewport, demo_elements)
    assert root.id == "root"
    assert root.type == ElementType.PAGE


def test_build_ast_direct_children(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    root = build_ast(demo_viewport, demo_elements)
    # Direct children of root should be: header, hero section, features section, footer
    direct_types = [child.type for child in root.children]
    assert direct_types == [
        ElementType.HEADER,
        ElementType.SECTION,
        ElementType.SECTION,
        ElementType.FOOTER,
    ]
    # Header should contain heading, nav, button
    header = root.children[0]
    header_child_types = [c.type for c in header.children]
    assert ElementType.HEADING in header_child_types
    assert ElementType.NAV in header_child_types
    assert ElementType.BUTTON in header_child_types


def test_build_ast_cards_nested_under_features(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    root = build_ast(demo_viewport, demo_elements)
    # Third child is the features section
    features_section = root.children[2]
    cards = [c for c in features_section.children if c.type == ElementType.CARD]
    assert len(cards) == 3
    for card in cards:
        child_types = [c.type for c in card.children]
        assert ElementType.ICON in child_types
        assert ElementType.HEADING in child_types
        assert ElementType.TEXT in child_types


def test_build_ast_no_duplicate_ids(demo_viewport: Viewport, demo_elements: list[DetectedElement]) -> None:
    root = build_ast(demo_viewport, demo_elements)
    all_ids = _get_all_ast_ids(root)
    assert len(all_ids) == len(set(all_ids)), "Tree contains duplicate IDs"


def test_build_ast_empty_elements(sample_viewport: Viewport) -> None:
    root = build_ast(sample_viewport, [])
    assert root.id == "root"
    assert root.type == ElementType.PAGE
    assert len(root.children) == 0


def test_build_ast_single_element(sample_viewport: Viewport) -> None:
    element = DetectedElement(
        id="single-hero",
        type=ElementType.SECTION,
        bbox=BoundingBox(x=0.0, y=0.1, width=1.0, height=0.5),
        style={"backgroundColor": "#333333"},
    )
    root = build_ast(sample_viewport, [element])
    assert len(root.children) == 1
    assert root.children[0].id == "single-hero"
    assert root.children[0].type == ElementType.SECTION
