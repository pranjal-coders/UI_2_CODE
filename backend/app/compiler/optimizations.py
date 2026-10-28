from __future__ import annotations

import re
from typing import Callable
from app.schemas.models import (
    ElementType,
    UIIR,
    UIIRNode,
    OptimizationEvent,
)


def _traverse_nodes(root: UIIRNode) -> list[UIIRNode]:
    nodes = [root]
    for child in root.children:
        nodes.extend(_traverse_nodes(child))
    return nodes


def _normalize_hex_color(val: str) -> str:
    # Match #RGB or #RRGGBB
    val = val.strip()
    match_3 = re.fullmatch(r"#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])", val)
    if match_3:
        r, g, b = match_3.groups()
        return f"#{r}{r}{g}{g}{b}{b}".lower()
    match_6 = re.fullmatch(r"#[0-9a-fA-F]{6}", val)
    if match_6:
        return val.lower()
    return val


def style_normalization(ir: UIIR) -> tuple[UIIR, OptimizationEvent]:
    """Canonicalize color values, normalize font sizes, and remove redundant defaults."""
    new_ir = ir.model_copy(deep=True)
    all_nodes = _traverse_nodes(new_ir.root)
    changed_count = 0

    redundant_keys = {"border": "none", "outline": "none", "opacity": "1"}

    for node in all_nodes:
        if not node.style:
            continue
        cleaned_style: dict[str, str] = {}
        for prop, val in node.style.items():
            orig_val = val
            # Check redundant defaults
            if redundant_keys.get(prop) == val:
                changed_count += 1
                continue

            # Color normalization
            if isinstance(val, str) and val.startswith("#"):
                val = _normalize_hex_color(val)

            # Font size normalization: bare numbers to px
            if prop in ("fontSize", "width", "height", "padding", "margin") and isinstance(val, str):
                if val.isdigit():
                    val = f"{val}px"

            if val != orig_val:
                changed_count += 1
            cleaned_style[prop] = val

        node.style = cleaned_style

    event = OptimizationEvent(
        pass_name="style_normalization",
        description="Canonicalize color values, normalize font sizes, and remove redundant defaults",
        changed_count=changed_count,
        before_summary=f"Processed {len(all_nodes)} nodes",
        after_summary=f"{changed_count} style attributes normalized" if changed_count else "No changes",
    )
    return new_ir, event


def duplicate_style_elimination(ir: UIIR) -> tuple[UIIR, OptimizationEvent]:
    """Find nodes with identical style dicts, create shared CSS class in style_tokens, assign to nodes."""
    new_ir = ir.model_copy(deep=True)
    all_nodes = _traverse_nodes(new_ir.root)

    # Group nodes by their exact non-empty style tuple
    style_groups: dict[tuple[tuple[str, str], ...], list[UIIRNode]] = {}
    for node in all_nodes:
        if node.style and len(node.style) >= 1:
            key = tuple(sorted(node.style.items()))
            style_groups.setdefault(key, []).append(node)

    # Sort groups deterministically by style key
    sorted_groups = sorted(
        [(k, v) for k, v in style_groups.items() if len(v) >= 2],
        key=lambda item: item[0],
    )

    changed_count = 0
    token_idx = 1
    for style_key, nodes in sorted_groups:
        class_name = f"ui2c-shared-{token_idx}"
        style_dict = dict(style_key)
        new_ir.style_tokens[class_name] = style_dict

        for node in nodes:
            if class_name not in node.css_classes:
                node.css_classes.append(class_name)
                # Keep node.style empty or minimal so shared class handles styling
                node.style = {}
                changed_count += 1
        token_idx += 1

    event = OptimizationEvent(
        pass_name="duplicate_style_elimination",
        description="Extract identical styles into shared CSS utility tokens",
        changed_count=changed_count,
        before_summary=f"Found {len(sorted_groups)} repeated style signatures",
        after_summary=f"Created {len(sorted_groups)} shared CSS tokens applied to {changed_count} nodes" if changed_count else "No changes",
    )
    return new_ir, event


