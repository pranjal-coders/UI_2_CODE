from __future__ import annotations

from typing import Optional
from app.schemas.models import (
    ElementType,
    BoundingBox,
    DetectedElement,
    Viewport,
    UIASTNode,
)

# Container types and their allowed children
CONTAINER_TYPES: set[ElementType] = {
    ElementType.PAGE,
    ElementType.HEADER,
    ElementType.NAV,
    ElementType.SECTION,
    ElementType.CONTAINER,
    ElementType.CARD,
    ElementType.LIST,
    ElementType.TABLE,
    ElementType.FOOTER,
    ElementType.FORM,
}

LEAF_TYPES: set[ElementType] = {
    ElementType.BUTTON,
    ElementType.LINK,
    ElementType.HEADING,
    ElementType.TEXT,
    ElementType.ICON,
    ElementType.INPUT,
    ElementType.IMAGE,
    ElementType.UNKNOWN,
}

# Type constraints: parent -> disallowed child types
DISALLOWED_CHILDREN: dict[ElementType, set[ElementType]] = {
    ElementType.NAV: {
        ElementType.BUTTON,
        ElementType.HEADER,
        ElementType.FOOTER,
        ElementType.SECTION,
        ElementType.CARD,
        ElementType.FORM,
        ElementType.TABLE,
        ElementType.PAGE,
    },
    ElementType.BUTTON: set(ElementType),  # Leaf node
    ElementType.LINK: {
        ElementType.HEADER,
        ElementType.FOOTER,
        ElementType.SECTION,
        ElementType.CARD,
        ElementType.FORM,
        ElementType.TABLE,
        ElementType.PAGE,
        ElementType.BUTTON,
    },
    ElementType.CARD: {
        ElementType.PAGE,
        ElementType.HEADER,
        ElementType.FOOTER,
        ElementType.SECTION,
        ElementType.CARD,
    },
    ElementType.FOOTER: {
        ElementType.PAGE,
        ElementType.HEADER,
        ElementType.FOOTER,
        ElementType.SECTION,
    },
    ElementType.HEADER: {
        ElementType.PAGE,
        ElementType.HEADER,
        ElementType.FOOTER,
        ElementType.SECTION,
    },
    ElementType.SECTION: {
        ElementType.PAGE,
        ElementType.HEADER,
        ElementType.FOOTER,
    },
}


def _clamp_bbox(bbox: BoundingBox) -> BoundingBox:
    x = max(0.0, min(1.0, bbox.x))
    y = max(0.0, min(1.0, bbox.y))
    width = max(0.0, min(1.0 - x, bbox.width))
    height = max(0.0, min(1.0 - y, bbox.height))
    return BoundingBox(x=round(x, 4), y=round(y, 4), width=round(width, 4), height=round(height, 4))


def _bbox_area(bbox: BoundingBox) -> float:
    return bbox.width * bbox.height


def _box_contains(parent_box: BoundingBox, child_box: BoundingBox, eps: float = 0.02) -> bool:
    """Check if parent_box contains child_box with tolerance or high intersection ratio."""
    p_x1, p_y1 = parent_box.x - eps, parent_box.y - eps
    p_x2, p_y2 = parent_box.x + parent_box.width + eps, parent_box.y + parent_box.height + eps

    c_x1, c_y1 = child_box.x, child_box.y
    c_x2, c_y2 = child_box.x + child_box.width, child_box.y + child_box.height

    if p_x1 <= c_x1 and p_y1 <= c_y1 and p_x2 >= c_x2 and p_y2 >= c_y2:
        return True

    # Calculate intersection area over child area
    ix1 = max(parent_box.x, child_box.x)
    iy1 = max(parent_box.y, child_box.y)
    ix2 = min(parent_box.x + parent_box.width, child_box.x + child_box.width)
    iy2 = min(parent_box.y + parent_box.height, child_box.y + child_box.height)

    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    intersection = iw * ih
    child_area = child_box.width * child_box.height

    if child_area > 0 and (intersection / child_area) >= 0.75:
        return True

    return False


def _can_contain(parent_type: ElementType, child_type: ElementType) -> bool:
    if parent_type in LEAF_TYPES:
        return False
    disallowed = DISALLOWED_CHILDREN.get(parent_type, set())
    if child_type in disallowed:
        return False
    return True


