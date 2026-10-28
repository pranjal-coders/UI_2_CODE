from __future__ import annotations

from typing import Literal
from app.schemas.models import (
    ElementType,
    BoundingBox,
    Viewport,
    UIASTNode,
    UIIRNode,
    UIIR,
)


def _map_html_tag(element_type: ElementType, depth: int) -> str:
    """Map AST element type to an HTML5 semantic tag."""
    _TAG_MAP = {
        ElementType.PAGE: "div",
        ElementType.HEADER: "header",
        ElementType.NAV: "nav",
        ElementType.SECTION: "section",
        ElementType.CONTAINER: "div",
        ElementType.TEXT: "p",
        ElementType.BUTTON: "button",
        ElementType.LINK: "a",
        ElementType.IMAGE: "img",
        ElementType.INPUT: "input",
        ElementType.FORM: "form",
        ElementType.CARD: "div",
        ElementType.LIST: "ul",
        ElementType.TABLE: "table",
        ElementType.FOOTER: "footer",
        ElementType.ICON: "span",
        ElementType.UNKNOWN: "div",
    }
    if element_type == ElementType.HEADING:
        if depth <= 1:
            return "h1"
        elif depth == 2:
            return "h2"
        else:
            return "h3"
    return _TAG_MAP.get(element_type, "div")


def _infer_layout(children: list[UIASTNode], parent_type: ElementType) -> tuple[Literal["flow", "flex", "grid", "absolute"], dict[str, str]]:
    """Infer layout strategy based on spatial arrangement of children."""
    layout_style: dict[str, str] = {}
    if not children or len(children) < 2:
        if parent_type == ElementType.CARD:
            return "flex", {"display": "flex", "flexDirection": "column"}
        return "flow", layout_style

    bboxes = [c.bbox for c in children if c.bbox is not None]
    if len(bboxes) < 2:
        return "flow", layout_style

    y_coords = [b.y for b in bboxes]
    x_coords = [b.x for b in bboxes]

    y_spread = max(y_coords) - min(y_coords)
    x_spread = max(x_coords) - min(x_coords)

    # Check horizontal alignment (similar y, varying x)
    if y_spread < 0.05 and x_spread >= 0.05:
        layout_style["display"] = "flex"
        layout_style["flexDirection"] = "row"
        return "flex", layout_style

    # Check vertical alignment (similar x, varying y)
    if x_spread < 0.08 and y_spread >= 0.05:
        layout_style["display"] = "flex"
        layout_style["flexDirection"] = "column"
        return "flex", layout_style

    # Check if cards or grid-like row arrangements exist
    has_card_children = any(c.type == ElementType.CARD for c in children)
    if has_card_children:
        layout_style["display"] = "flex"
        layout_style["flexWrap"] = "wrap"
        return "flex", layout_style

    # Default to flow
    return "flow", layout_style


def _build_ir_node(ast_node: UIASTNode, depth: int) -> UIIRNode:
    html_tag = _map_html_tag(ast_node.type, depth)
    layout, layout_style = _infer_layout(ast_node.children, ast_node.type)

    short_id = ast_node.id.replace("el-", "").replace("root", "root")
    css_classes: list[str] = [f"ui2c-{ast_node.type.value}-{short_id}"]

    if ast_node.type == ElementType.PAGE and "page" not in css_classes:
        css_classes.append("page")
    elif ast_node.type == ElementType.CARD and "card" not in css_classes:
        css_classes.append("card")

    node_style: dict[str, str] = dict(ast_node.style) if ast_node.style else {}
    for k, v in layout_style.items():
        if k not in node_style:
            node_style[k] = v

    attributes: dict[str, str] = dict(ast_node.attributes)
    if ast_node.type == ElementType.IMAGE:
        attributes.setdefault("src", "https://via.placeholder.com/300x200")
        attributes.setdefault("alt", ast_node.text or "Placeholder image")
    elif ast_node.type == ElementType.LINK:
        attributes.setdefault("href", "#")
    elif ast_node.type == ElementType.BUTTON:
        attributes.setdefault("type", "button")
    elif ast_node.type == ElementType.INPUT:
        attributes.setdefault("type", "text")

    ir_children = [_build_ir_node(child, depth + 1) for child in ast_node.children]

    return UIIRNode(
        id=ast_node.id,
        type=ast_node.type,
        html_tag=html_tag,
        text=ast_node.text,
        attributes=attributes,
        bbox=ast_node.bbox,
        style=node_style,
        css_classes=css_classes,
        layout=layout,
        children=ir_children,
    )


def build_ir(ast: UIASTNode, viewport: Viewport) -> UIIR:
    """Convert AST to Intermediate Representation (IR)."""
    ir_root = _build_ir_node(ast, depth=0)
    return UIIR(
        version="1.0.0",
        viewport=viewport,
        root=ir_root,
        style_tokens={},
        assets=[],
        diagnostics=[],
    )