def repeated_pattern_recognition(ir: UIIR) -> tuple[UIIR, OptimizationEvent]:
    """Find sibling nodes of same type with similar styles, give them a shared class. Do NOT remove any elements."""
    new_ir = ir.model_copy(deep=True)
    all_nodes = _traverse_nodes(new_ir.root)
    changed_count = 0
    group_counter = 1

    for parent in all_nodes:
        if len(parent.children) < 2:
            continue

        # Group siblings by element type
        type_to_siblings: dict[ElementType, list[UIIRNode]] = {}
        for child in parent.children:
            type_to_siblings.setdefault(child.type, []).append(child)

        for el_type, siblings in sorted(type_to_siblings.items(), key=lambda x: x[0].value):
            if len(siblings) >= 2:
                pattern_class = f"{el_type.value}-group-{group_counter}"
                for s in siblings:
                    if pattern_class not in s.css_classes:
                        s.css_classes.append(pattern_class)
                        changed_count += 1
                group_counter += 1

    event = OptimizationEvent(
        pass_name="repeated_pattern_recognition",
        description="Identify repeated sibling patterns and assign shared pattern classes",
        changed_count=changed_count,
        before_summary=f"Scanned {len(all_nodes)} nodes for repeated sibling structures",
        after_summary=f"Assigned group classes to {changed_count} elements" if changed_count else "No changes",
    )
    return new_ir, event


def safe_wrapper_simplification(ir: UIIR) -> tuple[UIIR, OptimizationEvent]:
    """Remove a wrapper div ONLY when: 1 child, no semantic tag, no background/border, no explicit positioning."""
    new_ir = ir.model_copy(deep=True)
    all_nodes = _traverse_nodes(new_ir.root)
    removed_ids: list[str] = []

    visual_props = {"background", "backgroundColor", "border", "borderColor", "borderRadius", "boxShadow"}
    position_props = {"position", "top", "left", "right", "bottom"}

    def _is_safe_wrapper(node: UIIRNode) -> bool:
        if node.id == "root":
            return False
        # Must be a plain div with container/unknown type (no semantic tag like header, nav, section, card, footer)
        if node.html_tag != "div" or node.type not in (ElementType.CONTAINER, ElementType.UNKNOWN):
            return False
        if len(node.children) != 1:
            return False
        # Must not have visual background/border styling
        for prop in visual_props:
            if prop in node.style and node.style[prop] not in ("none", "transparent", ""):
                return False
        # Must not have explicit positioning
        for prop in position_props:
            if prop in node.style:
                return False
        # Must not have specialized semantic css classes (e.g., 'card')
        if any(cls in node.css_classes for cls in ("card", "page", "header", "footer")):
            return False
        return True

    def _simplify_children(parent: UIIRNode) -> None:
        new_children: list[UIIRNode] = []
        for child in parent.children:
            if _is_safe_wrapper(child):
                removed_ids.append(child.id)
                new_children.append(child.children[0])
            else:
                new_children.append(child)
        parent.children = new_children
        for child in parent.children:
            _simplify_children(child)

    _simplify_children(new_ir.root)

    event = OptimizationEvent(
        pass_name="safe_wrapper_simplification",
        description="Safely eliminate unstyled single-child wrapper divs",
        changed_count=len(removed_ids),
        before_summary=f"Evaluated tree of {len(all_nodes)} nodes",
        after_summary=f"Removed {len(removed_ids)} redundant wrapper divs ({removed_ids})" if removed_ids else "No changes",
    )
    return new_ir, event


def layout_simplification(ir: UIIR) -> tuple[UIIR, OptimizationEvent]:
    """For flex containers where children have consistent spacing, consolidate layout attributes to parent."""
    new_ir = ir.model_copy(deep=True)
    all_nodes = _traverse_nodes(new_ir.root)
    changed_count = 0

    for node in all_nodes:
        if node.layout == "flex" and len(node.children) >= 2:
            # Check if children share a common margin that can be consolidated to gap
            child_margins = [c.style.get("marginRight") or c.style.get("gap") for c in node.children[:-1]]
            if child_margins and all(m == child_margins[0] and m is not None for m in child_margins):
                shared_margin = child_margins[0]
                if shared_margin and "gap" not in node.style:
                    node.style["gap"] = shared_margin
                    for c in node.children:
                        if "marginRight" in c.style:
                            del c.style["marginRight"]
                    changed_count += 1

    event = OptimizationEvent(
        pass_name="layout_simplification",
        description="Consolidate repetitive sibling gaps into parent flexbox gap",
        changed_count=changed_count,
        before_summary=f"Inspected flex containers across {len(all_nodes)} nodes",
        after_summary=f"Consolidated gaps for {changed_count} containers" if changed_count else "No changes",
    )
    return new_ir, event


def run_optimizations(ir: UIIR) -> tuple[UIIR, list[OptimizationEvent]]:
    """Execute all optimization passes deterministically in pipeline order."""
    optimized = ir
    events: list[OptimizationEvent] = []

    passes: list[Callable[[UIIR], tuple[UIIR, OptimizationEvent]]] = [
        style_normalization,
        duplicate_style_elimination,
        repeated_pattern_recognition,
        safe_wrapper_simplification,
        layout_simplification,
    ]

    for p in passes:
        optimized, event = p(optimized)
        events.append(event)

    return optimized, events
