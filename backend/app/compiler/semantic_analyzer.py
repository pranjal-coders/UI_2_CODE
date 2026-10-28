from __future__ import annotations

from app.schemas.models import (
    ElementType,
    UIIR,
    UIIRNode,
    Diagnostic,
)


def _check_node_recursive(
    node: UIIRNode,
    seen_ids: set[str],
    ancestor_ids: set[str],
    ancestor_types: list[ElementType],
    diagnostics: list[Diagnostic],
) -> None:
    # 1. Unique node IDs
    if node.id in seen_ids:
        diagnostics.append(
            Diagnostic(
                code="DUPLICATE_ID",
                severity="error",
                message=f"Duplicate node ID '{node.id}' detected in IR tree.",
                node_id=node.id,
                suggestion="Ensure all elements have unique IDs",
            )
        )
    seen_ids.add(node.id)

    # 4. Cycle detection
    if node.id in ancestor_ids:
        diagnostics.append(
            Diagnostic(
                code="CYCLE_DETECTED",
                severity="error",
                message=f"Cycle detected at node '{node.id}'.",
                node_id=node.id,
                suggestion="Break circular references in the AST/IR hierarchy",
            )
        )
        return  # Avoid infinite recursion

    # 2. Valid node types (warning for unknown)
    if node.type == ElementType.UNKNOWN:
        diagnostics.append(
            Diagnostic(
                code="UNKNOWN_TYPE",
                severity="warning",
                message=f"Node '{node.id}' has unknown element type.",
                node_id=node.id,
                suggestion="Classify element into a known semantic type",
            )
        )

    # 3. Valid bbox values (0-1 range, width/height > 0)
    if node.bbox is not None:
        if (
            node.bbox.x < 0.0
            or node.bbox.y < 0.0
            or node.bbox.width <= 0.0
            or node.bbox.height <= 0.0
            or (node.bbox.x + node.bbox.width) > 1.05
            or (node.bbox.y + node.bbox.height) > 1.05
        ):
            diagnostics.append(
                Diagnostic(
                    code="INVALID_BBOX",
                    severity="warning",
                    message=f"Node '{node.id}' has out-of-range bounding box dimensions.",
                    node_id=node.id,
                    suggestion="Clamp bounding box coordinates between 0.0 and 1.0",
                )
            )

        # 9. Very small bbox (likely noise)
        area = node.bbox.width * node.bbox.height
        if area < 0.0005 or node.bbox.width < 0.005 or node.bbox.height < 0.005:
            diagnostics.append(
                Diagnostic(
                    code="SMALL_BBOX_NOISE",
                    severity="warning",
                    message=f"Node '{node.id}' has a very small bounding box (area={round(area, 6)}), likely noise.",
                    node_id=node.id,
                    suggestion="Filter out or enlarge small visual detections",
                )
            )

    # 5. Invalid nesting checks
    if node.type == ElementType.BUTTON and ElementType.BUTTON in ancestor_types:
        diagnostics.append(
            Diagnostic(
                code="INVALID_NESTING",
                severity="warning",
                message=f"Button '{node.id}' is nested inside another button.",
                node_id=node.id,
                suggestion="Avoid nesting interactive buttons inside buttons",
            )
        )
    if node.type == ElementType.LINK and ElementType.LINK in ancestor_types:
        diagnostics.append(
            Diagnostic(
                code="INVALID_NESTING",
                severity="warning",
                message=f"Link '{node.id}' is nested inside another link.",
                node_id=node.id,
                suggestion="Avoid nesting links inside links",
            )
        )
    if node.type == ElementType.HEADER and ElementType.CARD in ancestor_types:
        diagnostics.append(
            Diagnostic(
                code="INVALID_NESTING",
                severity="warning",
                message=f"Header '{node.id}' is nested inside a card.",
                node_id=node.id,
                suggestion="Move header outside of the card component",
            )
        )

    # 6. Missing text on buttons/links
    if node.type in (ElementType.BUTTON, ElementType.LINK):
        if not node.text or not node.text.strip():
            diagnostics.append(
                Diagnostic(
                    code="MISSING_TEXT",
                    severity="info",
                    message=f"{node.type.value.capitalize()} '{node.id}' is missing readable text.",
                    node_id=node.id,
                    suggestion="Add descriptive label or text content for accessibility",
                )
            )

    # 7. Image nodes without valid src
    if node.type == ElementType.IMAGE:
        src = node.attributes.get("src", "")
        if not src or "placeholder" in src:
            diagnostics.append(
                Diagnostic(
                    code="PLACEHOLDER_IMAGE",
                    severity="info",
                    message=f"Image node '{node.id}' is using placeholder src.",
                    node_id=node.id,
                    suggestion="Replace placeholder with production image asset",
                )
            )

    # 8. Form controls without labels
    if node.type == ElementType.INPUT:
        has_label = bool(
            node.attributes.get("aria-label")
            or node.attributes.get("placeholder")
            or node.attributes.get("title")
            or node.text
        )
        if not has_label:
            diagnostics.append(
                Diagnostic(
                    code="UNLABELED_FORM_CONTROL",
                    severity="info",
                    message=f"Input node '{node.id}' has no associated label or placeholder.",
                    node_id=node.id,
                    suggestion="Add aria-label, placeholder, or associated label element",
                )
            )

    # 10. Check overlapping sibling nodes
    for i, child_a in enumerate(node.children):
        for child_b in node.children[i + 1 :]:
            if child_a.bbox and child_b.bbox:
                ix = max(
                    0.0,
                    min(child_a.bbox.x + child_a.bbox.width, child_b.bbox.x + child_b.bbox.width)
                    - max(child_a.bbox.x, child_b.bbox.x),
                )
                iy = max(
                    0.0,
                    min(child_a.bbox.y + child_a.bbox.height, child_b.bbox.y + child_b.bbox.height)
                    - max(child_a.bbox.y, child_b.bbox.y),
                )
                overlap_area = ix * iy
                if overlap_area > 0.005:
                    diagnostics.append(
                        Diagnostic(
                            code="SIBLING_OVERLAP",
                            severity="info",
                            message=f"Sibling nodes '{child_a.id}' and '{child_b.id}' have overlapping bboxes.",
                            node_id=child_a.id,
                            suggestion="Check layout margins to prevent visual collision",
                        )
                    )

    # Recurse down children
    new_ancestors = ancestor_ids | {node.id}
    new_ancestor_types = ancestor_types + [node.type]
    for child in node.children:
        _check_node_recursive(child, seen_ids, new_ancestors, new_ancestor_types, diagnostics)


def analyze_semantics(ir: UIIR) -> list[Diagnostic]:
    """Perform semantic and accessibility analysis on the IR tree."""
    diagnostics: list[Diagnostic] = []
    seen_ids: set[str] = set()
    ancestor_ids: set[str] = set()
    ancestor_types: list[ElementType] = []

    _check_node_recursive(ir.root, seen_ids, ancestor_ids, ancestor_types, diagnostics)
    return diagnostics