def _sort_children_reading_order(children: list[UIASTNode]) -> list[UIASTNode]:
    """Sort child nodes in natural reading order: top-to-bottom, left-to-right with row grouping."""
    if len(children) <= 1:
        return children

    # Filter out nodes without bbox
    with_bbox = [c for c in children if c.bbox is not None]
    without_bbox = [c for c in children if c.bbox is None]

    if not with_bbox:
        return children

    # Sort initially by top (y) coordinate
    sorted_by_y = sorted(with_bbox, key=lambda c: (c.bbox.y if c.bbox else 0, c.bbox.x if c.bbox else 0))

    # Group into visual rows
    rows: list[list[UIASTNode]] = []
    current_row: list[UIASTNode] = [sorted_by_y[0]]

    for node in sorted_by_y[1:]:
        assert node.bbox is not None
        ref_node = current_row[0]
        assert ref_node.bbox is not None

        # Check vertical overlap with the current row
        y_top = max(ref_node.bbox.y, node.bbox.y)
        y_bottom = min(ref_node.bbox.y + ref_node.bbox.height, node.bbox.y + node.bbox.height)
        overlap = y_bottom - y_top
        min_height = min(ref_node.bbox.height, node.bbox.height)

        is_same_row = (
            (overlap > 0.3 * min_height)
            or abs(ref_node.bbox.y - node.bbox.y) < 0.04
        )

        if is_same_row:
            current_row.append(node)
        else:
            rows.append(current_row)
            current_row = [node]

    if current_row:
        rows.append(current_row)

    # Sort each row horizontally (x coordinate)
    ordered: list[UIASTNode] = []
    for row in rows:
        ordered.extend(sorted(row, key=lambda c: c.bbox.x if c.bbox else 0))

    ordered.extend(without_bbox)
    return ordered


def _collect_tree_nodes(node: UIASTNode) -> list[UIASTNode]:
    nodes = [node]
    for child in node.children:
        nodes.extend(_collect_tree_nodes(child))
    return nodes


def build_ast(viewport: Viewport, elements: list[DetectedElement]) -> UIASTNode:
    """Build a hierarchical UI AST from flat detected elements.
    
    1. Create root Page node with viewport bbox
    2. Sort elements by area (largest first) for parent assignment
    3. For each element, find the best parent: smallest existing node containing the element
    4. Apply type constraints
    5. Preserve visual reading order
    6. Clamps out-of-viewport bboxes
    7. Generate warnings for ambiguous nesting
    8. Prevent cycles and self-nesting
    9. Store metadata with source_element_id and confidence
    """
    root_bbox = BoundingBox(x=0.0, y=0.0, width=1.0, height=1.0)
    root = UIASTNode(
        id="root",
        type=ElementType.PAGE,
        bbox=root_bbox,
        style={"width": f"{viewport.width}px", "minHeight": f"{viewport.height}px"},
        attributes={"class": "page"},
        children=[],
        metadata={"source": "root_viewport", "warnings": []},
    )

    if not elements:
        return root

    # Clamp bounding boxes and create AST nodes
    node_map: dict[str, UIASTNode] = {}
    for el in elements:
        clamped_box = _clamp_bbox(el.bbox)
        node = UIASTNode(
            id=el.id,
            type=el.type,
            text=el.text,
            attributes={},
            bbox=clamped_box,
            style=dict(el.style) if el.style else None,
            children=[],
            metadata={
                "source_element_id": el.id,
                "confidence": el.confidence,
                "relation_hints": el.relation_hints or [],
                "warnings": [],
            },
        )
        node_map[el.id] = node

    # Sort elements by area descending (largest first)
    sorted_elements = sorted(
        elements,
        key=lambda el: _bbox_area(node_map[el.id].bbox or el.bbox),
        reverse=True,
    )

    # Insert each element into the tree under its best-fitting parent
    for el in sorted_elements:
        node = node_map[el.id]
        assert node.bbox is not None

        # Gather all currently attached nodes in the tree
        available_parents = _collect_tree_nodes(root)

        best_parent: UIASTNode = root
        best_area = float("inf")
        ambiguous_parents: list[str] = []

        for candidate in available_parents:
            if candidate.id == node.id:
                continue
            if not _can_contain(candidate.type, node.type):
                continue
            assert candidate.bbox is not None
            if _box_contains(candidate.bbox, node.bbox):
                area = _bbox_area(candidate.bbox)
                if area < best_area:
                    best_area = area
                    best_parent = candidate
                elif abs(area - best_area) < 1e-5 and candidate.id != best_parent.id:
                    ambiguous_parents.append(candidate.id)

        if ambiguous_parents:
            node.metadata.setdefault("warnings", []).append(
                f"Ambiguous nesting: node could also fit under {ambiguous_parents}"
            )

        best_parent.children.append(node)

    # Recursively sort children of every node in visual reading order
    def _finalize_order(parent: UIASTNode) -> None:
        parent.children = _sort_children_reading_order(parent.children)
        for child in parent.children:
            _finalize_order(child)

    _finalize_order(root)
    return root
